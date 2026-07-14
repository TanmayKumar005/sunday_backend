from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.schemas.learner import (
    LearnerCreate,
    LearnerResponse
)

from app.services.learner_service import create_learner

router = APIRouter(
    prefix="/learners",
    tags=["Learners"]
)


@router.post(
    "/",
    response_model=LearnerResponse
)
def add_learner(
    learner: LearnerCreate,
    db: Session = Depends(get_db)
):

    return create_learner(
        db,
        learner
    )