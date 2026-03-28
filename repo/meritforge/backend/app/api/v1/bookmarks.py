from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.database import get_db
from app.core.enums import AuditAction
from app.dependencies.auth import get_current_user
from app.models.bookmark import Bookmark
from app.models.content import Content
from app.models.user import User
from app.schemas.bookmarks import BookmarkOut, BookmarkUpsertRequest

router = APIRouter(tags=["Bookmarks"])


@router.get("/bookmarks", response_model=list[BookmarkOut])
def list_bookmarks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BookmarkOut]:
    rows = db.scalars(select(Bookmark).where(Bookmark.user_id == current_user.id).order_by(Bookmark.updated_at.desc())).all()
    return [
        BookmarkOut(
            id=row.id,
            content_id=row.content_id,
            is_favorite=row.is_favorite,
            folder=row.folder,
            notes=row.notes,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


@router.post("/bookmarks", response_model=BookmarkOut, status_code=status.HTTP_201_CREATED)
def upsert_bookmark(
    payload: BookmarkUpsertRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookmarkOut:
    content = db.scalar(select(Content).where(Content.id == payload.content_id))
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")

    existing = db.scalar(select(Bookmark).where(Bookmark.user_id == current_user.id, Bookmark.content_id == payload.content_id))
    if existing:
        before = {
            "is_favorite": existing.is_favorite,
            "folder": existing.folder,
            "notes": existing.notes,
        }
        existing.is_favorite = payload.is_favorite
        existing.folder = payload.folder
        existing.notes = payload.notes
        write_audit_log(
            db,
            action=AuditAction.UPDATE,
            entity_type="bookmark",
            entity_id=str(existing.id),
            actor=current_user,
            request=request,
            before_data=before,
            after_data={
                "is_favorite": existing.is_favorite,
                "folder": existing.folder,
                "notes": existing.notes,
            },
            description="Updated bookmark",
        )
        db.commit()
        db.refresh(existing)
        return BookmarkOut(
            id=existing.id,
            content_id=existing.content_id,
            is_favorite=existing.is_favorite,
            folder=existing.folder,
            notes=existing.notes,
            updated_at=existing.updated_at,
        )

    bookmark = Bookmark(
        user_id=current_user.id,
        content_id=payload.content_id,
        is_favorite=payload.is_favorite,
        folder=payload.folder,
        notes=payload.notes,
    )
    db.add(bookmark)
    db.flush()
    write_audit_log(
        db,
        action=AuditAction.CREATE,
        entity_type="bookmark",
        entity_id=str(bookmark.id),
        actor=current_user,
        request=request,
        after_data={
            "content_id": str(bookmark.content_id),
            "is_favorite": bookmark.is_favorite,
            "folder": bookmark.folder,
        },
        description="Created bookmark",
    )
    db.commit()
    db.refresh(bookmark)
    return BookmarkOut(
        id=bookmark.id,
        content_id=bookmark.content_id,
        is_favorite=bookmark.is_favorite,
        folder=bookmark.folder,
        notes=bookmark.notes,
        updated_at=bookmark.updated_at,
    )


@router.delete("/bookmarks/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bookmark(
    content_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    content = db.scalar(select(Content).where(Content.id == content_id))
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")

    bookmark = db.scalar(select(Bookmark).where(Bookmark.user_id == current_user.id, Bookmark.content_id == content_id))
    if not bookmark:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found")

    write_audit_log(
        db,
        action=AuditAction.DELETE,
        entity_type="bookmark",
        entity_id=str(bookmark.id),
        actor=current_user,
        request=request,
        before_data={
            "content_id": str(bookmark.content_id),
            "is_favorite": bookmark.is_favorite,
            "folder": bookmark.folder,
        },
        description="Deleted bookmark",
    )
    db.delete(bookmark)
    db.commit()
