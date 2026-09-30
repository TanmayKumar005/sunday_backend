from typing import Optional

from sqlalchemy.orm import Session

from app.ai.adaptation_config import (
    AdaptationConfig,
    DEFAULT_CONFIG,
    difficulty_rank,
)
from app.ai.recommendation import (
    AnswerRecord,
    CurrentAttempt,
    TARGET_CURRENT,
    TARGET_NEXT,
    TARGET_PREREQUISITE,
    compute_signals,
    recommend,
)
from app.ai.scaffolding import (
    MAX_LEVEL,
    ScaffoldContext,
    build_scaffold,
    next_level,
)
from app.models.assessment import Assessment, AssessmentAnswer
from app.models.content import Content
from app.models.learning_profile import LearningProfile
from app.models.question import Question
from app.schemas.question import QuestionResponse
from app.services.content_service import (
    get_content,
    get_content_by_section,
    get_next_content,
)
from app.services.learning_profile_service import create_learning_profile


class AdaptationNotFound(Exception):
    """Assessment, question or answer does not exist / does not match."""


class AdaptationConflict(Exception):
    """Request is valid but not allowed in the current state."""


def _load_attempt(db: Session, assessment_id: int, question_id: int):

    assessment = (
        db.query(Assessment).filter(Assessment.id == assessment_id).first()
    )

    if assessment is None:
        raise AdaptationNotFound("Assessment not found")

    if question_id not in (assessment.question_ids or []):
        raise AdaptationNotFound("Question is not part of this assessment")

    question = db.query(Question).filter(Question.id == question_id).first()

    if question is None:
        raise AdaptationNotFound("Question not found")

    answer = (
        db.query(AssessmentAnswer)
        .filter(
            AssessmentAnswer.assessment_id == assessment_id,
            AssessmentAnswer.question_id == question_id,
        )
        .first()
    )

    if answer is None:
        raise AdaptationConflict(
            "Submit an answer to this question before requesting adaptation"
        )

    return assessment, question, answer


def _learner_history(db: Session, learner_id: int):
    """All of a learner's answers across assessments, as AnswerRecords."""

    rows = (
        db.query(AssessmentAnswer, Question)
        .join(Assessment, Assessment.id == AssessmentAnswer.assessment_id)
        .join(Question, Question.id == AssessmentAnswer.question_id)
        .filter(Assessment.learner_id == learner_id)
        .all()
    )

    return [
        AnswerRecord(
            answer_id=int(a.id),
            unit_id=int(q.unit_id),
            difficulty=str(q.difficulty),
            is_correct=bool(a.is_correct),
        )
        for a, q in rows
    ], {int(a.question_id) for a, _ in rows}


def _brief(unit: Optional[Content]):
    if unit is None:
        return None

    return {
        "unit_id": unit.unit_id,
        "section_code": unit.section_code,
        "topic": unit.topic,
        "title": unit.title,
        "learning_objective": unit.learning_objective,
    }


def select_question(
    db: Session,
    unit_id: int,
    difficulty: str,
    answered_question_ids: set,
    exclude_question_id: Optional[int] = None,
):
    """Pick the best next question in a unit.

    Preference: closest to the target difficulty, then not answered yet,
    then lowest id. Never returns the question just answered. If the bank has
    no unanswered question at the target level, an answered one is reused.
    """

    candidates = db.query(Question).filter(Question.unit_id == unit_id).all()

    candidates = [
        q for q in candidates
        if exclude_question_id is None or q.id != exclude_question_id
    ]

    if not candidates:
        return None

    target = difficulty_rank(difficulty)

    def rank(q):
        try:
            distance = abs(difficulty_rank(str(q.difficulty)) - target)
        except ValueError:
            distance = 99
        return (distance, 1 if q.id in answered_question_ids else 0, q.id)

    return sorted(candidates, key=rank)[0]


def _get_profile(db: Session, learner_id: int):
    profile = (
        db.query(LearningProfile)
        .filter(LearningProfile.learner_id == learner_id)
        .first()
    )

    if profile is None:
        profile = create_learning_profile(db, learner_id)

    return profile


