from datetime import datetime, date
from sqlalchemy import String, Text, DateTime, Boolean, Integer, Index, ForeignKey, func, Date, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, Optional
import uuid

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class StudentProgressMilestone(Base):
    __tablename__ = "student_progress_milestones"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    job_post_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("job_posts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    
    milestone_template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("student_milestone_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    milestone_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    milestone_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    achievement_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    progress_value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    target_value: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    last_event_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    certificate_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    badge_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    student: Mapped["User"] = relationship("User", foreign_keys=[student_id], back_populates="milestones")
    verified_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[verified_by_id])

    __table_args__ = (
        Index("ix_milestones_student_type", "student_id", "milestone_type"),
        Index("ix_milestones_student_date", "student_id", "achievement_date"),
        Index("ix_milestones_verified", "is_verified", "achievement_date"),
        Index("ix_milestones_student_template", "student_id", "milestone_template_id"),
        Index("ix_milestones_updated_at", "updated_at"),
        Index("ix_milestones_job_post_student", "job_post_id", "student_id"),
        Index("ix_milestones_application", "application_id", "updated_at"),
    )

    def __repr__(self) -> str:
        return f"<StudentProgressMilestone(id={self.id}, type={self.milestone_type})>"
