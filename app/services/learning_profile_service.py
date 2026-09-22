from sqlalchemy.orm import Session

from app.models.learning_profile import LearningProfile


def create_learning_profile(
    db: Session,
    learner_id: int
):

    profile = LearningProfile(
        learner_id=learner_id
    )

    db.add(profile)

    db.commit()

    db.refresh(profile)

    return profile