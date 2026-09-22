from sqlalchemy.orm import Session

from app.models.learner import Learner
from app.schemas.learner import LearnerCreate

from app.services.learning_profile_service import (
    create_learning_profile
)


def create_learner(
    db: Session,
    learner: LearnerCreate
):

    new_learner = Learner(
        name=learner.name,
        grade=learner.grade,
        subject=learner.subject
    )

    db.add(new_learner)

    db.commit()

    db.refresh(new_learner)

    create_learning_profile(
        db,
        new_learner.id # type: ignore
    )

    return new_learner