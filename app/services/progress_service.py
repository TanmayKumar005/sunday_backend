from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.ai.progress_rules import (
    DEFAULT_PROGRESS_CONFIG,
    ProgressConfig,
    TopicStat,
    find_weak_topics,
    is_topic_complete,
    percentage,
)
from app.models.assessment import Assessment, AssessmentAnswer
from app.models.content import Content
from app.models.learner import Learner
from app.models.learning_profile import LearningProfile
from app.models.progress import LearnerProgress
from app.models.question import Question

CHAPTER_COMPLETE = "CHAPTER_COMPLETE"
START_LEARNING = "START_LEARNING"
PRACTISE_WEAK_TOPIC = "PRACTISE_WEAK_TOPIC"
CONTINUE_NEXT_TOPIC = "CONTINUE_NEXT_TOPIC"


def topic_label(section_code, topic) -> Optional[str]:
    if section_code and topic:
        return f"{section_code} {topic}"

    return topic or section_code


def update_topic_progress(
    db: Session,
    learner_id: int,
    unit_id: int,
    struggle_score: float,
    struggle_level: str,
    current_difficulty: str,
    config: ProgressConfig = DEFAULT_PROGRESS_CONFIG,
) -> LearnerProgress:
    """Recompute one topic's progress from the learner's answers.

    Counts are recalculated (not incremented) so re-answering a question or
    calling this twice never double counts. A completed topic stays completed.
    """

    rows = (
        db.query(AssessmentAnswer.is_correct)
        .join(Assessment, Assessment.id == AssessmentAnswer.assessment_id)
        .join(Question, Question.id == AssessmentAnswer.question_id)
        .filter(
            Assessment.learner_id == learner_id,
            Question.unit_id == unit_id,
        )
        .all()
    )

    attempted = len(rows)
    correct = sum(1 for (value,) in rows if value)

    unit = db.query(Content).filter(Content.unit_id == unit_id).first()

    progress = (
        db.query(LearnerProgress)
        .filter(
            LearnerProgress.learner_id == learner_id,
            LearnerProgress.unit_id == unit_id,
        )
        .first()
    )

    if progress is None:
        progress = LearnerProgress(learner_id=learner_id, unit_id=unit_id)
        db.add(progress)

    already_completed = bool(progress.completed)

    progress.section_code = unit.section_code if unit else None   # type: ignore
    progress.topic = unit.topic if unit else None   # type: ignore
    progress.questions_attempted = attempted   # type: ignore
    progress.questions_correct = correct   # type: ignore
    progress.accuracy = percentage(correct, attempted)   # type: ignore
    progress.current_difficulty = current_difficulty   # type: ignore
    progress.struggle_score = struggle_score   # type: ignore
    progress.struggle_level = struggle_level   # type: ignore
    progress.completed = already_completed or is_topic_complete(   # type: ignore
        attempted, correct, struggle_level, config
    )
    progress.last_activity = datetime.utcnow()   # type: ignore

    db.commit()
    db.refresh(progress)

    return progress


def _progress_rows(db: Session, learner_id: int):
    return (
        db.query(LearnerProgress)
        .join(Content, Content.unit_id == LearnerProgress.unit_id)
        .filter(LearnerProgress.learner_id == learner_id)
        .order_by(Content.order.asc())
        .all()
    )


def get_progress(db: Session, learner_id: int):
    """Per-topic progress, in curriculum order. None if learner unknown."""

    learner = db.query(Learner).filter(Learner.id == learner_id).first()

    if learner is None:
        return None

    return {
        "learner_id": learner_id,
        "topics": [
            {
                "unit_id": row.unit_id,
                "section_code": row.section_code,
                "topic": row.topic,
                "questions_attempted": row.questions_attempted or 0,
                "questions_correct": row.questions_correct or 0,
                "accuracy": row.accuracy or 0.0,
                "current_difficulty": row.current_difficulty or "EASY",
                "struggle_score": row.struggle_score or 0.0,
                "struggle_level": row.struggle_level or "Low",
                "completed": bool(row.completed),
                "last_activity": row.last_activity,
            }
            for row in _progress_rows(db, learner_id)
        ],
    }


def _brief(unit: Content):
    return {
        "unit_id": unit.unit_id,
        "section_code": unit.section_code,
        "topic": unit.topic,
        "title": unit.title,
        "learning_objective": unit.learning_objective,
    }


def get_summary(
    db: Session,
    learner_id: int,
    config: ProgressConfig = DEFAULT_PROGRESS_CONFIG,
):
    """Whole-chapter summary for a learner. None if learner unknown."""

    learner = db.query(Learner).filter(Learner.id == learner_id).first()

    if learner is None:
        return None

    units = db.query(Content).order_by(Content.order.asc()).all()
    order_of = {u.unit_id: u.order for u in units}

    rows = _progress_rows(db, learner_id)

    profile = (
        db.query(LearningProfile)
        .filter(LearningProfile.learner_id == learner_id)
        .first()
    )

    attempted = sum(r.questions_attempted or 0 for r in rows)
    correct = sum(r.questions_correct or 0 for r in rows)

    completed_ids = {r.unit_id for r in rows if r.completed}

    stats = [
        TopicStat(
            unit_id=r.unit_id,
            attempted=r.questions_attempted or 0,
            correct=r.questions_correct or 0,
            section_code=r.section_code,
            topic=r.topic,
            order=order_of.get(r.unit_id, 0),
            completed=bool(r.completed),
        )
        for r in rows
    ]

    weak = find_weak_topics(stats, config)

    latest = max(
        (r for r in rows if r.last_activity is not None),
        key=lambda r: r.last_activity,
        default=None,
    )

    # recommendation: weakest topic first, else first unfinished topic
    unit_by_id = {u.unit_id: u for u in units}
    recommended = None

    if not units:
        action, reason = START_LEARNING, "No content is available yet."
    elif weak:
        recommended = unit_by_id.get(weak[0].unit_id)
        action = PRACTISE_WEAK_TOPIC
        reason = "This topic is below the target accuracy: practise it next."
    else:
        remaining = [u for u in units if u.unit_id not in completed_ids]

        if not remaining:
            action = CHAPTER_COMPLETE
            reason = "Every topic in the chapter is completed."
        else:
            recommended = remaining[0]
            action = START_LEARNING if not rows else CONTINUE_NEXT_TOPIC
            reason = (
                "Start with the first topic."
                if not rows
                else "Continue with the first topic that is not completed."
            )

    return {
        "learner_id": learner_id,
        "learner_name": learner.name,
        "total_topics": len(units),
        "topics_started": len(rows),
        "topics_completed": len(completed_ids),
        "completed_topics": [
            topic_label(r.section_code, r.topic) or f"Unit {r.unit_id}"
            for r in rows if r.completed
        ],
        "completion_percent": percentage(len(completed_ids), len(units)),
        "questions_attempted": attempted,
        "questions_correct": correct,
        "accuracy": percentage(correct, attempted),
        "current_difficulty": (
            str(profile.current_difficulty).upper() if profile else "EASY"
        ),
        "struggle_level": str(profile.struggle_level) if profile else "Low",
        "struggle_score": latest.struggle_score if latest else None,
        "mastery_level": str(profile.mastery_level) if profile else "Beginner",
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
        "last_activity": latest.last_activity if latest else None,
        "recommended_action": action,
        "recommended_topic": _brief(recommended) if recommended else None,
        "reason": reason,
    }
