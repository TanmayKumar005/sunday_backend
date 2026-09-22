from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import JSON

from app.core.database import Base


class Question(Base):

    __tablename__ = "questions"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    unit_id = Column(
        Integer,
        nullable=False
    )

    concept = Column(
        String(100),
        nullable=False
    )

    question_text = Column(
        String(500),
        nullable=False
    )

    options = Column(
        JSON,
        nullable=False
    )

    correct_answer = Column(
        String(100),
        nullable=False
    )

    difficulty = Column(
        String(20),
        nullable=False
    )

    marks = Column(
        Integer,
        default=1
    )