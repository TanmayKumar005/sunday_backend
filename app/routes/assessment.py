from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.schemas.assessment import (
    StartAssessmentRequest,
    SubmitAnswerRequest,
    AssessmentStartResponse,
    AssessmentAnswerResponse,
    AssessmentResult
)

from app.services.adaptation_service import record_answer_outcome

from app.services.post_assessment_service import build_post_assessment

from app.services.assessment_service import (
    create_assessment,
    submit_answer,
    calculate_result
)


router = APIRouter(
    prefix="/assessments",
    tags=["Assessments"]
)


@router.post(
    "/start",
    response_model=AssessmentStartResponse
)
def start_assessment(
    request: StartAssessmentRequest,
    db: Session = Depends(get_db)
):

    assessment = create_assessment(
        db,
        request.learner_id,
        request.unit_id
    )

    if assessment is None:

        raise HTTPException(
            status_code=404,
            detail="No questions available"
        )

    return {
        "assessment_id": assessment.id,
        "learner_id": assessment.learner_id,
        "assessment_type": assessment.assessment_type,
        "questions": assessment.question_ids
    }


@router.post(
    "/{assessment_id}/answer",
    response_model=AssessmentAnswerResponse
)
def answer_question(
    assessment_id: int,
    request: SubmitAnswerRequest,
    db: Session = Depends(get_db)
):

    result = submit_answer(
        db,
        assessment_id,
        request.question_id,
        request.answer,
        request.response_time_seconds
    )

    if result is None:

        raise HTTPException(
            status_code=404,
            detail="Assessment or question not found"
        )

    # adaptive loop: struggle -> progress -> profile (response shape unchanged)
    record_answer_outcome(
        db,
        assessment_id,
        request.question_id
    )

    return result


@router.get(
    "/{assessment_id}/result",
    response_model=AssessmentResult
)
def get_result(
    assessment_id: int,
    db: Session = Depends(get_db)
):

    result = calculate_result(
        db,
        assessment_id
    )

    if result is None:

        raise HTTPException(
            status_code=404,
            detail="Assessment not found"
        )

    result.update(
        build_post_assessment(db, result)
    )

    return result