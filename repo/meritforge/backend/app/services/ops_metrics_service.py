from datetime import date, datetime, timedelta, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.enums import EventType
from app.models.application import Application
from app.models.event_telemetry import EventTelemetry
from app.models.job_post import JobPost
from app.models.ops_daily_metric import OpsDailyMetric
from app.models.ops_event_daily_count import OpsEventDailyCount
from app.models.student_progress_milestone import StudentProgressMilestone


CONTENT_INTERACTION_EVENTS = {
    EventType.PLAY,
    EventType.SKIP,
    EventType.FAVORITE,
    EventType.SEARCH,
}

APPLICATION_EVENTS = {EventType.JOB_APPLICATION, EventType.APPLICATION}


def _day_bounds(metric_date: date) -> tuple[datetime, datetime]:
    start_dt = datetime.combine(metric_date, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = start_dt + timedelta(days=1)
    return start_dt, end_dt


def aggregate_ops_for_day(db: Session, metric_date: date) -> OpsDailyMetric:
    start_dt, end_dt = _day_bounds(metric_date)
    prev_start = start_dt - timedelta(days=1)

    active_users = db.scalar(
        select(func.count(func.distinct(EventTelemetry.user_id))).where(
            EventTelemetry.user_id.is_not(None),
            EventTelemetry.created_at >= start_dt,
            EventTelemetry.created_at < end_dt,
        )
    ) or 0

    returning_users = db.scalar(
        select(func.count(func.distinct(EventTelemetry.user_id))).where(
            EventTelemetry.user_id.is_not(None),
            EventTelemetry.created_at >= start_dt,
            EventTelemetry.created_at < end_dt,
            EventTelemetry.user_id.in_(
                select(EventTelemetry.user_id).where(
                    EventTelemetry.user_id.is_not(None),
                    EventTelemetry.created_at >= prev_start,
                    EventTelemetry.created_at < start_dt,
                )
            ),
        )
    ) or 0

    interacted_user_subq = (
        select(func.distinct(EventTelemetry.user_id))
        .where(
            EventTelemetry.user_id.is_not(None),
            EventTelemetry.event_type.in_(CONTENT_INTERACTION_EVENTS),
            EventTelemetry.created_at >= start_dt,
            EventTelemetry.created_at < end_dt,
        )
        .subquery()
    )
    interacted_users = db.scalar(select(func.count()).select_from(interacted_user_subq)) or 0

    applying_user_subq = (
        select(func.distinct(EventTelemetry.user_id))
        .where(
            EventTelemetry.user_id.is_not(None),
            EventTelemetry.event_type.in_(APPLICATION_EVENTS),
            EventTelemetry.created_at >= start_dt,
            EventTelemetry.created_at < end_dt,
        )
        .subquery()
    )
    applying_users = db.scalar(select(func.count()).select_from(applying_user_subq)) or 0

    converted_users = db.scalar(
        select(func.count()).select_from(interacted_user_subq).where(
            interacted_user_subq.c.user_id.in_(select(applying_user_subq.c.user_id))
        )
    ) or 0

    job_posts_created = db.scalar(
        select(func.count(JobPost.id)).where(
            JobPost.created_at >= start_dt,
            JobPost.created_at < end_dt,
        )
    ) or 0

    applications_created = db.scalar(
        select(func.count(Application.id)).where(
            Application.created_at >= start_dt,
            Application.created_at < end_dt,
        )
    ) or 0

    milestones_completed = db.scalar(
        select(func.count(StudentProgressMilestone.id)).where(
            StudentProgressMilestone.achievement_date == metric_date,
            StudentProgressMilestone.progress_value >= StudentProgressMilestone.target_value,
        )
    ) or 0

    events_by_type = db.execute(
        select(
            EventTelemetry.event_type,
            func.count(EventTelemetry.id),
            func.count(func.distinct(EventTelemetry.user_id)),
        )
        .where(
            EventTelemetry.created_at >= start_dt,
            EventTelemetry.created_at < end_dt,
        )
        .group_by(EventTelemetry.event_type)
    ).all()

    event_counts: dict[str, int] = {}
    for event_type, count, unique_users in events_by_type:
        key = event_type.value if hasattr(event_type, "value") else str(event_type)
        event_counts[key] = int(count)

        row = db.scalar(
            select(OpsEventDailyCount).where(
                OpsEventDailyCount.metric_date == metric_date,
                OpsEventDailyCount.event_type == key,
            )
        )
        if row:
            row.event_count = int(count)
            row.unique_user_count = int(unique_users)
        else:
            db.add(
                OpsEventDailyCount(
                    metric_date=metric_date,
                    event_type=key,
                    event_count=int(count),
                    unique_user_count=int(unique_users),
                )
            )

    daily = db.scalar(select(OpsDailyMetric).where(OpsDailyMetric.metric_date == metric_date))
    if daily is None:
        daily = OpsDailyMetric(metric_date=metric_date, event_counts={})
        db.add(daily)

    daily.active_users = int(active_users)
    daily.returning_users = int(returning_users)
    daily.interacted_users = int(interacted_users)
    daily.applying_users = int(applying_users)
    daily.converted_users = int(converted_users)
    daily.job_posts_created = int(job_posts_created)
    daily.applications_created = int(applications_created)
    daily.milestones_completed = int(milestones_completed)
    daily.event_counts = event_counts

    return daily


def aggregate_ops_range(db: Session, start_date: date, end_date: date) -> list[OpsDailyMetric]:
    if end_date < start_date:
        return []

    current = start_date
    results: list[OpsDailyMetric] = []
    while current <= end_date:
        results.append(aggregate_ops_for_day(db, current))
        current = current + timedelta(days=1)
    return results
