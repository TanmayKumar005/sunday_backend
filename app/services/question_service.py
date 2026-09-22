from sqlalchemy.orm import Session

from app.models.question import Question
from app.schemas.question import QuestionCreate


def create_question(
    db: Session,
    question: QuestionCreate
):

    new_question = Question(
        unit_id=question.unit_id,
        concept=question.concept,
        question_text=question.question_text,
        options=question.options,
        correct_answer=question.correct_answer,
        difficulty=question.difficulty,
        marks=question.marks
    )

    db.add(new_question)

    db.commit()

    db.refresh(new_question)

    return new_question


def get_questions(
    db: Session
):

    return db.query(Question).all()


def get_question(
    db: Session,
    question_id: int
):

    return db.query(
        Question
    ).filter(
        Question.id == question_id
    ).first()