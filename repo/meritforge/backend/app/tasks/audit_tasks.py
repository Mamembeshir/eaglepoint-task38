from datetime import datetime, timedelta, timezone

from sqlalchemy import delete

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.audit_log import AuditLog


RETENTION_DAYS = 365


@celery_app.task(name="app.tasks.audit_tasks.cleanup_expired_audit_logs")
def cleanup_expired_audit_logs() -> dict:
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
        result = db.execute(delete(AuditLog).where(AuditLog.created_at < cutoff))
        deleted_count = int(result.rowcount or 0)
        db.commit()
        return {"deleted_count": deleted_count, "retention_days": RETENTION_DAYS, "cutoff": cutoff.isoformat()}
    finally:
        db.close()
