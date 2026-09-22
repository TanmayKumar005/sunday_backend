def calculate_struggle_score(
    accuracy: float,
    recent_accuracy: float,
    repeated_mistakes: float,
    difficulty_factor: float
) -> float:

    struggle_score = (
        (1 - accuracy) * 0.35
        + (1 - recent_accuracy) * 0.30
        + repeated_mistakes * 0.20
        + difficulty_factor * 0.15
    )

    return round(struggle_score, 2)


def classify_struggle(
    struggle_score: float
) -> str:

    if struggle_score < 0.30:
        return "Low"

    elif struggle_score < 0.60:
        return "Medium"

    else:
        return "High"