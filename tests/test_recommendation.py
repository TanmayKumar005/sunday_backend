"""Decision rules (pure, no database)."""

from dataclasses import replace

from app.ai.adaptation_config import (
    DEFAULT_CONFIG,
    FRACTIONS_PREREQUISITES,
    step_down,
    step_up,
)
from app.ai.recommendation import (
    ADVANCE_TOPIC,
    CONTINUE,
    EASIER_QUESTION,
    HINT_AND_EASIER_QUESTION,
    HINT_AND_SIMILAR_QUESTION,
    INCREASE_DIFFICULTY,
    SCAFFOLD_AND_REVISIT_PREREQUISITE,
    SIMILAR_QUESTION,
    TARGET_CURRENT,
    TARGET_NEXT,
    TARGET_PREREQUISITE,
    Signals,
    recommend,
)


def make(level, correct, difficulty="MEDIUM", streak=0, attempts=1,
         wrong_attempts=None, repeated=0.0, slow=False, guess=False):
    if wrong_attempts is None:
        wrong_attempts = 0 if correct else 1
    return Signals(
        is_correct=correct, difficulty=difficulty, attempts=attempts,
        wrong_attempts=wrong_attempts, unit_accuracy=0.5, recent_accuracy=0.5,
        repeated_mistakes=repeated, difficulty_factor=0.5,
        response_time_seconds=None, is_slow=slow, is_possible_guess=guess,
        correct_streak=streak, base_struggle_score=0.0, time_adjustment=0.0,
        struggle_score=0.0, struggle_level=level,
    )


# ---- difficulty ladder -----------------------------------------------------

def test_difficulty_ladder_is_bounded():
    assert step_up("EASY") == "MEDIUM"
    assert step_up("HARD") == "HARD"
    assert step_down("HARD") == "MEDIUM"
    assert step_down("EASY") == "EASY"


def test_prerequisite_map_covers_every_section():
    assert set(FRACTIONS_PREREQUISITES) == {f"7.{i}" for i in range(1, 10)}
    assert FRACTIONS_PREREQUISITES["7.1"] is None
    assert FRACTIONS_PREREQUISITES["7.2"] == "7.1"
    assert FRACTIONS_PREREQUISITES["7.8"] == "7.6"


# ---- LOW -------------------------------------------------------------------

def test_low_correct_continues():
    r = recommend(make("Low", True, "MEDIUM", streak=1))
    assert (r.action, r.next_difficulty, r.topic_target) == (CONTINUE, "MEDIUM", TARGET_CURRENT)
    assert r.suggested_scaffold_level == 0


def test_low_correct_streak_increases_difficulty():
    r = recommend(make("Low", True, "EASY", streak=3))
    assert r.action == INCREASE_DIFFICULTY
    assert r.next_difficulty == "MEDIUM"
    assert r.topic_target == TARGET_CURRENT


def test_low_correct_streak_at_hard_advances_topic():
    r = recommend(make("Low", True, "HARD", streak=3))
    assert r.action == ADVANCE_TOPIC
    assert r.topic_target == TARGET_NEXT
    assert r.next_difficulty == "EASY"


def test_slow_answer_blocks_level_up():
    r = recommend(make("Low", True, "EASY", streak=3, slow=True))
    assert r.action == CONTINUE
    assert "slow" in r.reason.lower()


def test_low_wrong_continues_with_optional_hint():
    r = recommend(make("Low", False, "MEDIUM"))
    assert r.action == CONTINUE
    assert r.next_difficulty == "MEDIUM"
    assert r.suggested_scaffold_level == 1


# ---- MEDIUM ----------------------------------------------------------------

def test_medium_wrong_gives_hint_and_similar_question():
    r = recommend(make("Medium", False, "MEDIUM"))
    assert r.action == HINT_AND_SIMILAR_QUESTION
    assert r.next_difficulty == "MEDIUM"
    assert r.suggested_scaffold_level == 1
    assert r.topic_target == TARGET_CURRENT


def test_medium_wrong_with_repeated_mistakes_goes_slightly_easier():
    r = recommend(make("Medium", False, "HARD", repeated=0.33))
    assert r.action == HINT_AND_EASIER_QUESTION
    assert r.next_difficulty == "MEDIUM"          # one step, not straight to EASY
    assert r.suggested_scaffold_level == 1


def test_medium_wrong_on_easy_cannot_go_easier():
    r = recommend(make("Medium", False, "EASY", repeated=0.5))
    assert r.action == HINT_AND_SIMILAR_QUESTION
    assert r.next_difficulty == "EASY"


def test_medium_correct_consolidates_with_similar_question():
    r = recommend(make("Medium", True, "MEDIUM"))
    assert r.action == SIMILAR_QUESTION
    assert r.next_difficulty == "MEDIUM"
    assert r.suggested_scaffold_level == 0


# ---- HIGH ------------------------------------------------------------------

def test_high_wrong_scaffolds_and_revisits_prerequisite():
    r = recommend(make("High", False, "HARD"))
    assert r.action == SCAFFOLD_AND_REVISIT_PREREQUISITE
    assert r.topic_target == TARGET_PREREQUISITE
    assert r.next_difficulty == "EASY"
    assert r.suggested_scaffold_level == 2


def test_high_correct_steps_down_one_level():
    r = recommend(make("High", True, "HARD"))
    assert r.action == EASIER_QUESTION
    assert r.next_difficulty == "MEDIUM"
    assert r.topic_target == TARGET_CURRENT


# ---- general ---------------------------------------------------------------

def test_repeated_wrong_tries_escalate_scaffolding():
    r = recommend(make("Medium", False, "MEDIUM", attempts=3, wrong_attempts=3))
    assert r.suggested_scaffold_level == 3
    assert "ESCALATE_SCAFFOLD_AFTER_REPEATED_WRONG_TRIES" in r.rules_applied


def test_escalation_does_not_lower_a_higher_suggestion():
    cfg = replace(DEFAULT_CONFIG, scaffold_high_wrong=4)
    r = recommend(make("High", False, attempts=3, wrong_attempts=3), cfg)
    assert r.suggested_scaffold_level == 4


def test_possible_guess_is_noted_in_reason():
    r = recommend(make("Low", False, guess=True))
    assert "guess" in r.reason.lower()


def test_every_recommendation_explains_itself():
    for level in ("Low", "Medium", "High"):
        for correct in (True, False):
            for difficulty in ("EASY", "MEDIUM", "HARD"):
                r = recommend(make(level, correct, difficulty))
                assert r.reason and r.rules_applied
                assert r.next_difficulty in ("EASY", "MEDIUM", "HARD")
                assert 0 <= r.suggested_scaffold_level <= 4


def test_rules_are_configurable():
    cfg = replace(DEFAULT_CONFIG, streak_to_level_up=2)
    assert recommend(make("Low", True, "EASY", streak=2), cfg).action == INCREASE_DIFFICULTY
    assert recommend(make("Low", True, "EASY", streak=2)).action == CONTINUE
