from datetime import date, timedelta
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.enums import RoleType
from app.dependencies.auth import require_roles
from app.models.ops_daily_metric import OpsDailyMetric
from app.models.ops_event_daily_count import OpsEventDailyCount
from app.models.user import User
from app.schemas.operations import (
    ConversionMetricsOut,
    EventTrendSummaryOut,
    FunnelMetricsOut,
    OperationsDashboardOut,
    RetentionMetricsOut,
)
from app.services.ops_metrics_service import aggregate_ops_range

router = APIRouter(tags=["Operations Dashboard"])


def _percentage(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100.0, 2)


def _load_daily_rows(db: Session, start_date: date, end_date: date) -> list[OpsDailyMetric]:
    rows = db.scalars(
        select(OpsDailyMetric)
        .where(OpsDailyMetric.metric_date >= start_date, OpsDailyMetric.metric_date <= end_date)
        .order_by(OpsDailyMetric.metric_date.asc())
    ).all()
    if rows:
        return rows

    rows = aggregate_ops_range(db, start_date=start_date, end_date=end_date)
    db.commit()
    return rows


@router.get("/operations/metrics", response_model=OperationsDashboardOut)
def get_operations_metrics(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleType.SYSTEM_ADMINISTRATOR)),
) -> OperationsDashboardOut:
    if end_date < start_date:
        raise HTTPException(status_code=422, detail="end_date must be >= start_date")

    rows = _load_daily_rows(db, start_date, end_date)
    if not rows:
        return OperationsDashboardOut(
            start_date=start_date,
            end_date=end_date,
            retention=RetentionMetricsOut(active_users=0, returning_users=0, retention_percentage=0.0),
            conversion=ConversionMetricsOut(interacted_users=0, applying_users=0, converted_users=0, conversion_percentage=0.0),
            funnel=FunnelMetricsOut(
                job_posts=0,
                applications=0,
                milestone_completions=0,
                post_to_application_percentage=0.0,
                application_to_milestone_percentage=0.0,
            ),
            trend_summaries=[],
        )

    active_users = sum(r.active_users for r in rows)
    returning_users = sum(r.returning_users for r in rows)
    interacted_users = sum(r.interacted_users for r in rows)
    applying_users = sum(r.applying_users for r in rows)
    converted_users = sum(r.converted_users for r in rows)
    job_posts = sum(r.job_posts_created for r in rows)
    applications = sum(r.applications_created for r in rows)
    milestones = sum(r.milestones_completed for r in rows)

    window_days = (end_date - start_date).days + 1
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=window_days - 1)

    current_trends = db.execute(
        select(OpsEventDailyCount.event_type, func.sum(OpsEventDailyCount.event_count))
        .where(OpsEventDailyCount.metric_date >= start_date, OpsEventDailyCount.metric_date <= end_date)
        .group_by(OpsEventDailyCount.event_type)
    ).all()
    previous_trends = dict(
        db.execute(
            select(OpsEventDailyCount.event_type, func.sum(OpsEventDailyCount.event_count))
            .where(OpsEventDailyCount.metric_date >= prev_start, OpsEventDailyCount.metric_date <= prev_end)
            .group_by(OpsEventDailyCount.event_type)
        ).all()
    )

    trend_summaries: list[EventTrendSummaryOut] = []
    for event_type, current_total in current_trends:
        current_total = int(current_total or 0)
        previous_total = int(previous_trends.get(event_type, 0) or 0)
        delta = current_total - previous_total
        trend_summaries.append(
            EventTrendSummaryOut(
                event_type=event_type,
                current_total=current_total,
                previous_total=previous_total,
                trend_delta=delta,
                trend_percentage=_percentage(delta, previous_total) if previous_total > 0 else (100.0 if current_total > 0 else 0.0),
            )
        )

    return OperationsDashboardOut(
        start_date=start_date,
        end_date=end_date,
        retention=RetentionMetricsOut(
            active_users=active_users,
            returning_users=returning_users,
            retention_percentage=_percentage(returning_users, active_users),
        ),
        conversion=ConversionMetricsOut(
            interacted_users=interacted_users,
            applying_users=applying_users,
            converted_users=converted_users,
            conversion_percentage=_percentage(converted_users, interacted_users),
        ),
        funnel=FunnelMetricsOut(
            job_posts=job_posts,
            applications=applications,
            milestone_completions=milestones,
            post_to_application_percentage=_percentage(applications, job_posts),
            application_to_milestone_percentage=_percentage(milestones, applications),
        ),
        trend_summaries=sorted(trend_summaries, key=lambda x: x.event_type),
    )


@router.get("/operations/metrics/export.csv")
def export_operations_metrics_csv(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleType.SYSTEM_ADMINISTRATOR)),
) -> Response:
    if end_date < start_date:
        raise HTTPException(status_code=422, detail="end_date must be >= start_date")

    rows = _load_daily_rows(db, start_date, end_date)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "metric_date",
            "active_users",
            "returning_users",
            "retention_percentage",
            "interacted_users",
            "applying_users",
            "converted_users",
            "conversion_percentage",
            "job_posts_created",
            "applications_created",
            "milestones_completed",
            "post_to_application_percentage",
            "application_to_milestone_percentage",
        ]
    )

    for r in rows:
        writer.writerow(
            [
                r.metric_date.isoformat(),
                r.active_users,
                r.returning_users,
                _percentage(r.returning_users, r.active_users),
                r.interacted_users,
                r.applying_users,
                r.converted_users,
                _percentage(r.converted_users, r.interacted_users),
                r.job_posts_created,
                r.applications_created,
                r.milestones_completed,
                _percentage(r.applications_created, r.job_posts_created),
                _percentage(r.milestones_completed, r.applications_created),
            ]
        )

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=operations_metrics_{start_date}_{end_date}.csv"},
    )
