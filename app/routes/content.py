from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.schemas.content import (
    ContentCreate,
    ContentResponse
)

from app.services.content_service import create_content

router = APIRouter(
    prefix="/content",
    tags=["Content"]
)


@router.post(
    "/",
    response_model=ContentResponse
)
def add_content(
    content: ContentCreate,
    db: Session = Depends(get_db)
):

    return create_content(
        db,
        content
    )