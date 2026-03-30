from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.enums import ContentStatus
from app.dependencies.integration import require_integration_hmac
from app.models.content import Content

router = APIRouter(tags=["Integration"])


@router.post("/integration/echo")
def integration_echo(
    payload: dict,
    auth: dict[str, str] = Depends(require_integration_hmac),
) -> dict:
    return {
        "ok": True,
        "key_id": auth["key_id"],
        "echo": payload,
    }


@router.get("/integration/published-content")
def integration_list_published_content(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    auth: dict[str, str] = Depends(require_integration_hmac),
    db: Session = Depends(get_db),
) -> dict:
    rows = db.scalars(
        select(Content)
        .where(Content.status == ContentStatus.PUBLISHED)
        .order_by(Content.published_at.desc(), Content.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    return {
        "ok": True,
        "key_id": auth["key_id"],
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": str(row.id),
                "title": row.title,
                "content_type": row.content_type.value if hasattr(row.content_type, "value") else str(row.content_type),
                "published_at": row.published_at.isoformat() if row.published_at else None,
            }
            for row in rows
        ],
    }
