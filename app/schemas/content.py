from pydantic import BaseModel


class ContentCreate(BaseModel):

    chapter: str

    concept: str

    micro_lesson: str

    example: str

    difficulty: str

    learning_outcome: str


class ContentResponse(ContentCreate):

    id: int

    class Config:
        from_attributes = True