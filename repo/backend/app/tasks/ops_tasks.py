from datetime import date, timedelta

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.ops_metrics_service import aggregate_ops_for_day, aggregate_ops_range


@celery_app.task(name="app.tasks.ops_tasks.aggregate_previous_day_metrics")
def aggregate_previous_day_metrics() -> dict:
    db = SessionLocal()
    try:
        target = date.today() - timedelta(days=1)
        metric = aggregate_ops_for_day(db, target)
        db.commit()
        return {
            "metric_date": metric.metric_date.isoformat(),
            "active_users": metric.active_users,
            "interacted_users": metric.interacted_users,
            "converted_users": metric.converted_users,
        }
    finally:
        db.close()


@celery_app.task(name="app.tasks.ops_tasks.backfill_recent_metrics")
def backfill_recent_metrics(days: int = 30) -> dict:
    db = SessionLocal()
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=max(1, days) - 1)
        rows = aggregate_ops_range(db, start_date=start_date, end_date=end_date)
        db.commit()
        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "rows_aggregated": len(rows),
        }
    finally:
        db.close()
