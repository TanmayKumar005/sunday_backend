"""Transparent, rule-based adaptive recommendation.

Pure functions only (no database, no web framework), so every rule can be
unit-tested. Two steps:

1. compute_signals()  - turn answer history into the inputs of the EXISTING
   struggle index (app.ai.struggle_index) plus a few extra signals.
2. recommend()        - map the signals to an action using simple rules.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from app.ai.adaptation_config import (
    AdaptationConfig,
    DEFAULT_CONFIG,
    step_down,
    step_up,
)
from app.ai.struggle_index import calculate_struggle_score
from app.ai.struggle_index import classify_struggle
from app.core.constants import normalize_difficulty

# Actions
CONTINUE = "CONTINUE"
INCREASE_DIFFICULTY = "INCREASE_DIFFICULTY"
ADVANCE_TOPIC = "ADVANCE_TOPIC"
SIMILAR_QUESTION = "SIMILAR_QUESTION"
EASIER_QUESTION = "EASIER_QUESTION"
HINT_AND_SIMILAR_QUESTION = "HINT_AND_SIMILAR_QUESTION"
HINT_AND_EASIER_QUESTION = "HINT_AND_EASIER_QUESTION"
SCAFFOLD_AND_REVISIT_PREREQUISITE = "SCAFFOLD_AND_REVISIT_PREREQUISITE"

# Where the next learning step should come from
TARGET_CURRENT = "CURRENT"
TARGET_NEXT = "NEXT"
TARGET_PREREQUISITE = "PREREQUISITE"


@dataclass(frozen=True)
class AnswerRecord:
    """One learner answer (final state of a question in an assessment)."""
    answer_id: int
    unit_id: int
    difficulty: str
    is_correct: bool


@dataclass(frozen=True)
class CurrentAttempt:
    record: AnswerRecord
    attempts: int = 1
    wrong_attempts: int = 0
    response_time_seconds: Optional[float] = None


@dataclass(frozen=True)
class Signals:
    is_correct: bool
    difficulty: str
    attempts: int
    wrong_attempts: int
    unit_accuracy: float
    recent_accuracy: float
    repeated_mistakes: float
    difficulty_factor: float
    response_time_seconds: Optional[float]
    is_slow: bool
    is_possible_guess: bool
    correct_streak: int
    base_struggle_score: float
    time_adjustment: float
    struggle_score: float
    struggle_level: str


@dataclass(frozen=True)
class Recommendation:
    action: str
    next_difficulty: str
    topic_target: str
    suggested_scaffold_level: int
    reason: str
    rules_applied: List[str] = field(default_factory=list)


def smoothed_accuracy(
    outcomes: Sequence[bool],
    config: AdaptationConfig = DEFAULT_CONFIG
) -> float:
    """Accuracy pulled toward a prior so tiny samples are not extreme."""

    correct = sum(1 for outcome in outcomes if outcome)

    value = (
        (correct + config.prior_accuracy * config.prior_weight)
        / (len(outcomes) + config.prior_weight)
    )

    return round(value, 4)


def compute_signals(
    history: Sequence[AnswerRecord],
    current: CurrentAttempt,
    config: AdaptationConfig = DEFAULT_CONFIG
) -> Signals:
    """Build the struggle-index inputs from the learner's answers.

    `history` = all of the learner's answers (may include the current one).
    """

    difficulty = normalize_difficulty(current.record.difficulty)

    others = sorted(
        (r for r in history if r.answer_id != current.record.answer_id),
        key=lambda r: r.answer_id,
        reverse=True
    )

    ordered = [current.record] + others          # newest first

    recent = ordered[:config.recent_window]

    unit_records = [
        r for r in ordered if r.unit_id == current.record.unit_id
    ]

    unit_accuracy = smoothed_accuracy(
        [r.is_correct for r in unit_records], config
    )

    recent_accuracy = smoothed_accuracy(
        [r.is_correct for r in recent], config
    )

    # repeated mistakes: extra wrong answers in this unit + wrong retries
    unit_wrong = sum(1 for r in unit_records if not r.is_correct)
    retry_wrong = max(0, current.wrong_attempts - 1)

    repeated_mistakes = min(
        1.0,
        (max(0, unit_wrong - 1) + retry_wrong) / config.repeated_mistake_cap
    )

    difficulty_factor = config.difficulty_factor[difficulty]

    # consecutive first-try correct answers, newest first
    streak = 0

    if current.record.is_correct and current.attempts <= 1:
        for record in ordered:
            if record.is_correct:
                streak += 1
            else:
                break

    # the EXISTING struggle formula
    base_score = calculate_struggle_score(
        accuracy=unit_accuracy,
        recent_accuracy=recent_accuracy,
        repeated_mistakes=repeated_mistakes,
        difficulty_factor=difficulty_factor
    )

    seconds = current.response_time_seconds
    expected = config.expected_seconds[difficulty]

    is_slow = seconds is not None and seconds > expected * config.slow_multiplier

    is_possible_guess = (
        seconds is not None
        and not current.record.is_correct
        and seconds < expected * config.guess_multiplier
    )

    time_adjustment = config.slow_penalty if is_slow else 0.0

    final_score = round(min(1.0, base_score + time_adjustment), 2)

    return Signals(
        is_correct=current.record.is_correct,
        difficulty=difficulty,
        attempts=current.attempts,
        wrong_attempts=current.wrong_attempts,
        unit_accuracy=round(unit_accuracy, 2),
        recent_accuracy=round(recent_accuracy, 2),
        repeated_mistakes=round(repeated_mistakes, 2),
        difficulty_factor=difficulty_factor,
        response_time_seconds=seconds,
        is_slow=is_slow,
        is_possible_guess=is_possible_guess,
        correct_streak=streak,
        base_struggle_score=base_score,
        time_adjustment=time_adjustment,
        struggle_score=final_score,
        struggle_level=classify_struggle(final_score)
    )


def recommend(
    signals: Signals,
    config: AdaptationConfig = DEFAULT_CONFIG
) -> Recommendation:
    """Map signals to the next learning action (Low / Medium / High rules)."""

    level = signals.struggle_level
    difficulty = signals.difficulty
    correct = signals.is_correct

    if level == "Low":
        result = _low(signals, config)
    elif level == "Medium":
        result = _medium(signals, config)
    else:
        result = _high(signals, config)

    # Extra notes (do not change the action)
    notes = []

    if signals.is_slow:
        notes.append("Response was slow, so the struggle score was raised slightly.")

    if signals.is_possible_guess:
        notes.append("Very fast wrong answer: this may be a guess.")

    # Repeated wrong tries on one question escalate the support offered
    scaffold = result.suggested_scaffold_level
    rules = list(result.rules_applied)

    if (
        not correct
        and signals.wrong_attempts >= config.escalate_scaffold_after_wrong_attempts
        and scaffold < config.escalated_scaffold_level
    ):
        scaffold = config.escalated_scaffold_level
        rules.append("ESCALATE_SCAFFOLD_AFTER_REPEATED_WRONG_TRIES")
        notes.append(
            f"{signals.wrong_attempts} wrong tries on this question, "
            "so stronger support is suggested."
        )

    reason = " ".join([result.reason] + notes)

    return Recommendation(
        action=result.action,
        next_difficulty=result.next_difficulty,
        topic_target=result.topic_target,
        suggested_scaffold_level=scaffold,
        reason=reason,
        rules_applied=rules
    )


def _low(s: Signals, c: AdaptationConfig) -> Recommendation:

    if s.is_correct:

        if s.correct_streak >= c.streak_to_level_up and not s.is_slow:

            if s.difficulty != "HARD":
                return Recommendation(
                    INCREASE_DIFFICULTY, step_up(s.difficulty),
                    TARGET_CURRENT, 0,
                    f"Low struggle and {s.correct_streak} correct answers in a "
                    "row: make the questions harder.",
                    ["LOW_CORRECT_STREAK_INCREASE_DIFFICULTY"]
                )

            return Recommendation(
                ADVANCE_TOPIC, c.new_topic_difficulty, TARGET_NEXT, 0,
                "Low struggle and a streak of correct answers at HARD "
                "level: move on to the next topic.",
                ["LOW_CORRECT_STREAK_AT_HARD_ADVANCE_TOPIC"]
            )

        return Recommendation(
            CONTINUE, s.difficulty, TARGET_CURRENT, 0,
            "Low struggle and a correct answer: continue the current path.",
            ["LOW_CORRECT_CONTINUE"]
        )

    return Recommendation(
        CONTINUE, s.difficulty, TARGET_CURRENT, c.scaffold_low_wrong,
        "Low struggle overall, so this looks like an isolated mistake: "
        "continue the path, with an optional hint.",
        ["LOW_WRONG_CONTINUE_WITH_OPTIONAL_HINT"]
    )


def _medium(s: Signals, c: AdaptationConfig) -> Recommendation:

    if s.is_correct:
        return Recommendation(
            SIMILAR_QUESTION, s.difficulty, TARGET_CURRENT, 0,
            "Medium struggle but a correct answer: practise with a "
            "similar question at the same level to consolidate.",
            ["MEDIUM_CORRECT_SIMILAR_QUESTION"]
        )

    repeating = (
        s.repeated_mistakes > 0
        or s.attempts >= c.medium_step_down_attempts
    )

    if s.difficulty != "EASY" and repeating:
        return Recommendation(
            HINT_AND_EASIER_QUESTION, step_down(s.difficulty),
            TARGET_CURRENT, c.scaffold_medium_wrong,
            "Medium struggle with repeated mistakes: give a hint and a "
            "slightly easier question.",
            ["MEDIUM_WRONG_REPEATED_HINT_EASIER"]
        )

    return Recommendation(
        HINT_AND_SIMILAR_QUESTION, s.difficulty, TARGET_CURRENT,
        c.scaffold_medium_wrong,
        "Medium struggle: give a hint and a similar question at the "
        "same level.",
        ["MEDIUM_WRONG_HINT_SIMILAR"]
    )


def _high(s: Signals, c: AdaptationConfig) -> Recommendation:

    if s.is_correct:
        return Recommendation(
            EASIER_QUESTION, step_down(s.difficulty), TARGET_CURRENT, 0,
            "Correct answer, but recent struggle is high: consolidate "
            "with an easier question before moving up.",
            ["HIGH_CORRECT_EASIER_QUESTION"]
        )

    return Recommendation(
        SCAFFOLD_AND_REVISIT_PREREQUISITE, c.prerequisite_difficulty,
        TARGET_PREREQUISITE, c.scaffold_high_wrong,
        "High struggle: provide scaffolding, revisit the prerequisite "
        "concept and move to an easier question.",
        ["HIGH_WRONG_SCAFFOLD_REVISIT_PREREQUISITE"]
    )
