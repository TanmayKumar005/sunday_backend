from app.models.assessment import Assessment
from app.models.content import Content
from app.models.learner import Learner
from app.models.question import Question
from app.seed.fractions_questions import FRACTIONS_QUESTIONS
from app.seed.seed_fractions import seed_fractions

TOTAL_QUESTIONS = sum(len(v) for v in FRACTIONS_QUESTIONS.values())


def test_seed_creates_content_and_questions(db_session):
    stats = seed_fractions(db_session)

    assert stats["content_created"] == 9
    assert stats["questions_created"] == TOTAL_QUESTIONS
    assert db_session.query(Content).count() == 9
    assert db_session.query(Question).count() == TOTAL_QUESTIONS


def test_seed_is_idempotent(db_session):
    seed_fractions(db_session)
    stats = seed_fractions(db_session)

    assert stats["content_created"] == 0
    assert stats["questions_created"] == 0
    assert db_session.query(Content).count() == 9
    assert db_session.query(Question).count() == TOTAL_QUESTIONS


def test_seed_keeps_learner_and_assessment_data(db_session):
    seed_fractions(db_session)

    learner = Learner(name="Asha", grade="6", subject="Mathematics")
    db_session.add(learner)
    db_session.commit()

    first_ids = [
        q.id for q in db_session.query(Question).order_by(Question.id).limit(5)
    ]
    db_session.add(Assessment(learner_id=learner.id, question_ids=first_ids))
    db_session.commit()

    seed_fractions(db_session)

    assert db_session.query(Learner).count() == 1
    assert db_session.query(Assessment).count() == 1
    kept = [
        q.id for q in db_session.query(Question).order_by(Question.id).limit(5)
    ]
    assert kept == first_ids


def test_questions_link_to_their_section(seeded):
    unit = seeded.query(Content).filter(Content.section_code == "7.6").one()
    questions = seeded.query(Question).filter(Question.unit_id == unit.unit_id).all()

    assert len(questions) == len(FRACTIONS_QUESTIONS["7.6"])
    assert all(q.topic == "Equivalent Fractions" for q in questions)
    assert all(q.learning_objective == unit.learning_objective for q in questions)
