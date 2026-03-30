from datetime import datetime
from sqlalchemy import String, Text, DateTime, Boolean, Integer, Index, ForeignKey, func, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, Optional, List
import uuid

from app.core.database import Base
from app.core.enums import ContentType, ContentStatus

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.content_version import ContentVersion
    from app.models.review_workflow_stage import ReviewWorkflowStage
    from app.models.publishing_schedule import PublishingSchedule
    from app.models.canary_release_config import CanaryReleaseConfig
    from app.models.job_post import JobPost
    from app.models.bookmark import Bookmark
    from app.models.annotation import Annotation
    from app.models.event_telemetry import EventTelemetry


class Content(Base):
    __tablename__ = "contents"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    
    content_type: Mapped[ContentType] = mapped_column(
        SQLEnum(
            ContentType,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            native_enum=True,
        ),
        nullable=False,
        index=True
    )
    status: Mapped[ContentStatus] = mapped_column(
        SQLEnum(
            ContentStatus,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            native_enum=True,
        ),
        default=ContentStatus.DRAFT,
        nullable=False,
        index=True
    )
    
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    current_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("content_versions.id", ondelete="SET NULL"),
        nullable=True
    )
    
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    retracted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
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

    author: Mapped[Optional["User"]] = relationship("User", foreign_keys=[author_id])
    current_version: Mapped[Optional["ContentVersion"]] = relationship(
        "ContentVersion",
        foreign_keys=[current_version_id],
        post_update=True
    )
    versions: Mapped[List["ContentVersion"]] = relationship(
        "ContentVersion",
        foreign_keys="ContentVersion.content_id",
        back_populates="content",
        order_by="ContentVersion.version_number.desc()"
    )
    review_stages: Mapped[List["ReviewWorkflowStage"]] = relationship(
        "ReviewWorkflowStage",
        back_populates="content",
        order_by="ReviewWorkflowStage.stage_order"
    )
    publishing_schedule: Mapped[Optional["PublishingSchedule"]] = relationship(
        "PublishingSchedule",
        back_populates="content",
        uselist=False
    )
    canary_config: Mapped[Optional["CanaryReleaseConfig"]] = relationship(
        "CanaryReleaseConfig",
        back_populates="content",
        uselist=False
    )
    job_post: Mapped[Optional["JobPost"]] = relationship(
        "JobPost",
        back_populates="content",
        uselist=False
    )
    bookmarks: Mapped[List["Bookmark"]] = relationship("Bookmark", back_populates="content")
    annotations: Mapped[List["Annotation"]] = relationship("Annotation", back_populates="content")
    telemetry_events: Mapped[List["EventTelemetry"]] = relationship("EventTelemetry", back_populates="content")

    __table_args__ = (
        Index("ix_contents_type_status", "content_type", "status"),
        Index("ix_contents_author_status", "author_id", "status"),
        Index("ix_contents_published_at", "published_at"),
        Index("ix_contents_updated_at", "updated_at"),
        Index("ix_contents_status_featured", "status", "is_featured"),
    )

    def __repr__(self) -> str:
        return f"<Content(id={self.id}, title={self.title}, status={self.status})>"
