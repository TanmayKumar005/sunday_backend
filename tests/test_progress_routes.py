"""API tests for /progress (needs the project's dependencies + SQLite)."""

from app.models.progress import LearnerProgress


def _learner(client, name="Asha"):
    return client.post(
        "/learners/", json={"name": name, "grade": "6", "subject": "Mathematics"}
    ).json()


def _start(client, learner_id):
    return client.post("/assessments/start", json={"learner_id": learner_id}).json()


def _correct(client, qid):
    return client.get(f"/questions/{qid}/solution").json()["correct_answer"]


def _answer(client, assessment, qid, answer, seconds=None):
    body = {"question_id": qid, "answer": answer}
    if seconds is not None:
        body["response_time_seconds"] = seconds
    return client.post(f"/assessments/{assessment['assessment_id']}/answer", json=body)


def test_unknown_learner_returns_404(client, seeded):
    assert client.get("/progress/9999").status_code == 404
    assert client.get("/progress/9999/summary").status_code == 404


def test_new_learner_has_empty_progress_and_a_start_recommendation(client, seeded):
    learner = _learner(client)

    progress = client.get(f"/progress/{learner['id']}")
    assert progress.status_code == 200
    assert progress.json() == {"learner_id": learner["id"], "topics": []}

    summary = client.get(f"/progress/{learner['id']}/summary").json()
    assert summary["learner_name"] == "Asha"
    assert summary["total_topics"] == 9
    assert summary["topics_started"] == 0
    assert summary["topics_completed"] == 0
    assert summary["questions_attempted"] == 0
    assert summary["accuracy"] == 0.0
    assert summary["struggle_score"] is None
    assert summary["last_activity"] is None
    assert summary["recommended_action"] == "START_LEARNING"
    assert summary["recommended_topic"]["section_code"] == "7.1"


def test_answering_updates_progress_automatically(client, seeded):
    learner = _learner(client)
    assessment = _start(client, learner["id"])
    q1, q2 = assessment["questions"][:2]

    _answer(client, assessment, q1, _correct(client, q1))
    _answer(client, assessment, q2, "definitely wrong")

    topics = client.get(f"/progress/{learner['id']}").json()["topics"]

    assert len(topics) == 1
    topic = topics[0]
    assert topic["section_code"] == "7.1"
    assert topic["topic"] == "Fractional Units and Equal Shares"
    assert topic["questions_attempted"] == 2
    assert topic["questions_correct"] == 1
    assert topic["accuracy"] == 50.0
    assert topic["struggle_level"] in ("Low", "Medium", "High")
    assert 0.0 <= topic["struggle_score"] <= 1.0
    assert topic["current_difficulty"] in ("EASY", "MEDIUM", "HARD")
    assert topic["completed"] is False
    assert topic["last_activity"]


def test_reanswering_and_reevaluating_never_double_counts(client, seeded, db_session):
    learner = _learner(client)
    assessment = _start(client, learner["id"])
    qid = assessment["questions"][0]

    _answer(client, assessment, qid, "wrong")
    _answer(client, assessment, qid, _correct(client, qid))

    for _ in range(3):
        client.post(
            "/adaptation/evaluate",
            json={"assessment_id": assessment["assessment_id"], "question_id": qid},
        )

    topic = client.get(f"/progress/{learner['id']}").json()["topics"][0]
    assert topic["questions_attempted"] == 1
    assert topic["questions_correct"] == 1
    assert db_session.query(LearnerProgress).count() == 1


def test_topic_completes_and_stays_completed(client, seeded):
    learner = _learner(client)
    assessment = _start(client, learner["id"])
    q1, q2, q3, q4 = assessment["questions"][:4]

    for qid in (q1, q2):
        _answer(client, assessment, qid, _correct(client, qid))
    assert client.get(f"/progress/{learner['id']}").json()["topics"][0]["completed"] is False

    _answer(client, assessment, q3, _correct(client, q3))
    assert client.get(f"/progress/{learner['id']}").json()["topics"][0]["completed"] is True

    # a later mistake does not un-complete the topic
    _answer(client, assessment, q4, "definitely wrong")
    assert client.get(f"/progress/{learner['id']}").json()["topics"][0]["completed"] is True


def test_summary_lists_completed_and_weak_topics(client, seeded):
    learner = _learner(client)
    assessment = _start(client, learner["id"])
    qids = assessment["questions"]

    for qid in qids[:3]:
        _answer(client, assessment, qid, _correct(client, qid))

    summary = client.get(f"/progress/{learner['id']}/summary").json()

    assert summary["topics_started"] == 1
    assert summary["topics_completed"] == 1
    assert summary["completed_topics"] == ["7.1 Fractional Units and Equal Shares"]
    assert summary["completion_percent"] == 11.11
    assert summary["questions_attempted"] == 3
    assert summary["questions_correct"] == 3
    assert summary["accuracy"] == 100.0
    assert summary["weak_topics"] == []
    assert summary["recommended_action"] == "CONTINUE_NEXT_TOPIC"
    assert summary["recommended_topic"]["section_code"] == "7.2"


def test_summary_flags_weak_topic_and_recommends_practising_it(client, seeded):
    learner = _learner(client)
    assessment = _start(client, learner["id"])

    for qid in assessment["questions"][:3]:
        _answer(client, assessment, qid, "definitely wrong")

    summary = client.get(f"/progress/{learner['id']}/summary").json()

    assert summary["struggle_level"] == "High"
    assert summary["struggle_score"] >= 0.6
    assert summary["current_difficulty"] == "EASY"
    assert [w["section_code"] for w in summary["weak_topics"]] == ["7.1"]
    assert summary["weak_topics"][0]["accuracy"] == 0.0
    assert summary["recommended_action"] == "PRACTISE_WEAK_TOPIC"
    assert summary["recommended_topic"]["section_code"] == "7.1"
    assert summary["last_activity"]


def test_progress_is_separate_for_each_learner(client, seeded):
    first, second = _learner(client, "Asha"), _learner(client, "Ravi")

    a1 = _start(client, first["id"])
    _answer(client, a1, a1["questions"][0], "wrong")

    assert len(client.get(f"/progress/{first['id']}").json()["topics"]) == 1
    assert client.get(f"/progress/{second['id']}").json()["topics"] == []


def test_answer_still_saved_when_the_adaptive_update_fails(client, seeded, monkeypatch):
    import app.services.adaptation_service as adaptation

    def boom(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(adaptation, "evaluate_answer", boom)

    learner = _learner(client)
    assessment = _start(client, learner["id"])
    qid = assessment["questions"][0]

    response = _answer(client, assessment, qid, _correct(client, qid))

    assert response.status_code == 200
    assert response.json() == {"question_id": qid, "correct": True}

    result = client.get(f"/assessments/{assessment['assessment_id']}/result").json()
    assert result["score"] == 1
