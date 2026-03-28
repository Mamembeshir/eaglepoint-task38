from datetime import datetime
from sqlalchemy import String, Text, DateTime, Boolean, Integer, Index, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, Optional, List
import uuid

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.content import Content
    from app.models.review_decision import ReviewDecision


class ReviewWorkflowStage(Base):
    __tablename__ = "review_workflow_stages"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    
    content_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    stage_name: Mapped[str] = mapped_column(String(100), nullable=False)
    stage_order: Mapped[int] = mapped_column(Integer, nullable=False)
    
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_parallel: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
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
    
    content: Mapped["Content"] = relationship("Content", back_populates="review_stages")
    decisions: Mapped[List["ReviewDecision"]] = relationship(
        "ReviewDecision",
        back_populates="stage",
        order_by="ReviewDecision.created_at.desc()"
    )

    __table_args__ = (
        Index("ix_review_stages_content_order", "content_id", "stage_order"),
        Index("ix_review_stages_completed", "content_id", "is_completed"),
    )

    def __repr__(self) -> str:
        return f"<ReviewWorkflowStage(id={self.id}, stage={self.stage_name}, order={self.stage_order})>"
