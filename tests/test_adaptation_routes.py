"""API tests for /adaptation (needs the project's dependencies + SQLite)."""

from app.models.question import Question


def _start(client):
    learner = client.post(
        "/learners/", json={"name": "Asha", "grade": "6", "subject": "Mathematics"}
    ).json()
    assessment = client.post(
        "/assessments/start", json={"learner_id": learner["id"]}
    ).json()
    return learner, assessment


def _answer(client, assessment, question_id, answer, seconds=None):
    body = {"question_id": question_id, "answer": answer}
    if seconds is not None:
        body["response_time_seconds"] = seconds
    return client.post(f"/assessments/{assessment['assessment_id']}/answer", json=body)


def _correct(client, question_id):
    return client.get(f"/questions/{question_id}/solution").json()["correct_answer"]


def _evaluate(client, assessment, question_id):
    return client.post(
        "/adaptation/evaluate",
        json={"assessment_id": assessment["assessment_id"], "question_id": question_id},
    )


def _scaffold(client, assessment, question_id):
    return client.post(
        "/adaptation/scaffold",
        json={"assessment_id": assessment["assessment_id"], "question_id": question_id},
    )


# ---- seed / existing flow --------------------------------------------------

def test_seeded_questions_all_have_hints(seeded):
    questions = seeded.query(Question).all()
    assert questions and all(q.hint for q in questions)


def test_answer_endpoint_shape_is_unchanged(client, seeded):
    _, assessment = _start(client)
    qid = assessment["questions"][0]

    response = _answer(client, assessment, qid, _correct(client, qid))

    assert response.status_code == 200
    assert response.json() == {"question_id": qid, "correct": True}


def test_negative_response_time_rejected(client, seeded):
    _, assessment = _start(client)
    qid = assessment["questions"][0]
    assert _answer(client, assessment, qid, "x", seconds=-1).status_code == 422


# ---- evaluate --------------------------------------------------------------

def test_evaluate_requires_a_submitted_answer(client, seeded):
    _, assessment = _start(client)
    response = _evaluate(client, assessment, assessment["questions"][0])
    assert response.status_code == 409


def test_evaluate_not_found_cases(client, seeded):
    _, assessment = _start(client)

    missing_assessment = client.post(
        "/adaptation/evaluate", json={"assessment_id": 9999, "question_id": 1}
    )
    assert missing_assessment.status_code == 404

    outside = client.post(
        "/adaptation/evaluate",
        json={"assessment_id": assessment["assessment_id"], "question_id": 9999},
    )
    assert outside.status_code == 404


def test_correct_answer_means_low_struggle_and_continue(client, seeded):
    learner, assessment = _start(client)
    qid = assessment["questions"][0]
    _answer(client, assessment, qid, _correct(client, qid))

    body = _evaluate(client, assessment, qid).json()

    assert body["struggle_level"] == "Low"
    assert body["action"] == "CONTINUE"
    assert body["suggested_scaffold_level"] == 0
    assert body["reason"] and body["rules_applied"]
    assert body["profile"]["struggle_level"] == "Low"
    assert body["recommended_question"]["id"] != qid
    assert "correct_answer" not in body["recommended_question"]
    assert body["recommended_content"]["section_code"] == "7.1"


def test_first_wrong_answer_is_medium_with_hint_and_similar_question(client, seeded):
    _, assessment = _start(client)
    qid = assessment["questions"][0]
    _answer(client, assessment, qid, "definitely wrong")

    body = _evaluate(client, assessment, qid).json()

    assert body["struggle_level"] == "Medium"
    assert body["action"] == "HINT_AND_SIMILAR_QUESTION"
    assert body["suggested_scaffold_level"] == 1
    assert body["recommended_question"]["id"] != qid
    assert body["profile"]["struggle_level"] == "Medium"
    assert body["profile"]["current_difficulty"] == body["next_difficulty"]


def test_three_wrong_answers_mean_high_struggle_and_prerequisite_revisit(client, seeded):
    _, assessment = _start(client)
    qids = assessment["questions"][:3]

    for qid in qids:
        _answer(client, assessment, qid, "definitely wrong")

    body = _evaluate(client, assessment, qids[-1]).json()

    assert body["struggle_level"] == "High"
    assert body["action"] == "SCAFFOLD_AND_REVISIT_PREREQUISITE"
    assert body["next_difficulty"] == "EASY"
    assert body["suggested_scaffold_level"] == 2
    # 7.1 has no earlier concept, so it revisits itself
    assert body["revisit_prerequisite"]["section_code"] == "7.1"
    assert body["recommended_question"]["difficulty"] == "EASY"
    assert body["profile"]["struggle_level"] == "High"


