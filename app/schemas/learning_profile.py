from pydantic import BaseModel


class LearningProfileResponse(BaseModel):

    learner_id: int

    baseline_score: float

    mastery_level: str

    struggle_level: str

    learning_style: str

    attention_score: float

    memory_score: float

    processing_speed: float

    current_difficulty: str

    class Config:
        from_attributes = True