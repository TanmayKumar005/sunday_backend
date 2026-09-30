from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.question import QuestionResponse


class EvaluateRequest(BaseModel):
    assessment_id: int
    question_id: int


class ScaffoldRequest(BaseModel):
    assessment_id: int
    question_id: int


class SignalsResponse(BaseModel):
    unit_accuracy: float
    recent_accuracy: float
    repeated_mistakes: float
    difficulty_factor: float
    response_time_seconds: Optional[float] = None
    is_slow: bool
    is_possible_guess: bool
    correct_streak: int
    attempts: int
    wrong_attempts: int
    base_struggle_score: float
    time_adjustment: float


class ContentBrief(BaseModel):
    unit_id: int
    section_code: Optional[str] = None
    topic: Optional[str] = None
    title: str
    learning_objective: Optional[str] = None


class ProfileSnapshot(BaseModel):
    struggle_level: str
    current_difficulty: str


class AdaptationDecision(BaseModel):
    assessment_id: int
    learner_id: int
    question_id: int
    is_correct: bool

    struggle_score: float
    struggle_level: str
    signals: SignalsResponse

    action: str
    current_difficulty: str
    next_difficulty: str
    suggested_scaffold_level: int
    reason: str
    rules_applied: List[str]

    recommended_content: Optional[ContentBrief] = None
    revisit_prerequisite: Optional[ContentBrief] = None
    recommended_question: Optional[QuestionResponse] = None

    profile: ProfileSnapshot


class ScaffoldResponse(BaseModel):
    assessment_id: int
    question_id: int
    level: int = Field(ge=1, le=4)
    level_name: str
    title: str
    content: str
    steps: List[str] = []
    reveals_answer: bool
    correct_answer: Optional[str] = None
    is_final_level: bool
    next_level: Optional[int] = None
