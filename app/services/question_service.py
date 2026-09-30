from typing import Optional

from sqlalchemy.orm import Session

from app.models.content import Content
from app.models.question import Question
from app.schemas.question import QuestionCreate


def create_question(
    db: Session,
    question: QuestionCreate
):

    unit = (
        db.query(Content)
        .filter(Content.unit_id == question.unit_id)
        .first()
    )

    if unit is None:
        return None

    new_question = Question(
        unit_id=question.unit_id,
        concept=question.concept,
        question_text=question.question_text,
        options=question.options,
        correct_answer=question.correct_answer,
        difficulty=question.difficulty,
        marks=question.marks,
        question_type=question.question_type,
        topic=question.topic or unit.topic,
        learning_objective=(
            question.learning_objective or unit.learning_objective
        ),
        explanation=question.explanation,
        hint=question.hint
    )

    db.add(new_question)

    db.commit()

    db.refresh(new_question)

    return new_question


def get_questions(
    db: Session,
    unit_id: Optional[int] = None,
    difficulty: Optional[str] = None,
    question_type: Optional[str] = None
):

    query = db.query(Question)

    if unit_id is not None:
        query = query.filter(Question.unit_id == unit_id)

    if difficulty:
        query = query.filter(
            Question.difficulty == difficulty.strip().upper()
        )

    if question_type:
        query = query.filter(
            Question.question_type == question_type.strip().upper()
        )

    return query.order_by(Question.id.asc()).all()


def get_question(
    db: Session,
    question_id: int
):

    return db.query(
        Question
    ).filter(
        Question.id == question_id
    ).first()
