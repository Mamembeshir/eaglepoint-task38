from datetime import datetime, date
from sqlalchemy import String, Text, DateTime, Boolean, Integer, Index, ForeignKey, func, Enum as SQLEnum, Date, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, Optional, List
import uuid
from decimal import Decimal

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.content import Content
    from app.models.application import Application


class JobPost(Base):
    __tablename__ = "job_posts"

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
    
    employer_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    employer_logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    location_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    employment_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    salary_min: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    salary_max: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    salary_currency: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    
    requirements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    benefits: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    application_deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    application_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
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
    
    content: Mapped["Content"] = relationship("Content", back_populates="job_post")
    applications: Mapped[List["Application"]] = relationship("Application", back_populates="job_post")

    __table_args__ = (
        Index("ix_job_posts_employer_active", "employer_name", "is_active"),
        Index("ix_job_posts_location_active", "location", "is_active"),
        Index("ix_job_posts_deadline_active", "application_deadline", "is_active"),
        Index("ix_job_posts_featured", "is_featured", "is_active"),
        Index("ix_job_posts_created_by", "created_by_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<JobPost(id={self.id}, employer={self.employer_name})>"
