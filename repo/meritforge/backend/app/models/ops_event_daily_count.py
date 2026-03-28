from datetime import date, datetime
import uuid

from sqlalchemy import Date, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OpsEventDailyCount(Base):
    __tablename__ = "ops_event_daily_counts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    metric_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    event_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unique_user_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_ops_event_daily_unique", "metric_date", "event_type", unique=True),
        Index("ix_ops_event_daily_trending", "event_type", "metric_date", "event_count"),
    )
