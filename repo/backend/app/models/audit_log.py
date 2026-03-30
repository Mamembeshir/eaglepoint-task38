from datetime import datetime
from sqlalchemy import String, Text, DateTime, Integer, Index, ForeignKey, func, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, Optional, Dict, Any
import uuid

from app.core.database import Base
from app.core.enums import AuditAction

if TYPE_CHECKING:
    from app.models.user import User


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    
    action: Mapped[AuditAction] = mapped_column(
        SQLEnum(
            AuditAction,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            native_enum=True,
        ),
        nullable=False,
        index=True
    )
    
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    user_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True, index=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    before_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    after_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    changes: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    request_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    request_method: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    session_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    
    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_user_action", "user_id", "action"),
        Index("ix_audit_logs_action_created", "action", "created_at"),
        Index("ix_audit_logs_user_created", "user_id", "created_at"),
        Index("ix_audit_logs_entity_created", "entity_type", "entity_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, entity={self.entity_type})>"
