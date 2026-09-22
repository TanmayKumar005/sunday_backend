from sqlalchemy import Column, Integer, String, Text
from app.database import Base


class Content(Base):
    __tablename__ = "content"

    unit_id = Column(Integer, primary_key=True, index=True)
    chapter = Column(String(100), nullable=False)
    title = Column(String(200), nullable=False)
    concept = Column(String(200), nullable=False)
    explanation = Column(Text, nullable=False)
    order = Column(Integer, nullable=False)
    difficulty = Column(String(20), nullable=False)