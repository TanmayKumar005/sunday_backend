def test_list_units_ordered(client, seeded):
    response = client.get("/content/units")

    assert response.status_code == 200
    data = response.json()
    assert [u["section_code"] for u in data] == [
        "7.1", "7.2", "7.3", "7.4", "7.5", "7.6", "7.7", "7.8", "7.9"
    ]
    assert data[0]["class_level"] == "Class 6"
    assert data[0]["book"] == "Ganita Prakash"


def test_get_unit_and_section(client, seeded):
    by_section = client.get("/content/sections/7.3")
    assert by_section.status_code == 200
    body = by_section.json()
    assert body["topic"] == "Measuring Using Fractional Units"

    by_id = client.get(f"/content/units/{body['unit_id']}")
    assert by_id.status_code == 200
    assert by_id.json()["section_code"] == "7.3"


def test_missing_section_and_unit_404(client, seeded):
    assert client.get("/content/sections/7.10").status_code == 404
    assert client.get("/content/units/9999").status_code == 404
    assert client.get("/content/units/9999/questions").status_code == 404


def test_next_unit(client, seeded):
    first = client.get("/content/sections/7.1").json()
    nxt = client.get(f"/content/units/{first['unit_id']}/next")
    assert nxt.status_code == 200
    assert nxt.json()["section_code"] == "7.2"

    last = client.get("/content/sections/7.9").json()
    assert client.get(f"/content/units/{last['unit_id']}/next").status_code == 404


def test_curriculum_hierarchy(client, seeded):
    response = client.get("/content/curriculum")

    assert response.status_code == 200
    chapters = response.json()
    assert len(chapters) == 1
    chapter = chapters[0]
    assert chapter["chapter"] == "Fractions"
    assert chapter["chapter_number"] == 7
    assert len(chapter["sections"]) == 9
    for section in chapter["sections"]:
        assert section["question_count"] >= 3
        assert sum(section["questions_by_difficulty"].values()) == section["question_count"]


def test_unit_questions_hide_answers(client, seeded):
    unit = client.get("/content/sections/7.2").json()
    response = client.get(f"/content/units/{unit['unit_id']}/questions")

    assert response.status_code == 200
    questions = response.json()
    assert len(questions) >= 3
    for q in questions:
        assert q["unit_id"] == unit["unit_id"]
        assert "correct_answer" not in q
        assert "explanation" not in q
        assert q["question_type"] in ("MCQ", "NUMERICAL", "CONCEPTUAL")


def _payload(**overrides):
    payload = {
        "chapter": "Fractions",
        "title": "Extra",
        "concept": "Extra concept",
        "explanation": "Text",
        "order": 99,
        "difficulty": "easy",
    }
    payload.update(overrides)
    return payload


def test_create_content_normalises_difficulty(client, db_session):
    response = client.post("/content/", json=_payload())

    assert response.status_code == 200
    assert response.json()["difficulty"] == "EASY"


def test_create_content_rejects_bad_difficulty(client, db_session):
    response = client.post("/content/", json=_payload(difficulty="Beginner"))
    assert response.status_code == 422


def test_create_content_duplicate_section_409(client, seeded):
    response = client.post("/content/", json=_payload(section_code="7.1"))
    assert response.status_code == 409
