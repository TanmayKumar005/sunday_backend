from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.content import ContentCreate, ContentResponse
from app.services.content_service import (
    create_content,
    get_content,
    get_next_content,
    get_all_content
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
    return create_content(db, content)


@router.get("/units", response_model=list[ContentResponse])
def get_all_units(
    db: Session = Depends(get_db)
):
    return get_all_content(db)


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