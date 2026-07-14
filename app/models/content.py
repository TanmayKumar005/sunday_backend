from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text

from app.core.database import Base


class ContentUnit(Base):

    __tablename__ = "content_units"

    id = Column(Integer, primary_key=True, index=True)

    chapter = Column(String(100), nullable=False)

    concept = Column(String(100), nullable=False)

    micro_lesson = Column(Text, nullable=False)

    example = Column(Text, nullable=False)

    difficulty = Column(String(20), nullable=False)

    learning_outcome = Column(String(255), nullable=False)