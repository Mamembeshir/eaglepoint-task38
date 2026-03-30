from datetime import datetime, timezone

from redis import Redis

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import SessionLocal
from app.services.user_deletion_service import process_due_user_hard_deletions


@celery_app.task(name="app.tasks.user_deletion_tasks.process_due_hard_deletions_daily")
def process_due_hard_deletions_daily() -> dict:
    redis_client = Redis.from_url(settings.redis_url)
    run_key = f"hard-delete-daily:{datetime.now(timezone.utc).strftime('%Y%m%d')}"
    acquired = redis_client.set(run_key, "1", nx=True, ex=23 * 60 * 60)
    if not acquired:
        return {"status": "skipped", "reason": "already_ran_today", "deleted_count": 0, "deleted_user_ids": []}

    db = SessionLocal()
    try:
        deleted_ids = process_due_user_hard_deletions(
            db,
            actor=None,
            request=None,
            source="scheduled_daily_job",
        )
        db.commit()
        return {
            "status": "completed",
            "deleted_count": len(deleted_ids),
            "deleted_user_ids": [str(user_id) for user_id in deleted_ids],
        }
    finally:
        db.close()
