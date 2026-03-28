from datetime import datetime
from sqlalchemy import String, Text, DateTime, Boolean, Integer, Index, ForeignKey, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, Optional, Any, Dict
import uuid

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.content import Content
    from app.models.user import User


class ContentVersion(Base):
    __tablename__ = "content_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    
    content_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    change_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    is_published_version: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    content: Mapped["Content"] = relationship(
        "Content",
        foreign_keys=[content_id],
        back_populates="versions"
    )
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id])

    __table_args__ = (
        Index("ix_content_versions_content_number", "content_id", "version_number", unique=True),
        Index("ix_content_versions_published", "content_id", "is_published_version"),
        Index("ix_content_versions_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<ContentVersion(id={self.id}, content_id={self.content_id}, version={self.version_number})>"
