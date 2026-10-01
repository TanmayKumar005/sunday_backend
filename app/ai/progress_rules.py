"""Pure rules for progress tracking and post-assessment recommendations.

No database and no web framework, so every rule is unit-testable.
Accuracy values here are PERCENTAGES (0-100), matching Assessment.accuracy.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from app.ai.adaptation_config import DEFAULT_CONFIG as ADAPTATION_CONFIG
from app.ai.adaptation_config import difficulty_rank

# Post-assessment actions
ADVANCE_TO_NEXT_TOPIC = "ADVANCE_TO_NEXT_TOPIC"
PRACTISE_WEAK_TOPICS = "PRACTISE_WEAK_TOPICS"
REVISIT_PREREQUISITES = "REVISIT_PREREQUISITES"
CONTINUE_ASSESSMENT = "CONTINUE_ASSESSMENT"

# Where the recommended content should come from
TARGET_NEXT = "NEXT"
TARGET_WEAKEST = "WEAKEST"
TARGET_PREREQUISITE = "PREREQUISITE"
TARGET_CURRENT = "CURRENT"


@dataclass(frozen=True)
class ProgressConfig:
    # a topic counts as completed when ALL of these hold
    min_questions_to_complete: int = 3
    completion_accuracy: float = 70.0
    # topic is "weak" below this accuracy (and not completed)
    weak_topic_accuracy: float = 60.0
    weak_min_attempts: int = 1
    # post-assessment bands
    advance_accuracy: float = 80.0
    revisit_accuracy: float = 50.0
    # mastery label from baseline accuracy
    mastery_developing: float = 40.0
    mastery_proficient: float = 75.0


DEFAULT_PROGRESS_CONFIG = ProgressConfig()


@dataclass(frozen=True)
class TopicStat:
    unit_id: int
    attempted: int
    correct: int
    section_code: Optional[str] = None
    topic: Optional[str] = None
    order: int = 0
    completed: bool = False

    @property
    def accuracy(self) -> float:
        return percentage(self.correct, self.attempted)


@dataclass(frozen=True)
class PostAssessmentAdvice:
    action: str
    next_difficulty: str
    target: str
    reason: str
    rules_applied: List[str] = field(default_factory=list)


def percentage(correct: int, attempted: int) -> float:
    if attempted <= 0:
        return 0.0

    return round(correct / attempted * 100, 2)


def is_topic_complete(
    attempted: int,
    correct: int,
    struggle_level: str,
    config: ProgressConfig = DEFAULT_PROGRESS_CONFIG
) -> bool:
    """Enough questions, good accuracy and no current High struggle."""

    return (
        attempted >= config.min_questions_to_complete
        and percentage(correct, attempted) >= config.completion_accuracy
        and struggle_level != "High"
    )


def find_weak_topics(
    stats: Sequence[TopicStat],
    config: ProgressConfig = DEFAULT_PROGRESS_CONFIG
) -> List[TopicStat]:
    """Lowest accuracy first; completed topics are never weak."""

    weak = [
        s for s in stats
        if not s.completed
        and s.attempted >= config.weak_min_attempts
        and s.accuracy < config.weak_topic_accuracy
    ]

    return sorted(weak, key=lambda s: (s.accuracy, s.order))


def mastery_level_for(
    accuracy: float,
    config: ProgressConfig = DEFAULT_PROGRESS_CONFIG
) -> str:
    if accuracy >= config.mastery_proficient:
        return "Proficient"

    if accuracy >= config.mastery_developing:
        return "Developing"

    return "Beginner"


def recommend_post_assessment(
    accuracy: float,
    struggle_level: str,
    current_difficulty: str,
    weak_topics: Sequence[TopicStat],
    config: ProgressConfig = DEFAULT_PROGRESS_CONFIG
) -> PostAssessmentAdvice:
    """Final recommendation once an assessment has been answered."""

    difficulty = current_difficulty.strip().upper()
    difficulty_rank(difficulty)          # validates the value

    new_topic = ADAPTATION_CONFIG.new_topic_difficulty
    easiest = ADAPTATION_CONFIG.prerequisite_difficulty

    if struggle_level == "High" or accuracy < config.revisit_accuracy:
        return PostAssessmentAdvice(
            REVISIT_PREREQUISITES, easiest, TARGET_PREREQUISITE,
            "High struggle or low accuracy: revisit the prerequisite "
            "concept of the weakest topic and practise easier questions.",
            ["POST_HIGH_STRUGGLE_OR_LOW_ACCURACY_REVISIT"]
        )

    if (
        accuracy >= config.advance_accuracy
        and struggle_level == "Low"
        and not weak_topics
    ):
        return PostAssessmentAdvice(
            ADVANCE_TO_NEXT_TOPIC, new_topic, TARGET_NEXT,
            "Strong accuracy with low struggle: move on to the next "
            "topic (new topics start at the easiest level).",
            ["POST_STRONG_AND_LOW_STRUGGLE_ADVANCE"]
        )

    if weak_topics:
        return PostAssessmentAdvice(
            PRACTISE_WEAK_TOPICS, difficulty, TARGET_WEAKEST,
            "Some topics are below the target accuracy: practise the "
            "weakest topic at the current level.",
            ["POST_WEAK_TOPICS_PRACTISE"]
        )

    return PostAssessmentAdvice(
        PRACTISE_WEAK_TOPICS, difficulty, TARGET_CURRENT,
        "Good progress but not yet secure: keep practising at the "
        "current level before moving on.",
        ["POST_NOT_YET_SECURE_PRACTISE"]
    )
