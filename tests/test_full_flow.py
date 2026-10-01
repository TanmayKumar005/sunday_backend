"""End-to-end adaptive loop (needs the project's dependencies + SQLite).

learner -> assessment -> answer -> performance -> struggle -> progress
-> adaptation decision -> scaffolding -> next question -> final result
-> progress summary
"""

from app.models.learner import Learner
from app.models.learning_profile import LearningProfile


def _learner(client, name):
    response = client.post(
        "/learners/", json={"name": name, "grade": "6", "subject": "Mathematics"}
    )
    assert response.status_code == 200
    return response.json()


def _start(client, learner_id):
    response = client.post("/assessments/start", json={"learner_id": learner_id})
    assert response.status_code == 200
    return response.json()


def _correct(client, qid):
    return client.get(f"/questions/{qid}/solution").json()["correct_answer"]


def _answer(client, assessment_id, qid, answer, seconds=None):
    body = {"question_id": qid, "answer": answer}
    if seconds is not None:
        body["response_time_seconds"] = seconds
    return client.post(f"/assessments/{assessment_id}/answer", json=body)


def _evaluate(client, assessment_id, qid):
    response = client.post(
        "/adaptation/evaluate",
        json={"assessment_id": assessment_id, "question_id": qid},
    )
    assert response.status_code == 200
    return response.json()


def _scaffold(client, assessment_id, qid):
    response = client.post(
        "/adaptation/scaffold",
        json={"assessment_id": assessment_id, "question_id": qid},
    )
    assert response.status_code == 200
    return response.json()


