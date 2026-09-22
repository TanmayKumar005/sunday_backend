from sqlalchemy.orm import Session

from app.models.content import Content
from app.schemas.content import ContentCreate


def create_content(db: Session, content: ContentCreate):
    new_content = Content(
        chapter=content.chapter,
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
    return db.query(Content).filter(Content.unit_id == unit_id).first()


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
    return db.query(Content).order_by(Content.order.asc()).all()