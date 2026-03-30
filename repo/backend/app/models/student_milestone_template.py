from datetime import datetime
import uuid

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.enums import EventType


class StudentMilestoneTemplate(Base):
    __tablename__ = "student_milestone_templates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_predefined: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    automation_event_type: Mapped[EventType | None] = mapped_column(
        SQLEnum(
            EventType,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            native_enum=True,
        ),
        nullable=True,
        index=True,
    )
    threshold_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    job_post_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("job_posts.id", ondelete="CASCADE"), nullable=True, index=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_student_milestone_templates_active_event", "is_active", "automation_event_type"),
        Index("ix_student_milestone_templates_job_post", "job_post_id", "is_active"),
    )
