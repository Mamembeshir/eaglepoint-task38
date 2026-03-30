import os

from celery import Celery


redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "meritforge",
    broker=redis_url,
    backend=redis_url,
    include=[
        "app.tasks.publishing_tasks",
        "app.tasks.ops_tasks",
        "app.tasks.audit_tasks",
        "app.tasks.webhook_tasks",
        "app.tasks.user_deletion_tasks",
    ],
)

celery_app.conf.update(
    timezone="UTC",
    enable_utc=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    beat_schedule={
        "process-scheduled-publishing": {
            "task": "app.tasks.publishing_tasks.process_scheduled_publishing",
            "schedule": 60.0,
        },
        "aggregate-previous-day-ops-metrics": {
            "task": "app.tasks.ops_tasks.aggregate_previous_day_metrics",
            "schedule": 3600.0,
        },
        "backfill-recent-ops-metrics": {
            "task": "app.tasks.ops_tasks.backfill_recent_metrics",
            "schedule": 21600.0,
        },
        "cleanup-expired-audit-logs": {
            "task": "app.tasks.audit_tasks.cleanup_expired_audit_logs",
            "schedule": 86400.0,
        },
        "process-due-hard-deletions-daily": {
            "task": "app.tasks.user_deletion_tasks.process_due_hard_deletions_daily",
            "schedule": 86400.0,
        },
    },
)
