from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.adaptation import ContentBrief
from app.schemas.progress import WeakTopic


class StartAssessmentRequest(BaseModel):

    learner_id: int
    unit_id: Optional[int] = None


class SubmitAnswerRequest(BaseModel):

    question_id: int

    answer: str

    response_time_seconds: Optional[float] = Field(
        default=None,
        ge=0
    )


class AssessmentStartResponse(BaseModel):

    assessment_id: int

    learner_id: int

    assessment_type: str

    questions: list[int]


class AssessmentAnswerResponse(BaseModel):

    question_id: int

    correct: bool


class AssessmentResult(BaseModel):

    assessment_id: int

    learner_id: int

    score: float

    total_marks: float

    accuracy: float

    status: str

    # --- post-assessment report (all optional, additive) ---
    total_questions: Optional[int] = None

    questions_answered: Optional[int] = None

    struggle_level: Optional[str] = None

    struggle_score: Optional[float] = None

    mastery_level: Optional[str] = None

    weak_topics: list[WeakTopic] = []

    recommended_action: Optional[str] = None

    next_difficulty: Optional[str] = None

    recommended_content: Optional[ContentBrief] = None

    reason: Optional[str] = None

    rules_applied: list[str] = []
