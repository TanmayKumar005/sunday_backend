from pydantic import BaseModel, Field


class LearnerCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    grade: str
    subject: str


class LearnerResponse(BaseModel):
    id: int
    name: str
    grade: str
    subject: str
    baseline_score: float
    mastery_level: str

    class Config:
        from_attributes = True