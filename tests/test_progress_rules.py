"""Progress + post-assessment rules (pure, no database)."""

from dataclasses import replace

from app.ai.progress_rules import (
    ADVANCE_TO_NEXT_TOPIC,
    DEFAULT_PROGRESS_CONFIG,
    PRACTISE_WEAK_TOPICS,
    REVISIT_PREREQUISITES,
    TARGET_CURRENT,
    TARGET_NEXT,
    TARGET_PREREQUISITE,
    TARGET_WEAKEST,
    TopicStat,
    find_weak_topics,
    is_topic_complete,
    mastery_level_for,
    percentage,
    recommend_post_assessment,
)


def stat(unit, attempted, correct, order=None, completed=False):
    return TopicStat(unit, attempted, correct, f"7.{unit}", f"Topic {unit}", order or unit, completed)


def test_percentage():
    assert percentage(0, 0) == 0.0
    assert percentage(3, 4) == 75.0
    assert percentage(1, 3) == 33.33


def test_topic_stat_accuracy_property():
    assert stat(1, 4, 3).accuracy == 75.0
    assert stat(1, 0, 0).accuracy == 0.0


def test_topic_completion_needs_volume_accuracy_and_no_high_struggle():
    assert is_topic_complete(3, 3, "Low")
    assert is_topic_complete(5, 4, "Medium")           # 80%
    assert not is_topic_complete(2, 2, "Low")          # too few questions
    assert not is_topic_complete(5, 3, "Low")          # 60% < 70%
    assert not is_topic_complete(4, 4, "High")         # struggling right now


def test_completion_thresholds_are_configurable():
    strict = replace(DEFAULT_PROGRESS_CONFIG, min_questions_to_complete=5)
    assert not is_topic_complete(4, 4, "Low", strict)


def test_weak_topics_sorted_weakest_first_and_exclude_completed():
    stats = [
        stat(1, 4, 3),                       # 75%  fine
        stat(2, 4, 1),                       # 25%  weak
        stat(3, 3, 0),                       # 0%   weakest
        stat(4, 5, 0, completed=True),       # completed -> never weak
        stat(5, 0, 0),                       # nothing attempted -> not weak
    ]
    assert [w.unit_id for w in find_weak_topics(stats)] == [3, 2]


def test_weak_threshold_boundary():
    assert find_weak_topics([stat(1, 5, 3)]) == []              # exactly 60%
    assert len(find_weak_topics([stat(1, 5, 2)])) == 1          # 40%


def test_mastery_labels():
    assert mastery_level_for(0) == "Beginner"
    assert mastery_level_for(39.9) == "Beginner"
    assert mastery_level_for(40) == "Developing"
    assert mastery_level_for(74.9) == "Developing"
    assert mastery_level_for(75) == "Proficient"


# ---- post-assessment recommendation ---------------------------------------

def test_strong_low_struggle_advances_to_next_topic():
    advice = recommend_post_assessment(100, "Low", "HARD", [])
    assert advice.action == ADVANCE_TO_NEXT_TOPIC
    assert advice.target == TARGET_NEXT
    assert advice.next_difficulty == "EASY"           # new topics start easy


def test_high_struggle_revisits_prerequisites_even_with_decent_accuracy():
    advice = recommend_post_assessment(70, "High", "MEDIUM", [])
    assert advice.action == REVISIT_PREREQUISITES
    assert advice.target == TARGET_PREREQUISITE
    assert advice.next_difficulty == "EASY"


def test_low_accuracy_revisits_prerequisites():
    advice = recommend_post_assessment(40, "Medium", "MEDIUM", [stat(1, 5, 2)])
    assert advice.action == REVISIT_PREREQUISITES


def test_weak_topics_mean_practise_weakest_at_current_level():
    advice = recommend_post_assessment(55, "Medium", "MEDIUM", [stat(1, 5, 2)])
    assert advice.action == PRACTISE_WEAK_TOPICS
    assert advice.target == TARGET_WEAKEST
    assert advice.next_difficulty == "MEDIUM"


def test_good_but_not_secure_keeps_practising_current_topic():
    advice = recommend_post_assessment(60, "Medium", "MEDIUM", [])
    assert advice.action == PRACTISE_WEAK_TOPICS
    assert advice.target == TARGET_CURRENT


def test_strong_accuracy_with_medium_struggle_does_not_advance():
    advice = recommend_post_assessment(90, "Medium", "MEDIUM", [])
    assert advice.action == PRACTISE_WEAK_TOPICS


def test_strong_accuracy_but_a_weak_topic_does_not_advance():
    advice = recommend_post_assessment(85, "Low", "MEDIUM", [stat(2, 3, 1)])
    assert advice.action == PRACTISE_WEAK_TOPICS
    assert advice.target == TARGET_WEAKEST


def test_every_post_assessment_advice_is_explained_and_valid():
    for accuracy in (0, 49, 50, 79, 80, 100):
        for level in ("Low", "Medium", "High"):
            for difficulty in ("EASY", "MEDIUM", "HARD"):
                advice = recommend_post_assessment(accuracy, level, difficulty, [])
                assert advice.reason and advice.rules_applied
                assert advice.next_difficulty in ("EASY", "MEDIUM", "HARD")


def test_post_assessment_thresholds_are_configurable():
    lenient = replace(DEFAULT_PROGRESS_CONFIG, advance_accuracy=60.0)
    assert recommend_post_assessment(65, "Low", "EASY", [], lenient).action == ADVANCE_TO_NEXT_TOPIC
    assert recommend_post_assessment(65, "Low", "EASY", []).action == PRACTISE_WEAK_TOPICS
