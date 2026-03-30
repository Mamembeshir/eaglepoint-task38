from datetime import datetime
from sqlalchemy import String, Text, DateTime, Boolean, Integer, Index, ForeignKey, func, JSON, Enum as SQLEnum, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, Optional, Any, Dict, List
import uuid

from app.core.database import Base
from app.core.enums import SegmentationType

if TYPE_CHECKING:
    from app.models.content import Content
    from app.models.user import User


class CanaryReleaseConfig(Base):
    __tablename__ = "canary_release_configs"

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
    
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    percentage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    segmentation_type: Mapped[SegmentationType] = mapped_column(
        SQLEnum(
            SegmentationType,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            native_enum=True,
        ),
        default=SegmentationType.RANDOM,
        nullable=False
    )
    
    segment_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    ramp_stages: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    
    current_stage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    target_user_ids: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    target_cohort_ids: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    metrics_threshold: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
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
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    content: Mapped["Content"] = relationship("Content", back_populates="canary_config")
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id])

    __table_args__ = (
        Index("ix_canary_configs_enabled_active", "is_enabled", "is_active"),
        Index("ix_canary_configs_percentage", "percentage"),
        Index("ix_canary_configs_segmentation", "segmentation_type"),
        Index("ix_canary_configs_started", "started_at"),
        CheckConstraint("percentage >= 0 AND percentage <= 100", name="ck_canary_percentage_range"),
    )

    def __repr__(self) -> str:
        return f"<CanaryReleaseConfig(id={self.id}, content_id={self.content_id}, percentage={self.percentage}%)>"
