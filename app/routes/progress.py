from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.progress import LearnerProgressResponse, ProgressSummary
from app.services.progress_service import get_progress, get_summary


router = APIRouter(
    prefix="/progress",
    tags=["Progress"]
)


@router.get("/{learner_id}", response_model=LearnerProgressResponse)
def learner_progress(
    learner_id: int,
    db: Session = Depends(get_db)
):
    """Per-topic progress for a learner (empty list if nothing answered yet)."""

    result = get_progress(db, learner_id)

    if result is None:
        raise HTTPException(status_code=404, detail="Learner not found")

    return result


@router.get("/{learner_id}/summary", response_model=ProgressSummary)
def learner_progress_summary(
    learner_id: int,
    db: Session = Depends(get_db)
):
    """Chapter-level summary: totals, completed and weak topics, next step."""

    result = get_summary(db, learner_id)

    if result is None:
        raise HTTPException(status_code=404, detail="Learner not found")

    return result
