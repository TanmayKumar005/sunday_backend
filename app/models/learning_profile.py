from sqlalchemy import Column
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String

from app.core.database import Base


class LearningProfile(Base):

    __tablename__ = "learning_profiles"

    id = Column(Integer, primary_key=True, index=True)

    learner_id = Column(
        Integer,
        ForeignKey("learners.id"),
        unique=True,
        nullable=False
    )

    baseline_score = Column(Float, default=0)

    mastery_level = Column(
        String(30),
        default="Beginner"
    )

    struggle_level = Column(
        String(30),
        default="Low"
    )

    learning_style = Column(
        String(30),
        default="Unknown"
    )

    attention_score = Column(Float, default=0)

    memory_score = Column(Float, default=0)

    processing_speed = Column(Float, default=0)

    current_difficulty = Column(
        String(20),
        default="Easy"
    )