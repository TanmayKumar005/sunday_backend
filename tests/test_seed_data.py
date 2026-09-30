"""Pure data checks - no database needed."""

from app.core.constants import DIFFICULTY_LEVELS, QUESTION_TYPES
from app.seed.fractions_content import FRACTIONS_CONTENT
from app.seed.fractions_questions import FRACTIONS_QUESTIONS

EXPECTED_SECTIONS = ["7.1", "7.2", "7.3", "7.4", "7.5", "7.6", "7.7", "7.8", "7.9"]


def test_all_nine_sections_present_and_ordered():
    codes = [c["section_code"] for c in FRACTIONS_CONTENT]
    assert codes == EXPECTED_SECTIONS
    assert [c["order"] for c in FRACTIONS_CONTENT] == list(range(1, 10))


def test_content_hierarchy_fields():
    for c in FRACTIONS_CONTENT:
        assert c["class_level"] == "Class 6"
        assert c["subject"] == "Mathematics"
        assert c["book"] == "Ganita Prakash"
        assert c["chapter_number"] == 7
        assert c["chapter"] == "Fractions"
        assert c["topic"] and c["learning_objective"] and c["explanation"]
        assert c["difficulty"] in DIFFICULTY_LEVELS


def test_every_section_has_questions():
    assert set(FRACTIONS_QUESTIONS) == set(EXPECTED_SECTIONS)
    for code, questions in FRACTIONS_QUESTIONS.items():
        assert len(questions) >= 3, code


def test_question_validity():
    seen = set()
    for questions in FRACTIONS_QUESTIONS.values():
        for q in questions:
            assert q["difficulty"] in DIFFICULTY_LEVELS
            assert q["question_type"] in QUESTION_TYPES
            assert q["explanation"]
            assert len(q["question_text"]) <= 500
            assert len(q["correct_answer"]) <= 100
            assert q["question_text"] not in seen
            seen.add(q["question_text"])
            if q["question_type"] == "NUMERICAL":
                assert q["options"] == []
            else:
                assert len(q["options"]) >= 2
                assert q["correct_answer"] in q["options"]


def test_mix_of_difficulties_and_types():
    all_q = [q for v in FRACTIONS_QUESTIONS.values() for q in v]
    assert {q["difficulty"] for q in all_q} == set(DIFFICULTY_LEVELS)
    assert {q["question_type"] for q in all_q} == set(QUESTION_TYPES)