def test_high_struggle_in_a_later_section_revisits_its_prerequisite(client, seeded, db_session):
    learner = client.post(
        "/learners/", json={"name": "Ravi", "grade": "6", "subject": "Mathematics"}
    ).json()

    from app.models.assessment import Assessment

    section_8 = client.get("/content/sections/7.8").json()["unit_id"]
    unit_questions = client.get(f"/questions/?unit_id={section_8}").json()
    ids = [q["id"] for q in unit_questions][:3]

    db_session.add(Assessment(learner_id=learner["id"], question_ids=ids))
    db_session.commit()
    assessment = {"assessment_id": db_session.query(Assessment).one().id}

    for qid in ids:
        _answer(client, assessment, qid, "definitely wrong")

    body = _evaluate(client, assessment, ids[-1]).json()

    assert body["struggle_level"] == "High"
    assert body["revisit_prerequisite"]["section_code"] == "7.6"
    assert body["recommended_content"]["section_code"] == "7.6"
    assert body["recommended_question"]["unit_id"] == body["revisit_prerequisite"]["unit_id"]


def test_correct_streak_increases_difficulty(client, seeded):
    _, assessment = _start(client)
    qids = assessment["questions"][:3]          # EASY, EASY, EASY

    for qid in qids:
        _answer(client, assessment, qid, _correct(client, qid))

    body = _evaluate(client, assessment, qids[-1]).json()

    assert body["struggle_level"] == "Low"
    assert body["signals"]["correct_streak"] == 3
    assert body["action"] == "INCREASE_DIFFICULTY"
    assert body["next_difficulty"] == "MEDIUM"
    assert body["recommended_question"]["difficulty"] == "MEDIUM"
    assert body["profile"]["current_difficulty"] == "MEDIUM"


def test_response_time_and_retries_are_recorded(client, seeded):
    _, assessment = _start(client)
    qid = assessment["questions"][0]

    _answer(client, assessment, qid, "wrong one", seconds=200)
    _answer(client, assessment, qid, "wrong two", seconds=150)

    signals = _evaluate(client, assessment, qid).json()["signals"]

    assert signals["attempts"] == 2
    assert signals["wrong_attempts"] == 2
    assert signals["response_time_seconds"] == 150
    assert signals["is_slow"] is True
    assert signals["time_adjustment"] == 0.05
    assert signals["repeated_mistakes"] > 0


def test_evaluation_does_not_change_assessment_results(client, seeded):
    _, assessment = _start(client)
    qid = assessment["questions"][0]
    _answer(client, assessment, qid, _correct(client, qid))

    before = client.get(f"/assessments/{assessment['assessment_id']}/result").json()
    _evaluate(client, assessment, qid)
    after = client.get(f"/assessments/{assessment['assessment_id']}/result").json()

    assert before == after


# ---- scaffold --------------------------------------------------------------

def test_scaffold_needs_an_answer_first(client, seeded):
    _, assessment = _start(client)
    response = _scaffold(client, assessment, assessment["questions"][0])
    assert response.status_code == 409


def test_scaffold_not_found(client, seeded):
    _, assessment = _start(client)
    response = client.post(
        "/adaptation/scaffold",
        json={"assessment_id": assessment["assessment_id"], "question_id": 9999},
    )
    assert response.status_code == 404


def test_scaffold_refused_after_a_correct_answer(client, seeded):
    _, assessment = _start(client)
    qid = assessment["questions"][0]
    _answer(client, assessment, qid, _correct(client, qid))

    assert _scaffold(client, assessment, qid).status_code == 409


def test_scaffold_levels_are_progressive_and_hide_the_answer_until_four(client, seeded, db_session):
    _, assessment = _start(client)
    qid = assessment["questions"][0]
    correct = _correct(client, qid)
    _answer(client, assessment, qid, "definitely wrong")

    stored_hint = db_session.query(Question).filter(Question.id == qid).one().hint

    seen = []
    for expected_level in (1, 2, 3, 4):
        body = _scaffold(client, assessment, qid).json()
        seen.append(body["level_name"])

        assert body["level"] == expected_level
        assert body["is_final_level"] is (expected_level == 4)

        if expected_level < 4:
            assert body["reveals_answer"] is False
            assert body["correct_answer"] is None
            assert correct not in body["content"]
            assert body["next_level"] == expected_level + 1
        else:
            assert body["reveals_answer"] is True
            assert body["correct_answer"] == correct
            assert body["next_level"] is None

        if expected_level == 1:
            assert body["content"] == stored_hint
        if expected_level == 3:
            assert len(body["steps"]) >= 3

    assert seen == ["HINT", "CONCEPT_REMINDER", "WORKED_STEPS", "FINAL_EXPLANATION"]

    again = _scaffold(client, assessment, qid).json()
    assert again["level"] == 4


def test_scaffold_level_is_tracked_per_question(client, seeded):
    _, assessment = _start(client)
    first, second = assessment["questions"][:2]

    _answer(client, assessment, first, "wrong")
    _answer(client, assessment, second, "wrong")

    _scaffold(client, assessment, first)
    _scaffold(client, assessment, first)

    assert _scaffold(client, assessment, second).json()["level"] == 1
    assert _scaffold(client, assessment, first).json()["level"] == 3
