def _unit_id(client, code="7.1"):
    return client.get(f"/content/sections/{code}").json()["unit_id"]


def test_list_questions_and_filters(client, seeded):
    all_q = client.get("/questions/").json()
    assert len(all_q) >= 40

    unit_id = _unit_id(client, "7.8")
    by_unit = client.get("/questions/", params={"unit_id": unit_id}).json()
    assert by_unit and all(q["unit_id"] == unit_id for q in by_unit)

    hard = client.get("/questions/", params={"difficulty": "hard"}).json()
    assert hard and all(q["difficulty"] == "HARD" for q in hard)

    numerical = client.get("/questions/", params={"question_type": "NUMERICAL"}).json()
    assert numerical and all(q["question_type"] == "NUMERICAL" and q["options"] == [] for q in numerical)


def test_get_single_question_hides_answer(client, seeded):
    first = client.get("/questions/").json()[0]
    response = client.get(f"/questions/{first['id']}")

    assert response.status_code == 200
    assert "correct_answer" not in response.json()
    assert client.get("/questions/99999").status_code == 404


def test_solution_endpoint(client, seeded):
    first = client.get("/questions/").json()[0]
    response = client.get(f"/questions/{first['id']}/solution")

    assert response.status_code == 200
    body = response.json()
    assert body["correct_answer"]
    assert body["explanation"]
    assert client.get("/questions/99999/solution").status_code == 404


def _new_question(unit_id, **overrides):
    payload = {
        "unit_id": unit_id,
        "concept": "Test",
        "question_text": "What is 1/2 + 1/2?",
        "options": ["1", "2", "1/4"],
        "correct_answer": "1",
        "difficulty": "easy",
        "question_type": "mcq",
        "explanation": "Two halves make one.",
    }
    payload.update(overrides)
    return payload


def test_create_question_inherits_topic(client, seeded):
    unit_id = _unit_id(client, "7.8")
    response = client.post("/questions/", json=_new_question(unit_id))

    assert response.status_code == 200
    body = response.json()
    assert body["difficulty"] == "EASY"
    assert body["question_type"] == "MCQ"
    assert body["topic"] == "Addition and Subtraction of Fractions"
    assert body["learning_objective"]


def test_create_question_unknown_unit_404(client, seeded):
    response = client.post("/questions/", json=_new_question(9999))
    assert response.status_code == 404


def test_create_question_validation(client, seeded):
    unit_id = _unit_id(client)

    wrong_answer = client.post(
        "/questions/", json=_new_question(unit_id, correct_answer="7")
    )
    assert wrong_answer.status_code == 422

    bad_difficulty = client.post(
        "/questions/", json=_new_question(unit_id, difficulty="Hardest")
    )
    assert bad_difficulty.status_code == 422

    bad_type = client.post(
        "/questions/", json=_new_question(unit_id, question_type="essay")
    )
    assert bad_type.status_code == 422

    one_option_mcq = client.post(
        "/questions/", json=_new_question(unit_id, options=["1"])
    )
    assert one_option_mcq.status_code == 422


def test_numerical_question_needs_no_options(client, seeded):
    unit_id = _unit_id(client)
    response = client.post(
        "/questions/",
        json=_new_question(
            unit_id,
            question_type="NUMERICAL",
            options=[],
            correct_answer="3",
            question_text="How many thirds make 1?",
        ),
    )
    assert response.status_code == 200
    assert response.json()["options"] == []


def test_existing_assessment_flow_still_works_with_seeded_questions(client, seeded):
    learner = client.post(
        "/learners/", json={"name": "Asha", "grade": "6", "subject": "Mathematics"}
    ).json()

    started = client.post("/assessments/start", json={"learner_id": learner["id"]})
    assert started.status_code == 200
    assessment = started.json()
    assert len(assessment["questions"]) == 5

    question_id = assessment["questions"][0]
    answer = client.get(f"/questions/{question_id}/solution").json()["correct_answer"]

    submitted = client.post(
        f"/assessments/{assessment['assessment_id']}/answer",
        json={"question_id": question_id, "answer": answer},
    )
    assert submitted.status_code == 200
    assert submitted.json()["correct"] is True

    result = client.get(f"/assessments/{assessment['assessment_id']}/result")
    assert result.status_code == 200
    assert result.json()["score"] == 1
