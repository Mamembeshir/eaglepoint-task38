from datetime import datetime
from sqlalchemy import String, Text, DateTime, Boolean, Integer, Index, ForeignKey, func, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, Optional
import uuid

from app.core.database import Base
from app.core.enums import ApplicationStatus

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.job_post import JobPost


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    
    job_post_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("job_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    applicant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    status: Mapped[ApplicationStatus] = mapped_column(
        SQLEnum(
            ApplicationStatus,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            native_enum=True,
        ),
        default=ApplicationStatus.DRAFT,
        nullable=False,
        index=True
    )
    
    cover_letter: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resume_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    portfolio_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    custom_fields: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status_changed_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
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
    
    job_post: Mapped["JobPost"] = relationship("JobPost", back_populates="applications")
    applicant: Mapped["User"] = relationship(
        "User",
        back_populates="applications",
        foreign_keys=[applicant_id],
    )

    __table_args__ = (
        Index("ix_applications_job_status", "job_post_id", "status"),
        Index("ix_applications_applicant_status", "applicant_id", "status"),
        Index("ix_applications_submitted", "submitted_at"),
        Index("ix_applications_status_changed_by", "status_changed_by_id", "updated_at"),
        Index("uq_applications_job_applicant", "job_post_id", "applicant_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<Application(id={self.id}, status={self.status})>"
