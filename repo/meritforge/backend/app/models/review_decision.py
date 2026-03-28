from datetime import datetime
from sqlalchemy import String, Text, DateTime, Boolean, Integer, Index, ForeignKey, func, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, Optional
import uuid

from app.core.database import Base
from app.core.enums import ContentStatus

if TYPE_CHECKING:
    from app.models.review_workflow_stage import ReviewWorkflowStage
    from app.models.user import User


class ReviewDecision(Base):
    __tablename__ = "review_decisions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    
    stage_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("review_workflow_stages.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    decision: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    content_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("content_versions.id", ondelete="SET NULL"),
        nullable=True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    stage: Mapped["ReviewWorkflowStage"] = relationship("ReviewWorkflowStage", back_populates="decisions")
    reviewer: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewer_id])

    __table_args__ = (
        Index("ix_review_decisions_stage_decision", "stage_id", "decision"),
        Index("ix_review_decisions_reviewer_created", "reviewer_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<ReviewDecision(id={self.id}, decision={self.decision})>"
