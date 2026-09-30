from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.content import (
    ChapterCurriculum,
    ContentCreate,
    ContentResponse
)
from app.schemas.question import QuestionResponse
from app.services.content_service import (
    create_content,
    get_content,
    get_content_by_section,
    get_next_content,
    get_all_content,
    get_curriculum,
    get_unit_questions
)


router = APIRouter(
    prefix="/content",
    tags=["Content"]
)


@router.post("/", response_model=ContentResponse)
def create_new_content(
    content: ContentCreate,
    db: Session = Depends(get_db)
):
    if content.section_code and get_content_by_section(
        db, content.section_code
    ):
        raise HTTPException(
            status_code=409,
            detail="A unit with this section_code already exists"
        )

    return create_content(db, content)


@router.get("/curriculum", response_model=list[ChapterCurriculum])
def curriculum(
    db: Session = Depends(get_db)
):
    return get_curriculum(db)


@router.get("/units", response_model=list[ContentResponse])
def get_all_units(
    db: Session = Depends(get_db)
):
    return get_all_content(db)


@router.get("/sections/{section_code}", response_model=ContentResponse)
def get_section(
    section_code: str,
    db: Session = Depends(get_db)
):
    content = get_content_by_section(db, section_code)

    if not content:
        raise HTTPException(
            status_code=404,
            detail="Section not found"
        )

    return content


@router.get("/units/{unit_id}", response_model=ContentResponse)
def get_unit(
    unit_id: int,
    db: Session = Depends(get_db)
):
    content = get_content(db, unit_id)

    if not content:
        raise HTTPException(
            status_code=404,
            detail="Learning unit not found"
        )

    return content


@router.get("/units/{unit_id}/next", response_model=ContentResponse)
def get_next_unit(
    unit_id: int,
    db: Session = Depends(get_db)
):
    content = get_next_content(db, unit_id)

    if not content:
        raise HTTPException(
            status_code=404,
            detail="Next learning unit not found"
        )

    return content


@router.get(
    "/units/{unit_id}/questions",
    response_model=list[QuestionResponse]
)
def get_questions_for_unit(
    unit_id: int,
    db: Session = Depends(get_db)
):
    if not get_content(db, unit_id):
        raise HTTPException(
            status_code=404,
            detail="Learning unit not found"
        )

    return get_unit_questions(db, unit_id)
