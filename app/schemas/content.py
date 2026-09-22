from pydantic import BaseModel, ConfigDict


class ContentBase(BaseModel):
    chapter: str
    title: str
    concept: str
    explanation: str
    order: int
    difficulty: str


class ContentCreate(ContentBase):
    pass


class ContentResponse(ContentBase):
    unit_id: int

    model_config = ConfigDict(from_attributes=True)