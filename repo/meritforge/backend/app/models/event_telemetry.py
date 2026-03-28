from datetime import datetime
from sqlalchemy import String, Text, DateTime, Integer, Index, ForeignKey, func, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, Optional, Dict, Any
import uuid

from app.core.database import Base
from app.core.enums import EventType

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.content import Content


class EventTelemetry(Base):
    __tablename__ = "event_telemetry"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    
    event_type: Mapped[EventType] = mapped_column(
        SQLEnum(
            EventType,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            native_enum=True,
        ),
        nullable=False,
        index=True
    )
    
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    session_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    content_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("contents.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    event_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    page_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    referrer_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True, index=True)
    
    device_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    browser: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    os: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    progress_percentage: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    
    user: Mapped[Optional["User"]] = relationship("User", back_populates="telemetry_events")
    content: Mapped[Optional["Content"]] = relationship("Content", back_populates="telemetry_events")

    __table_args__ = (
        Index("ix_telemetry_type_created", "event_type", "created_at"),
        Index("ix_telemetry_user_type", "user_id", "event_type"),
        Index("ix_telemetry_content_type", "content_id", "event_type"),
        Index("ix_telemetry_session_created", "session_id", "created_at"),
        Index("ix_telemetry_resource", "resource_type", "resource_id"),
        Index("ix_telemetry_device_created", "device_type", "created_at"),
        Index("ix_telemetry_analytics_event_user_time", "event_type", "user_id", "created_at"),
        Index("ix_telemetry_analytics_content_time", "content_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<EventTelemetry(id={self.id}, type={self.event_type})>"
