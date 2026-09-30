from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.adaptation import (
    AdaptationDecision,
    EvaluateRequest,
    ScaffoldRequest,
    ScaffoldResponse,
)
from app.services.adaptation_service import (
    AdaptationConflict,
    AdaptationNotFound,
    evaluate_answer,
    request_scaffold,
)


router = APIRouter(
    prefix="/adaptation",
    tags=["Adaptation"]
)


@router.post("/evaluate", response_model=AdaptationDecision)
def evaluate(
    request: EvaluateRequest,
    db: Session = Depends(get_db)
):
    """Struggle score + recommended next step for an answered question.

    Call after POST /assessments/{id}/answer.
    """

    try:
        return evaluate_answer(
            db, request.assessment_id, request.question_id
        )
    except AdaptationNotFound as error:
        raise HTTPException(status_code=404, detail=str(error))
    except AdaptationConflict as error:
        raise HTTPException(status_code=409, detail=str(error))


@router.post("/scaffold", response_model=ScaffoldResponse)
def scaffold(
    request: ScaffoldRequest,
    db: Session = Depends(get_db)
):
    """Next scaffold level (1 hint, 2 concept, 3 worked steps, 4 solution).

    Each call reveals one more level; the answer appears only at level 4.
    """

    try:
        return request_scaffold(
            db, request.assessment_id, request.question_id
        )
    except AdaptationNotFound as error:
        raise HTTPException(status_code=404, detail=str(error))
    except AdaptationConflict as error:
        raise HTTPException(status_code=409, detail=str(error))
