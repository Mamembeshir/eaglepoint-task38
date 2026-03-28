from datetime import datetime
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ContentRiskAssessment(Base):
    __tablename__ = "content_risk_assessments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    content_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contents.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_grade: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    triggering_words: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    blocked_until_final_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    required_distinct_reviewers: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_content_risk_assessments_grade_score", "risk_grade", "risk_score"),
    )
