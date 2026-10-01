from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.schemas.adaptation import ContentBrief


class TopicProgress(BaseModel):
    unit_id: int
    section_code: Optional[str] = None
    topic: Optional[str] = None
    questions_attempted: int
    questions_correct: int
    accuracy: float
    current_difficulty: str
    struggle_score: float
    struggle_level: str
    completed: bool
    last_activity: Optional[datetime] = None


class WeakTopic(BaseModel):
    unit_id: int
    section_code: Optional[str] = None
    topic: Optional[str] = None
    questions_attempted: int
    questions_correct: int
    accuracy: float


class LearnerProgressResponse(BaseModel):
    learner_id: int
    topics: List[TopicProgress]


class ProgressSummary(BaseModel):
    learner_id: int
    learner_name: str

    total_topics: int
    topics_started: int
    topics_completed: int
    completed_topics: List[str]
    completion_percent: float

    questions_attempted: int
    questions_correct: int
    accuracy: float

    current_difficulty: str
    struggle_level: str
    struggle_score: Optional[float] = None
    mastery_level: str

    weak_topics: List[WeakTopic]
    last_activity: Optional[datetime] = None

    recommended_action: str
    recommended_topic: Optional[ContentBrief] = None
    reason: str
