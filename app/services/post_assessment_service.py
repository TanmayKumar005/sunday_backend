from typing import Optional

from sqlalchemy.orm import Session

from app.ai.adaptation_config import DEFAULT_CONFIG as ADAPTATION_CONFIG
from app.ai.progress_rules import (
    CONTINUE_ASSESSMENT,
    DEFAULT_PROGRESS_CONFIG,
    TARGET_CURRENT,
    TARGET_NEXT,
    TARGET_PREREQUISITE,
    TARGET_WEAKEST,
    ProgressConfig,
    TopicStat,
    find_weak_topics,
    mastery_level_for,
    recommend_post_assessment,
)
from app.models.assessment import Assessment, AssessmentAnswer
from app.models.content import Content
from app.models.learner import Learner
from app.models.learning_profile import LearningProfile
from app.models.question import Question
from app.services.adaptation_service import analyze_answer
from app.services.content_service import get_next_content


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


def _by_section(db: Session, section_code: Optional[str]):
    if not section_code:
        return None

    return (
        db.query(Content)
        .filter(Content.section_code == section_code)
        .first()
    )


def build_post_assessment(
    db: Session,
    result: dict,
    config: ProgressConfig = DEFAULT_PROGRESS_CONFIG,
) -> dict:
    """Extra fields for GET /assessments/{id}/result.

    `result` is the dict from assessment_service.calculate_result.
    Adds struggle, weak topics, recommended action/content and next
    difficulty. When a Baseline assessment is Completed it also stores the
    baseline score and mastery level on the learner and learning profile.
    """

    assessment = (
        db.query(Assessment)
        .filter(Assessment.id == result["assessment_id"])
        .first()
    )

    question_ids = list(assessment.question_ids or [])   # type: ignore

    rows = (
        db.query(AssessmentAnswer, Question)
        .join(Question, Question.id == AssessmentAnswer.question_id)
        .filter(AssessmentAnswer.assessment_id == assessment.id)
        .order_by(AssessmentAnswer.id.asc())
        .all()
    )

    base = {
        "total_questions": len(question_ids),
        "questions_answered": len(rows),
        "weak_topics": [],
        "rules_applied": [],
        "recommended_content": None,
    }

    if not rows:
        base.update({
            "recommended_action": CONTINUE_ASSESSMENT,
            "reason": "No answers have been submitted yet.",
        })
        return base

    # --- per-topic performance inside THIS assessment --------------------
    counts: dict = {}

    for answer, question in rows:
        entry = counts.setdefault(int(question.unit_id), [0, 0])
        entry[0] += 1
        entry[1] += 1 if answer.is_correct else 0

    units = {
        u.unit_id: u
        for u in db.query(Content)
        .filter(Content.unit_id.in_(list(counts)))
        .all()
    }

    stats = [
        TopicStat(
            unit_id=unit_id,
            attempted=attempted,
            correct=correct,
            section_code=units[unit_id].section_code if unit_id in units else None,
            topic=units[unit_id].topic if unit_id in units else None,
            order=units[unit_id].order if unit_id in units else 0,
        )
        for unit_id, (attempted, correct) in counts.items()
    ]

    weak = find_weak_topics(stats, config)

    # --- struggle: same behaviour-based calculation as the live loop ------
    last_answer, last_question = rows[-1]

    analysis = analyze_answer(
        db, int(assessment.id), int(last_question.id)   # type: ignore
    )

    signals = analysis.signals

    accuracy = float(result["accuracy"])

    advice = recommend_post_assessment(
        accuracy,
        signals.struggle_level,
        analysis.decision.next_difficulty,      # level the learner is working at now
        weak,
        config,
    )

    # --- which content to recommend ---------------------------------------
    reason = advice.reason
    content = None

    last_unit = units.get(int(last_question.unit_id))   # type: ignore

    if advice.target == TARGET_NEXT and units:
        furthest = max(units.values(), key=lambda u: u.order)
        content = get_next_content(db, int(furthest.unit_id))

        if content is None:
            reason += " This was the last topic: the chapter is complete."

    elif advice.target == TARGET_WEAKEST:
        content = units.get(weak[0].unit_id)

    elif advice.target == TARGET_PREREQUISITE:
        base_unit = units.get(weak[0].unit_id) if weak else last_unit
        code = base_unit.section_code if base_unit else None   # type: ignore
        prerequisite = ADAPTATION_CONFIG.prerequisites.get(code) if code else None
        content = _by_section(db, prerequisite) or base_unit

    elif advice.target == TARGET_CURRENT:
        content = last_unit

    # --- baseline bookkeeping (idempotent) --------------------------------
    profile = (
        db.query(LearningProfile)
        .filter(LearningProfile.learner_id == assessment.learner_id)
        .first()
    )

    mastery = str(profile.mastery_level) if profile else "Beginner"

    if (
        result.get("status") == "Completed"
        and assessment.assessment_type == "Baseline"
    ):
        mastery = mastery_level_for(accuracy, config)

        if profile is not None:
            profile.baseline_score = accuracy   # type: ignore
            profile.mastery_level = mastery   # type: ignore

        learner = (
            db.query(Learner)
            .filter(Learner.id == assessment.learner_id)
            .first()
        )

        if learner is not None:
            learner.baseline_score = accuracy   # type: ignore
            learner.mastery_level = mastery   # type: ignore

        db.commit()

    base.update({
        "struggle_level": signals.struggle_level,
        "struggle_score": signals.struggle_score,
        "mastery_level": mastery,
        "weak_topics": [
            {
                "unit_id": w.unit_id,
                "section_code": w.section_code,
                "topic": w.topic,
                "questions_attempted": w.attempted,
                "questions_correct": w.correct,
                "accuracy": w.accuracy,
            }
            for w in weak
        ],
        "recommended_action": advice.action,
        "next_difficulty": advice.next_difficulty,
        "recommended_content": _brief(content),
        "reason": reason,
        "rules_applied": advice.rules_applied,
    })

    return base
