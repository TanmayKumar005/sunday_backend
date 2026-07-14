from sqlalchemy.orm import Session

from app.models.content import ContentUnit

from app.schemas.content import ContentCreate


def create_content(
    db: Session,
    content: ContentCreate
):

    lesson = ContentUnit(**content.model_dump())

    db.add(lesson)

    db.commit()

    db.refresh(lesson)

    return lesson