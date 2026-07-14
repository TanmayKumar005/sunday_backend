from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import String

from app.core.database import Base


class Learner(Base):

    __tablename__ = "learners"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), nullable=False)

    grade = Column(String(20), nullable=False)

    subject = Column(String(100), nullable=False)

    baseline_score = Column(Float, default=0)

    mastery_level = Column(String(50), default="Beginner")

    created_at = Column(DateTime, default=datetime.utcnow)