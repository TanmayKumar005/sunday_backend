"""Tunable settings for the rule-based adaptation engine.

Everything the rules depend on lives here so behaviour can be changed
(or overridden in tests) without touching the rule code.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional

from app.core.constants import DIFFICULTY_LEVELS

# Fractions chapter: the concept a learner should revisit when struggling.
# Section 7.1 has no earlier concept, so it revisits itself.
FRACTIONS_PREREQUISITES: Dict[str, Optional[str]] = {
    "7.1": None,
    "7.2": "7.1",
    "7.3": "7.2",
    "7.4": "7.3",
    "7.5": "7.4",
    "7.6": "7.4",
    "7.7": "7.6",
    "7.8": "7.6",
    "7.9": "7.2",
}


@dataclass(frozen=True)
class AdaptationConfig:

    # --- evidence windows -------------------------------------------------
    recent_window: int = 5              # last N answers used for recent accuracy
    repeated_mistake_cap: int = 3       # this many repeat errors => factor 1.0

    # --- smoothing: stops 1 wrong answer from looking like "High" ----------
    # accuracy = (correct + prior_accuracy * prior_weight) / (n + prior_weight)
    prior_accuracy: float = 0.7
    prior_weight: float = 2.0

    # --- difficulty_factor fed to the existing struggle formula ------------
    difficulty_factor: Dict[str, float] = field(default_factory=lambda: {
        "EASY": 0.2,
        "MEDIUM": 0.5,
        "HARD": 0.8,
    })

    # --- response time ------------------------------------------------------
    expected_seconds: Dict[str, float] = field(default_factory=lambda: {
        "EASY": 30.0,
        "MEDIUM": 60.0,
        "HARD": 90.0,
    })
    slow_multiplier: float = 2.0        # slower than 2x expected => "slow"
    guess_multiplier: float = 0.2       # faster than 0.2x expected and wrong => "possible guess"
    slow_penalty: float = 0.05          # added to the struggle score when slow

    # --- decision rules -----------------------------------------------------
    streak_to_level_up: int = 3         # consecutive first-try correct answers
    new_topic_difficulty: str = "EASY"
    prerequisite_difficulty: str = "EASY"
    medium_step_down_attempts: int = 2  # Medium + wrong: go easier after this many tries
    escalate_scaffold_after_wrong_attempts: int = 3

    # suggested scaffold level (0 = none, 1 hint, 2 concept, 3 steps, 4 solution)
    scaffold_low_wrong: int = 1
    scaffold_medium_wrong: int = 1
    scaffold_high_wrong: int = 2
    escalated_scaffold_level: int = 3

    prerequisites: Dict[str, Optional[str]] = field(
        default_factory=lambda: dict(FRACTIONS_PREREQUISITES)
    )


DEFAULT_CONFIG = AdaptationConfig()


def difficulty_rank(difficulty: str) -> int:
    return DIFFICULTY_LEVELS.index(difficulty.strip().upper())


def step_up(difficulty: str) -> str:
    rank = min(difficulty_rank(difficulty) + 1, len(DIFFICULTY_LEVELS) - 1)
    return DIFFICULTY_LEVELS[rank]


def step_down(difficulty: str) -> str:
    rank = max(difficulty_rank(difficulty) - 1, 0)
    return DIFFICULTY_LEVELS[rank]
