from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query

from typing import Optional

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.schemas.question import (
    QuestionCreate,
    QuestionResponse,
    QuestionSolutionResponse
)

from app.services.question_service import (
    create_question,
    get_questions,
    get_question
)


router = APIRouter(
    prefix="/questions",
    tags=["Questions"]
)


@router.post(
    "/",
    response_model=QuestionResponse
)
def add_question(
    question: QuestionCreate,
    db: Session = Depends(get_db)
):

    created = create_question(
        db,
        question
    )

    if created is None:

        raise HTTPException(
            status_code=404,
            detail="Learning unit not found"
        )

    return created


@router.get(
    "/",
    response_model=list[QuestionResponse]
)
def list_questions(
    unit_id: Optional[int] = Query(None),
    difficulty: Optional[str] = Query(None),
    question_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):

    return get_questions(
        db,
        unit_id=unit_id,
        difficulty=difficulty,
        question_type=question_type
    )


@router.get(
    "/{question_id}",
    response_model=QuestionResponse
)
def get_single_question(
    question_id: int,
    db: Session = Depends(get_db)
):

    question = get_question(
        db,
        question_id
    )

    if question is None:

        raise HTTPException(
            status_code=404,
            detail="Question not found"
        )

    return question


@router.get(
    "/{question_id}/solution",
    response_model=QuestionSolutionResponse
)
def get_question_solution(
    question_id: int,
    db: Session = Depends(get_db)
):
    """Answer key + explanation (teacher/demo use)."""

    question = get_question(
        db,
        question_id
    )

    if question is None:

        raise HTTPException(
            status_code=404,
            detail="Question not found"
        )

    return question
