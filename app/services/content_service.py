from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.content import Content
from app.models.question import Question
from app.schemas.content import ContentCreate


def create_content(db: Session, content: ContentCreate):
    new_content = Content(
        class_level=content.class_level,
        subject=content.subject,
        book=content.book,
        chapter_number=content.chapter_number,
        chapter=content.chapter,
        section_code=content.section_code,
        topic=content.topic,
        learning_objective=content.learning_objective,
        title=content.title,
        concept=content.concept,
        explanation=content.explanation,
        order=content.order,
        difficulty=content.difficulty
    )

    db.add(new_content)
    db.commit()
    db.refresh(new_content)

    return new_content


def get_content(db: Session, unit_id: int):
    return db.query(Content).filter(
        Content.unit_id == unit_id
    ).first()


def get_content_by_section(db: Session, section_code: str):
    return db.query(Content).filter(
        Content.section_code == section_code
    ).first()


def get_next_content(db: Session, unit_id: int):
    current_content = get_content(db, unit_id)

    if not current_content:
        return None

    return (
        db.query(Content)
        .filter(Content.order > current_content.order)
        .order_by(Content.order.asc())
        .first()
    )


def get_all_content(db: Session):
    return db.query(Content).order_by(
        Content.order.asc()
    ).all()


def get_unit_questions(db: Session, unit_id: int):
    return (
        db.query(Question)
        .filter(Question.unit_id == unit_id)
        .order_by(Question.id.asc())
        .all()
    )


def get_curriculum(db: Session):
    """Class/Subject/Book/Chapter -> sections, with question counts."""

    units = get_all_content(db)

    rows = (
        db.query(
            Question.unit_id,
            Question.difficulty,
            func.count(Question.id)
        )
        .group_by(Question.unit_id, Question.difficulty)
        .all()
    )

    counts: dict = {}

    for unit_id, difficulty, total in rows:
        counts.setdefault(unit_id, {})[difficulty] = total

    chapters: dict = {}

    for unit in units:
        key = (
            unit.class_level,
            unit.subject,
            unit.book,
            unit.chapter_number,
            unit.chapter
        )

        if key not in chapters:
            chapters[key] = {
                "class_level": unit.class_level,
                "subject": unit.subject,
                "book": unit.book,
                "chapter_number": unit.chapter_number,
                "chapter": unit.chapter,
                "sections": []
            }

        by_difficulty = counts.get(unit.unit_id, {})

        chapters[key]["sections"].append({
            "unit_id": unit.unit_id,
            "section_code": unit.section_code,
            "topic": unit.topic,
            "title": unit.title,
            "learning_objective": unit.learning_objective,
            "difficulty": unit.difficulty,
            "order": unit.order,
            "question_count": sum(by_difficulty.values()),
            "questions_by_difficulty": by_difficulty
        })

    return list(chapters.values())
