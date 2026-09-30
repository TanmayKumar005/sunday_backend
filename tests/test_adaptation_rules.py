"""Struggle-index integration + signal computation (pure, no database)."""

from dataclasses import replace

from app.ai.adaptation_config import DEFAULT_CONFIG
from app.ai.recommendation import (
    AnswerRecord,
    CurrentAttempt,
    compute_signals,
    smoothed_accuracy,
)
from app.ai.struggle_index import calculate_struggle_score, classify_struggle


def rec(answer_id, correct, difficulty="MEDIUM", unit=1):
    return AnswerRecord(answer_id, unit, difficulty, correct)


def signals_for(history, index=-1, attempts=1, wrong=None, seconds=None, config=DEFAULT_CONFIG):
    current = history[index]
    if wrong is None:
        wrong = 0 if current.is_correct else 1
    return compute_signals(
        history,
        CurrentAttempt(current, attempts, wrong, seconds),
        config,
    )


def test_existing_struggle_formula_is_unchanged():
    assert calculate_struggle_score(0.40, 0.30, 0.70, 0.50) == 0.63
    assert classify_struggle(0.29) == "Low"
    assert classify_struggle(0.30) == "Medium"
    assert classify_struggle(0.60) == "High"


def test_signals_feed_the_existing_struggle_index():
    history = [rec(1, True), rec(2, False), rec(3, False)]
    s = signals_for(history)

    expected = calculate_struggle_score(
        accuracy=s.unit_accuracy,
        recent_accuracy=s.recent_accuracy,
        repeated_mistakes=s.repeated_mistakes,
        difficulty_factor=s.difficulty_factor,
    )

    # unit_accuracy etc. are rounded for display, so allow a tiny gap
    assert abs(s.base_struggle_score - expected) <= 0.01
    assert s.struggle_level == classify_struggle(s.struggle_score)


def test_one_wrong_answer_is_medium_not_high():
    s = signals_for([rec(1, False, "EASY")])
    assert s.struggle_level == "Medium"


def test_one_correct_answer_is_low():
    s = signals_for([rec(1, True, "EASY")])
    assert s.struggle_level == "Low"


def test_struggle_grows_with_more_wrong_answers():
    levels = []
    for n in (1, 2, 3):
        history = [rec(i, False, "MEDIUM") for i in range(1, n + 1)]
        levels.append(signals_for(history).struggle_level)
    assert levels == ["Medium", "Medium", "High"]

    scores = [
        signals_for([rec(i, False) for i in range(1, n + 1)]).struggle_score
        for n in (1, 2, 3)
    ]
    assert scores == sorted(scores) and len(set(scores)) == 3


def test_smoothing_moves_small_samples_toward_prior():
    assert smoothed_accuracy([False]) > 0.0
    assert smoothed_accuracy([True]) < 1.0
    many_wrong = smoothed_accuracy([False] * 20)
    assert many_wrong < 0.1


def test_recent_accuracy_uses_only_the_recent_window():
    history = [rec(i, False) for i in range(1, 6)] + [rec(i, True) for i in range(6, 11)]
    s = signals_for(history)            # current = newest (correct)
    assert s.recent_accuracy > s.unit_accuracy


def test_repeated_mistakes_count_other_wrong_answers_in_unit():
    one = signals_for([rec(1, False)])
    three = signals_for([rec(1, False), rec(2, False), rec(3, False)])
    assert one.repeated_mistakes == 0
    assert three.repeated_mistakes > one.repeated_mistakes


def test_wrong_retries_on_same_question_raise_repeated_mistakes():
    first = signals_for([rec(1, False)], attempts=1, wrong=1)
    retried = signals_for([rec(1, False)], attempts=3, wrong=3)
    assert retried.repeated_mistakes > first.repeated_mistakes
    assert retried.struggle_score > first.struggle_score


def test_repeated_mistakes_are_capped_at_one():
    s = signals_for([rec(1, False)], attempts=20, wrong=20)
    assert s.repeated_mistakes == 1.0


def test_only_the_same_unit_counts_for_unit_accuracy():
    history = [rec(1, False, unit=2), rec(2, False, unit=2), rec(3, True, unit=1)]
    s = signals_for(history)
    assert s.unit_accuracy > 0.75           # unit 1 has one correct answer


def test_difficulty_factor_comes_from_config():
    easy = signals_for([rec(1, False, "EASY")])
    hard = signals_for([rec(1, False, "HARD")])
    assert easy.difficulty_factor == 0.2
    assert hard.difficulty_factor == 0.8
    assert hard.struggle_score > easy.struggle_score


def test_slow_response_adds_penalty():
    fast = signals_for([rec(1, True, "EASY")], seconds=20)
    slow = signals_for([rec(1, True, "EASY")], seconds=200)
    assert not fast.is_slow and fast.time_adjustment == 0
    assert slow.is_slow and slow.time_adjustment == 0.05
    assert slow.struggle_score > fast.struggle_score


def test_missing_response_time_is_ignored():
    s = signals_for([rec(1, True, "EASY")], seconds=None)
    assert not s.is_slow and not s.is_possible_guess and s.time_adjustment == 0


def test_very_fast_wrong_answer_is_flagged_as_possible_guess():
    s = signals_for([rec(1, False, "EASY")], seconds=2)
    assert s.is_possible_guess
    assert not signals_for([rec(1, True, "EASY")], seconds=2).is_possible_guess


def test_correct_streak_counts_first_try_answers_only():
    history = [rec(1, True), rec(2, True), rec(3, True)]
    assert signals_for(history).correct_streak == 3
    assert signals_for(history, attempts=2, wrong=1).correct_streak == 0

    broken = [rec(1, True), rec(2, False), rec(3, True), rec(4, True)]
    assert signals_for(broken).correct_streak == 2


def test_score_is_capped_at_one():
    s = signals_for([rec(i, False, "HARD") for i in range(1, 30)], attempts=30, wrong=30, seconds=999)
    assert s.struggle_score <= 1.0


def test_config_is_adjustable():
    lenient = replace(DEFAULT_CONFIG, prior_accuracy=1.0, prior_weight=10.0)
    default = signals_for([rec(1, False), rec(2, False)])
    tuned = signals_for([rec(1, False), rec(2, False)], config=lenient)
    assert tuned.struggle_score < default.struggle_score
