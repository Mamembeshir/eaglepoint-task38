from datetime import datetime
from sqlalchemy import String, Text, DateTime, Boolean, Integer, Index, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, Optional, List
import uuid

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.role import Role
    from app.models.user_cohort import UserCohort
    from app.models.application import Application
    from app.models.student_progress_milestone import StudentProgressMilestone
    from app.models.bookmark import Bookmark
    from app.models.annotation import Annotation
    from app.models.event_telemetry import EventTelemetry
    from app.models.audit_log import AuditLog
    from app.models.refresh_token import RefreshToken
    from app.models.user_topic_subscription import UserTopicSubscription


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    consent_contact_info_visible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_photo_visible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_analytics: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_data_portability: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    role_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("roles.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_marked_for_deletion: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deletion_requested_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_deletion_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deletion_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
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
    
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    role: Mapped[Optional["Role"]] = relationship("Role", back_populates="users")
    cohorts: Mapped[List["UserCohort"]] = relationship(
        "UserCohort",
        secondary="user_cohort_memberships",
        back_populates="members"
    )
    applications: Mapped[List["Application"]] = relationship(
        "Application",
        back_populates="applicant",
        foreign_keys="[Application.applicant_id]"
    )
    milestones: Mapped[List["StudentProgressMilestone"]] = relationship(
        "StudentProgressMilestone",
        back_populates="student",
        foreign_keys="StudentProgressMilestone.student_id"
    )
    bookmarks: Mapped[List["Bookmark"]] = relationship("Bookmark", back_populates="user")
    annotations: Mapped[List["Annotation"]] = relationship("Annotation", back_populates="author")
    telemetry_events: Mapped[List["EventTelemetry"]] = relationship("EventTelemetry", back_populates="user")
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="user")
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship("RefreshToken", back_populates="user")
    topic_subscriptions: Mapped[List["UserTopicSubscription"]] = relationship("UserTopicSubscription", back_populates="user")

    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
        Index("ix_users_role_active", "role_id", "is_active"),
        Index("ix_users_updated_at", "updated_at"),
        Index("ix_users_marked_for_deletion", "is_marked_for_deletion", "scheduled_deletion_at"),
    )

    @property
    def full_name(self) -> Optional[str]:
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.display_name

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"
