from app.ai.struggle_index import calculate_struggle_score
from app.ai.struggle_index import classify_struggle


def test_high_struggle():

    score = calculate_struggle_score(
        accuracy=0.40,
        recent_accuracy=0.30,
        repeated_mistakes=0.70,
        difficulty_factor=0.50
    )

    level = classify_struggle(score)

    assert score == 0.63
    assert level == "High"