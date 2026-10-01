import logging
from dataclasses import dataclass
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
    Recommendation,
    Signals,
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
from app.services.progress_service import update_topic_progress

logger = logging.getLogger(__name__)

ADAPTIVE_ASSESSMENT_TYPE = "Adaptive"


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


@dataclass
class Analysis:
    """Everything computed for one answered question (no database writes)."""

    assessment: Assessment
    question: Question
    answer: AssessmentAnswer
    learner_id: int
    signals: Signals
    decision: Recommendation
    reason: str
    unit: Optional[Content]
    target_unit: Optional[Content]
    revisit: Optional[Content]
    next_question: Optional[Question]


def analyze_answer(
    db: Session,
    assessment_id: int,
    question_id: int,
    config: AdaptationConfig = DEFAULT_CONFIG,
) -> Analysis:
    """Struggle signals + recommendation for a submitted answer. Read-only."""

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

    return Analysis(
        assessment=assessment,
        question=question,
        answer=answer,
        learner_id=learner_id,
        signals=signals,
        decision=decision,
        reason=reason,
        unit=unit,
        target_unit=target_unit,
        revisit=revisit,
        next_question=next_question,
    )


def evaluate_answer(
    db: Session,
    assessment_id: int,
    question_id: int,
    config: AdaptationConfig = DEFAULT_CONFIG,
) -> dict:
    """Run one turn of the adaptive loop for a submitted answer.

    struggle calculated -> topic progress updated -> learning profile updated
    -> adaptation decision returned (with next content / question).

    Safe to call repeatedly: progress is recomputed, never incremented.
    """

    a = analyze_answer(db, assessment_id, question_id, config)

    signals = a.signals
    decision = a.decision

    # difficulty the learner is now working at IN THIS TOPIC
    topic_difficulty = (
        decision.next_difficulty
        if decision.topic_target == TARGET_CURRENT
        else signals.difficulty
    )

    update_topic_progress(
        db,
        a.learner_id,
        int(a.question.unit_id),
        signals.struggle_score,
        signals.struggle_level,
        topic_difficulty,
    )

    profile = _get_profile(db, a.learner_id)
    profile.struggle_level = signals.struggle_level   # type: ignore
    profile.current_difficulty = decision.next_difficulty   # type: ignore
    db.commit()

    return {
        "assessment_id": assessment_id,
        "learner_id": a.learner_id,
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
        "reason": a.reason,
        "rules_applied": decision.rules_applied,
        "recommended_content": _brief(a.target_unit),
        "revisit_prerequisite": _brief(a.revisit),
        "recommended_question": (
            QuestionResponse.model_validate(a.next_question)
            if a.next_question is not None else None
        ),
        "profile": {
            "struggle_level": str(profile.struggle_level),
            "current_difficulty": str(profile.current_difficulty),
        },
    }


def record_answer_outcome(
    db: Session,
    assessment_id: int,
    question_id: int,
) -> Optional[dict]:
    """Called by the answer endpoint after an answer is saved.

    Updates progress and the learning profile. A failure here must never
    lose or reject the learner's answer (already saved), so it is logged and
    swallowed.
    """

    try:
        return evaluate_answer(db, assessment_id, question_id)
    except Exception:
        db.rollback()
        logger.exception(
            "Adaptive update failed for assessment %s question %s",
            assessment_id,
            question_id,
        )
        return None


def _open_adaptive_assessment(
    db: Session,
    learner_id: int,
    question_id: int,
) -> Assessment:
    """Reuse or create a one-question Adaptive assessment for a learner."""

    open_ones = (
        db.query(Assessment)
        .filter(
            Assessment.learner_id == learner_id,
            Assessment.assessment_type == ADAPTIVE_ASSESSMENT_TYPE,
            Assessment.status == "In Progress",
        )
        .order_by(Assessment.id.desc())
        .limit(20)
        .all()
    )

    for existing in open_ones:
        if list(existing.question_ids or []) != [question_id]:
            continue

        answered = (
            db.query(AssessmentAnswer)
            .filter(AssessmentAnswer.assessment_id == existing.id)
            .count()
        )

        if answered == 0:
            return existing

    created = Assessment(
        learner_id=learner_id,
        assessment_type=ADAPTIVE_ASSESSMENT_TYPE,
        question_ids=[question_id],
        status="In Progress",
    )

    db.add(created)
    db.commit()
    db.refresh(created)

    return created


def next_question_assessment(
    db: Session,
    assessment_id: int,
    question_id: int,
    config: AdaptationConfig = DEFAULT_CONFIG,
) -> dict:
    """Evaluate the last answer AND open an assessment for the next question.

    The learner then answers the recommended question through the normal
    POST /assessments/{next_assessment_id}/answer endpoint, which closes
    the adaptive loop.
    """

    payload = evaluate_answer(db, assessment_id, question_id, config)

    recommended = payload["recommended_question"]

    payload["next_assessment_id"] = None

    if recommended is not None:
        adaptive = _open_adaptive_assessment(
            db, int(payload["learner_id"]), int(recommended.id)
        )
        payload["next_assessment_id"] = int(adaptive.id)

    return payload


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
