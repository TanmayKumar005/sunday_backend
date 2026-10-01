from datetime import datetime

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import UniqueConstraint

from app.core.database import Base


class LearnerProgress(Base):
    """One row per learner per topic (NCERT section)."""

    __tablename__ = "learner_progress"

    __table_args__ = (
        UniqueConstraint(
            "learner_id",
            "unit_id",
            name="uq_learner_unit_progress"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    learner_id = Column(
        Integer,
        ForeignKey("learners.id"),
        nullable=False,
        index=True
    )

    unit_id = Column(
        Integer,
        ForeignKey("content.unit_id"),
        nullable=False
    )

    section_code = Column(String(10), nullable=True)

    topic = Column(String(200), nullable=True)

    questions_attempted = Column(Integer, default=0)

    questions_correct = Column(Integer, default=0)

    # percentage 0-100 (same convention as Assessment.accuracy)
    accuracy = Column(Float, default=0)

    current_difficulty = Column(String(20), default="EASY")

    struggle_score = Column(Float, default=0)

    struggle_level = Column(String(30), default="Low")

    completed = Column(Boolean, default=False)

    last_activity = Column(DateTime, default=datetime.utcnow)