def evaluate_answer(
    db: Session,
    assessment_id: int,
    question_id: int,
    config: AdaptationConfig = DEFAULT_CONFIG,
) -> dict:
    """Score struggle for a submitted answer and recommend the next step.

    Also stores the resulting struggle level and next difficulty on the
    learner's learning profile.
    """

    assessment, question, answer = _load_attempt(
        db, assessment_id, question_id
    )

    learner_id = int(assessment.learner_id)

    history, answered_ids = _learner_history(db, learner_id)

    current = CurrentAttempt(
        record=AnswerRecord(
            answer_id=int(answer.id),
            unit_id=int(question.unit_id),
            difficulty=str(question.difficulty),
            is_correct=bool(answer.is_correct),
        ),
        attempts=int(answer.attempts or 1),
        wrong_attempts=int(answer.wrong_attempts or 0),
        response_time_seconds=answer.response_time_seconds,
    )

    signals = compute_signals(history, current, config)
    decision = recommend(signals, config)

    unit = get_content(db, int(question.unit_id))

    target_unit = unit
    revisit = None

    if decision.topic_target == TARGET_NEXT and unit is not None:
        target_unit = get_next_content(db, int(unit.unit_id))

    elif decision.topic_target == TARGET_PREREQUISITE and unit is not None:
        code = unit.section_code
        prerequisite_code = config.prerequisites.get(code) if code else None

        revisit = unit        # no earlier concept: revisit this one

        if prerequisite_code:
            revisit = get_content_by_section(db, prerequisite_code) or unit

        target_unit = revisit

    reason = decision.reason

    if decision.topic_target == TARGET_NEXT and target_unit is None:
        reason += " There is no later section in this chapter: chapter complete."

    next_question = None

    if target_unit is not None:
        next_question = select_question(
            db,
            int(target_unit.unit_id),
            decision.next_difficulty,
            answered_ids,
            exclude_question_id=int(question.id),
        )

    profile = _get_profile(db, learner_id)
    profile.struggle_level = signals.struggle_level   # type: ignore
    profile.current_difficulty = decision.next_difficulty   # type: ignore
    db.commit()

    return {
        "assessment_id": assessment_id,
        "learner_id": learner_id,
        "question_id": question_id,
        "is_correct": signals.is_correct,
        "struggle_score": signals.struggle_score,
        "struggle_level": signals.struggle_level,
        "signals": {
            "unit_accuracy": signals.unit_accuracy,
            "recent_accuracy": signals.recent_accuracy,
            "repeated_mistakes": signals.repeated_mistakes,
            "difficulty_factor": signals.difficulty_factor,
            "response_time_seconds": signals.response_time_seconds,
            "is_slow": signals.is_slow,
            "is_possible_guess": signals.is_possible_guess,
            "correct_streak": signals.correct_streak,
            "attempts": signals.attempts,
            "wrong_attempts": signals.wrong_attempts,
            "base_struggle_score": signals.base_struggle_score,
            "time_adjustment": signals.time_adjustment,
        },
        "action": decision.action,
        "current_difficulty": signals.difficulty,
        "next_difficulty": decision.next_difficulty,
        "suggested_scaffold_level": decision.suggested_scaffold_level,
        "reason": reason,
        "rules_applied": decision.rules_applied,
        "recommended_content": _brief(target_unit),
        "revisit_prerequisite": _brief(revisit),
        "recommended_question": (
            QuestionResponse.model_validate(next_question)
            if next_question is not None else None
        ),
        "profile": {
            "struggle_level": str(profile.struggle_level),
            "current_difficulty": str(profile.current_difficulty),
        },
    }


def request_scaffold(db: Session, assessment_id: int, question_id: int) -> dict:
    """Give the NEXT scaffold level for a question (1 -> 4), one at a time.

    Only allowed after an incorrect answer, so the final explanation cannot
    be pulled up before the learner has tried.
    """

    _, question, answer = _load_attempt(db, assessment_id, question_id)

    if bool(answer.is_correct):
        raise AdaptationConflict(
            "Scaffolding is only offered after an incorrect answer"
        )

    level = next_level(int(answer.scaffold_level or 0))

    answer.scaffold_level = level   # type: ignore
    db.commit()

    unit = get_content(db, int(question.unit_id))

    context = ScaffoldContext(
        concept=str(question.concept),
        question_type=str(question.question_type or "MCQ"),
        correct_answer=str(question.correct_answer),
        explanation=question.explanation,   # type: ignore
        hint=question.hint,   # type: ignore
        section_code=unit.section_code if unit else None,   # type: ignore
        section_explanation=unit.explanation if unit else None,   # type: ignore
        learning_objective=unit.learning_objective if unit else None,   # type: ignore
    )

    step = build_scaffold(level, context)

    return {
        "assessment_id": assessment_id,
        "question_id": question_id,
        "level": step.level,
        "level_name": step.level_name,
        "title": step.title,
        "content": step.content,
        "steps": step.steps,
        "reveals_answer": step.reveals_answer,
        "correct_answer": step.correct_answer,
        "is_final_level": level >= MAX_LEVEL,
        "next_level": None if level >= MAX_LEVEL else level + 1,
    }
