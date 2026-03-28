from datetime import datetime
from sqlalchemy import String, Text, DateTime, Boolean, Integer, Index, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, Optional
import uuid

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.content import Content


class Bookmark(Base):
    __tablename__ = "bookmarks"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    content_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    folder: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    user: Mapped["User"] = relationship("User", back_populates="bookmarks")
    content: Mapped["Content"] = relationship("Content", back_populates="bookmarks")

    __table_args__ = (
        Index("ix_bookmarks_user_favorite", "user_id", "is_favorite"),
        Index("ix_bookmarks_user_folder", "user_id", "folder"),
        Index("uq_bookmarks_user_content", "user_id", "content_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<Bookmark(id={self.id}, user_id={self.user_id})>"