def test_struggling_learner_full_adaptive_loop(client, seeded, db_session):
    # 1. learner creation
    learner = _learner(client, "Asha")
    assert learner["mastery_level"] == "Beginner"

    # 2. assessment creation / start
    assessment = _start(client, learner["id"])
    aid = assessment["assessment_id"]
    qids = assessment["questions"]
    assert len(qids) == 5

    # 3 + 4. answer submission -> correctness / performance
    first = _answer(client, aid, qids[0], "definitely wrong", seconds=15)
    assert first.status_code == 200
    assert first.json() == {"question_id": qids[0], "correct": False}

    _answer(client, aid, qids[1], "definitely wrong", seconds=20)
    _answer(client, aid, qids[2], "definitely wrong", seconds=25)

    # 5. struggle calculation + 7. adaptive recommendation
    decision = _evaluate(client, aid, qids[2])
    assert decision["is_correct"] is False
    assert decision["struggle_level"] == "High"
    assert decision["struggle_score"] >= 0.6
    assert decision["action"] == "SCAFFOLD_AND_REVISIT_PREREQUISITE"
    assert decision["next_difficulty"] == "EASY"
    assert decision["suggested_scaffold_level"] == 2
    assert decision["revisit_prerequisite"]["section_code"] == "7.1"
    assert decision["recommended_question"]["difficulty"] == "EASY"
    assert "correct_answer" not in decision["recommended_question"]
    assert decision["reason"] and decision["rules_applied"]

    # 6. progress was updated by the answer flow itself
    topic = client.get(f"/progress/{learner['id']}").json()["topics"][0]
    assert topic["section_code"] == "7.1"
    assert topic["questions_attempted"] == 3
    assert topic["questions_correct"] == 0
    assert topic["accuracy"] == 0.0
    assert topic["struggle_level"] == "High"
    assert topic["struggle_score"] == decision["struggle_score"]
    assert topic["completed"] is False

    profile = db_session.query(LearningProfile).filter_by(learner_id=learner["id"]).one()
    assert profile.struggle_level == "High"
    assert profile.current_difficulty == "EASY"

    # 8. scaffolding: progressive, answer only at level 4
    correct_answer = _correct(client, qids[2])
    levels = []
    for expected in (1, 2, 3, 4):
        step = _scaffold(client, aid, qids[2])
        levels.append(step["level_name"])
        assert step["level"] == expected
        assert (step["correct_answer"] is not None) == (expected == 4)
        if expected < 4:
            assert correct_answer not in step["content"]
    assert levels == ["HINT", "CONCEPT_REMINDER", "WORKED_STEPS", "FINAL_EXPLANATION"]

    # loop: next recommended question lives in a new adaptive assessment
    nxt = client.post(
        "/adaptation/next-question",
        json={"assessment_id": aid, "question_id": qids[2]},
    )
    assert nxt.status_code == 200
    nxt = nxt.json()
    assert nxt["next_assessment_id"] and nxt["next_assessment_id"] != aid
    next_qid = nxt["recommended_question"]["id"]

    again = client.post(
        "/adaptation/next-question",
        json={"assessment_id": aid, "question_id": qids[2]},
    ).json()
    assert again["next_assessment_id"] == nxt["next_assessment_id"]     # idempotent

    # ... the learner answers it through the normal answer endpoint (repeat)
    retry = _answer(
        client, nxt["next_assessment_id"], next_qid, _correct(client, next_qid), seconds=10
    )
    assert retry.status_code == 200
    assert retry.json()["correct"] is True

    after = client.get(f"/progress/{learner['id']}").json()["topics"][0]
    assert after["questions_attempted"] == 4
    assert after["questions_correct"] == 1
    assert after["accuracy"] == 25.0

    # finish the baseline assessment
    _answer(client, aid, qids[3], "definitely wrong")
    _answer(client, aid, qids[4], "definitely wrong")

    # 9. final assessment result (post-assessment report)
    result = client.get(f"/assessments/{aid}/result").json()
    assert result["status"] == "Completed"
    assert result["score"] == 0
    assert result["total_marks"] == 5
    assert result["accuracy"] == 0.0
    assert result["total_questions"] == 5
    assert result["questions_answered"] == 5
    assert result["struggle_level"] == "High"
    assert result["struggle_score"] is not None
    assert result["mastery_level"] == "Beginner"
    assert [w["section_code"] for w in result["weak_topics"]] == ["7.1"]
    assert result["weak_topics"][0]["questions_attempted"] == 5
    assert result["recommended_action"] == "REVISIT_PREREQUISITES"
    assert result["next_difficulty"] == "EASY"
    assert result["recommended_content"]["section_code"] == "7.1"
    assert result["reason"] and result["rules_applied"]

    # 10. progress summary
    summary = client.get(f"/progress/{learner['id']}/summary").json()
    assert summary["questions_attempted"] == 6
    assert summary["questions_correct"] == 1
    assert summary["topics_completed"] == 0
    assert summary["struggle_level"] == "High"
    assert [w["section_code"] for w in summary["weak_topics"]] == ["7.1"]
    assert summary["recommended_action"] == "PRACTISE_WEAK_TOPIC"
    assert summary["recommended_topic"]["section_code"] == "7.1"


