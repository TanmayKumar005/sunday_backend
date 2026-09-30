from sqlalchemy import Column, Integer, String, Text

from app.core.database import Base


class Content(Base):
    """One learning unit. For Fractions: one row per NCERT section (7.1 - 7.9)."""

    __tablename__ = "content"

    unit_id = Column(Integer, primary_key=True, index=True)

    # Curriculum hierarchy: class -> subject -> book -> chapter -> section(topic)
    class_level = Column(String(20), nullable=False, server_default="Class 6")
    subject = Column(String(100), nullable=False, server_default="Mathematics")
    book = Column(String(100), nullable=False, server_default="Ganita Prakash")
    chapter_number = Column(Integer, nullable=True)
    chapter = Column(String(100), nullable=False)
    section_code = Column(String(10), nullable=True, unique=True, index=True)
    topic = Column(String(200), nullable=True)
    learning_objective = Column(Text, nullable=True)

    title = Column(String(200), nullable=False)
    concept = Column(String(200), nullable=False)
    explanation = Column(Text, nullable=False)
    order = Column(Integer, nullable=False)
    difficulty = Column(String(20), nullable=False)
