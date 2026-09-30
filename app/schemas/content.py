from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.constants import normalize_difficulty


class ContentBase(BaseModel):
    chapter: str
    title: str
    concept: str
    explanation: str
    order: int
    difficulty: str

    class_level: str = "Class 6"
    subject: str = "Mathematics"
    book: str = "Ganita Prakash"
    chapter_number: Optional[int] = None
    section_code: Optional[str] = None
    topic: Optional[str] = None
    learning_objective: Optional[str] = None


class ContentCreate(ContentBase):

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, value: str) -> str:
        return normalize_difficulty(value)


class ContentResponse(ContentBase):
    unit_id: int

    model_config = ConfigDict(from_attributes=True)


class SectionSummary(BaseModel):
    unit_id: int
    section_code: Optional[str] = None
    topic: Optional[str] = None
    title: str
    learning_objective: Optional[str] = None
    difficulty: str
    order: int
    question_count: int
    questions_by_difficulty: Dict[str, int]


class ChapterCurriculum(BaseModel):
    class_level: str
    subject: str
    book: str
    chapter_number: Optional[int] = None
    chapter: str
    sections: List[SectionSummary]
