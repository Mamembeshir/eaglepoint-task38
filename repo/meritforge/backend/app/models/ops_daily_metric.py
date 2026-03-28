from datetime import date, datetime
import uuid

from sqlalchemy import Date, DateTime, Index, Integer, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OpsDailyMetric(Base):
    __tablename__ = "ops_daily_metrics"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    metric_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True, index=True)

    active_users: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    returning_users: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    interacted_users: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    applying_users: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    converted_users: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    job_posts_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    applications_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    milestones_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    event_counts: Mapped[dict] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_ops_daily_metrics_conversion", "metric_date", "converted_users", "interacted_users"),
        Index("ix_ops_daily_metrics_funnel", "metric_date", "job_posts_created", "applications_created", "milestones_completed"),
    )
