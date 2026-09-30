DIFFICULTY_LEVELS = ("EASY", "MEDIUM", "HARD")

QUESTION_TYPES = ("MCQ", "NUMERICAL", "CONCEPTUAL")


def normalize_difficulty(value: str) -> str:
    cleaned = value.strip().upper()

    if cleaned not in DIFFICULTY_LEVELS:
        raise ValueError(
            f"difficulty must be one of {', '.join(DIFFICULTY_LEVELS)}"
        )

    return cleaned


def normalize_question_type(value: str) -> str:
    cleaned = value.strip().upper()

    if cleaned not in QUESTION_TYPES:
        raise ValueError(
            f"question_type must be one of {', '.join(QUESTION_TYPES)}"
        )

    return cleaned