def test_strong_learner_full_adaptive_loop(client, seeded, db_session):
    learner = _learner(client, "Ravi")
    assessment = _start(client, learner["id"])
    aid = assessment["assessment_id"]
    qids = assessment["questions"]

    decisions = []
    for qid in qids:
        response = _answer(client, aid, qid, _correct(client, qid), seconds=12)
        assert response.json() == {"question_id": qid, "correct": True}
        decisions.append(_evaluate(client, aid, qid))

    # struggle stays Low; difficulty rises, then the loop moves to the next topic
    assert all(d["struggle_level"] == "Low" for d in decisions)
    assert [d["action"] for d in decisions] == [
        "CONTINUE",
        "CONTINUE",
        "INCREASE_DIFFICULTY",
        "INCREASE_DIFFICULTY",
        "ADVANCE_TOPIC",
    ]
    assert decisions[2]["next_difficulty"] == "MEDIUM"
    assert decisions[4]["recommended_content"]["section_code"] == "7.2"
    assert decisions[4]["recommended_question"]["unit_id"] == decisions[4]["recommended_content"]["unit_id"]

    # progress: topic completed
    topic = client.get(f"/progress/{learner['id']}").json()["topics"][0]
    assert topic["questions_attempted"] == 5
    assert topic["questions_correct"] == 5
    assert topic["accuracy"] == 100.0
    assert topic["completed"] is True

    # scaffolding is not offered after a correct answer
    refused = client.post(
        "/adaptation/scaffold", json={"assessment_id": aid, "question_id": qids[0]}
    )
    assert refused.status_code == 409

    # final result
    result = client.get(f"/assessments/{aid}/result").json()
    assert result["status"] == "Completed"
    assert result["score"] == 5
    assert result["total_marks"] == 5
    assert result["accuracy"] == 100.0
    assert result["struggle_level"] == "Low"
    assert result["mastery_level"] == "Proficient"
    assert result["weak_topics"] == []
    assert result["recommended_action"] == "ADVANCE_TO_NEXT_TOPIC"
    assert result["next_difficulty"] == "EASY"
    assert result["recommended_content"]["section_code"] == "7.2"

    # baseline stored on learner and learning profile
    db_session.expire_all()
    stored = db_session.query(Learner).filter_by(id=learner["id"]).one()
    assert stored.baseline_score == 100.0
    assert stored.mastery_level == "Proficient"

    profile = db_session.query(LearningProfile).filter_by(learner_id=learner["id"]).one()
    assert profile.baseline_score == 100.0
    assert profile.mastery_level == "Proficient"

    # summary
    summary = client.get(f"/progress/{learner['id']}/summary").json()
    assert summary["topics_completed"] == 1
    assert summary["completed_topics"] == ["7.1 Fractional Units and Equal Shares"]
    assert summary["accuracy"] == 100.0
    assert summary["mastery_level"] == "Proficient"
    assert summary["weak_topics"] == []
    assert summary["recommended_action"] == "CONTINUE_NEXT_TOPIC"
    assert summary["recommended_topic"]["section_code"] == "7.2"


def test_medium_performance_gets_practise_recommendation(client, seeded):
    learner = _learner(client, "Meera")
    assessment = _start(client, learner["id"])
    aid = assessment["assessment_id"]
    qids = assessment["questions"]

    for qid in qids[:3]:
        _answer(client, aid, qid, _correct(client, qid))
    for qid in qids[3:]:
        _answer(client, aid, qid, "definitely wrong")

    result = client.get(f"/assessments/{aid}/result").json()

    assert result["score"] == 3
    assert result["accuracy"] == 60.0
    assert result["struggle_level"] == "Medium"
    assert result["weak_topics"] == []
    assert result["recommended_action"] == "PRACTISE_WEAK_TOPICS"
    assert result["next_difficulty"] == "MEDIUM"
    assert result["recommended_content"]["section_code"] == "7.1"
    assert result["mastery_level"] == "Developing"


def test_partial_assessment_result_is_provisional(client, seeded, db_session):
    learner = _learner(client, "Kabir")
    assessment = _start(client, learner["id"])
    aid = assessment["assessment_id"]

    empty = client.get(f"/assessments/{aid}/result").json()
    assert empty["recommended_action"] == "CONTINUE_ASSESSMENT"
    assert empty["questions_answered"] == 0
    assert empty["weak_topics"] == []
    assert empty["struggle_level"] is None

    qid = assessment["questions"][0]
    _answer(client, aid, qid, _correct(client, qid))

    partial = client.get(f"/assessments/{aid}/result").json()
    assert partial["status"] == "In Progress"
    assert partial["questions_answered"] == 1
    assert partial["total_questions"] == 5
    assert partial["struggle_level"] == "Low"

    # an unfinished baseline does not set the baseline score
    db_session.expire_all()
    assert db_session.query(Learner).filter_by(id=learner["id"]).one().baseline_score == 0


def test_result_for_unknown_assessment_is_404(client, seeded):
    assert client.get("/assessments/9999/result").status_code == 404


def test_swagger_and_openapi_list_all_loop_endpoints(client):
    assert client.get("/docs").status_code == 200

    paths = client.get("/openapi.json").json()["paths"]
    for path in (
        "/learners/",
        "/assessments/start",
        "/assessments/{assessment_id}/answer",
        "/assessments/{assessment_id}/result",
        "/adaptation/evaluate",
        "/adaptation/next-question",
        "/adaptation/scaffold",
        "/progress/{learner_id}",
        "/progress/{learner_id}/summary",
        "/content/curriculum",
        "/questions/",
    ):
        assert path in paths, path
