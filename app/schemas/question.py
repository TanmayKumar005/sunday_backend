from typing import List

from pydantic import BaseModel


class QuestionCreate(BaseModel):

    unit_id: int

    concept: str

    question_text: str

    options: List[str]

    correct_answer: str

    difficulty: str

    marks: int = 1


class QuestionResponse(BaseModel):

    id: int

    unit_id: int

    concept: str

    question_text: str

    options: List[str]

    difficulty: str

    marks: int

    class Config:
        from_attributes = True