from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import JSON

from app.core.database import Base


class Assessment(Base):

    __tablename__ = "assessments"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    learner_id = Column(
        Integer,
        ForeignKey("learners.id"),
        nullable=False
    )

    assessment_type = Column(
        String(30),
        default="Baseline"
    )

    question_ids = Column(
        JSON,
        nullable=False
    )

    score = Column(
        Float,
        default=0
    )

    total_marks = Column(
        Float,
        default=0
    )

    accuracy = Column(
        Float,
        default=0
    )

    status = Column(
        String(20),
        default="In Progress"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class AssessmentAnswer(Base):

    __tablename__ = "assessment_answers"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    assessment_id = Column(
        Integer,
        ForeignKey("assessments.id"),
        nullable=False
    )

    question_id = Column(
        Integer,
        ForeignKey("questions.id"),
        nullable=False
    )

    answer = Column(
        String(100),
        nullable=False
    )

    is_correct = Column(
        Integer,
        default=0
    )

    # Stage 2 adaptation signals
    response_time_seconds = Column(
        Float,
        nullable=True
    )

    attempts = Column(
        Integer,
        default=1,
        server_default="1"
    )

    wrong_attempts = Column(
        Integer,
        default=0,
        server_default="0"
    )

    scaffold_level = Column(
        Integer,
        default=0,
        server_default="0"
    )