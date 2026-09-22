from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.schemas.question import (
    QuestionCreate,
    QuestionResponse
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

    return create_question(
        db,
        question
    )


@router.get(
    "/",
    response_model=list[QuestionResponse]
)
def list_questions(
    db: Session = Depends(get_db)
):

    return get_questions(db)


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