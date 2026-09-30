from typing import List, Optional

from pydantic import BaseModel, field_validator, model_validator

from app.core.constants import normalize_difficulty
from app.core.constants import normalize_question_type


class QuestionCreate(BaseModel):

    unit_id: int

    concept: str

    question_text: str

    options: List[str]

    correct_answer: str

    difficulty: str

    marks: int = 1

    question_type: str = "MCQ"

    topic: Optional[str] = None

    learning_objective: Optional[str] = None

    explanation: Optional[str] = None

    hint: Optional[str] = None

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, value: str) -> str:
        return normalize_difficulty(value)

    @field_validator("question_type")
    @classmethod
    def validate_question_type(cls, value: str) -> str:
        return normalize_question_type(value)

    @model_validator(mode="after")
    def validate_options_and_answer(self):

        if self.question_type in ("MCQ", "CONCEPTUAL"):
            if len(self.options) < 2:
                raise ValueError(
                    "MCQ and CONCEPTUAL questions need at least 2 options"
                )

        if self.options:
            cleaned = [o.strip().lower() for o in self.options]

            if self.correct_answer.strip().lower() not in cleaned:
                raise ValueError(
                    "correct_answer must be one of the options"
                )

        return self


class QuestionResponse(BaseModel):
    """Learner-facing view: never exposes the answer or explanation."""

    id: int

    unit_id: int

    concept: str

    question_text: str

    options: List[str]

    difficulty: str

    marks: int

    question_type: str = "MCQ"

    topic: Optional[str] = None

    learning_objective: Optional[str] = None

    class Config:
        from_attributes = True


class QuestionSolutionResponse(BaseModel):
    """Teacher/demo view including the answer key."""

    id: int

    correct_answer: str

    explanation: Optional[str] = None

    class Config:
        from_attributes = True
