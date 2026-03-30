from datetime import datetime
from sqlalchemy import String, Text, DateTime, Boolean, Integer, Index, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, Optional
import uuid

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.content import Content
    from app.models.user import User


class PublishingSchedule(Base):
    __tablename__ = "publishing_schedules"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    
    content_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    
    scheduled_publish_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    
    scheduled_unpublish_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_unpublished: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    unpublished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    publish_job_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    unpublish_job_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
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
    
    content: Mapped["Content"] = relationship("Content", back_populates="publishing_schedule")
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id])

    __table_args__ = (
        Index("ix_publishing_schedules_pending", "scheduled_publish_at", "is_published"),
        Index("ix_publishing_schedules_unpublish", "scheduled_unpublish_at", "is_unpublished"),
    )

    def __repr__(self) -> str:
        return f"<PublishingSchedule(id={self.id}, content_id={self.content_id})>"
