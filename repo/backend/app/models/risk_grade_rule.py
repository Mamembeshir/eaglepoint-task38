from datetime import datetime
import uuid

from sqlalchemy import Boolean, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RiskGradeRule(Base):
    __tablename__ = "risk_grade_rules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    grade: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    min_score: Mapped[int] = mapped_column(Integer, nullable=False)
    max_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    blocked_until_final_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    required_distinct_reviewers: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_risk_grade_rules_bounds", "min_score", "max_score"),
    )
