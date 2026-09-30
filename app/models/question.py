from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import JSON
from sqlalchemy import Text

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
        ForeignKey("content.unit_id"),
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

    question_type = Column(
        String(20),
        nullable=False,
        default="MCQ",
        server_default="MCQ"
    )

    topic = Column(
        String(200),
        nullable=True
    )

    learning_objective = Column(
        Text,
        nullable=True
    )

    explanation = Column(
        Text,
        nullable=True
    )

    hint = Column(
        Text,
        nullable=True
    )
