from datetime import datetime, timezone

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.enums import AuditAction
from app.core.audit import write_audit_log
from app.models.canary_release_config import CanaryReleaseConfig
from app.models.publishing_schedule import PublishingSchedule
from app.services.publishing_service import (
    activate_scheduled_publish,
    activate_scheduled_unpublish,
    expire_canary_if_due,
    record_publishing_history,
)


@celery_app.task(name="app.tasks.publishing_tasks.process_scheduled_publishing")
def process_scheduled_publishing() -> dict:
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        published_count = 0
        unpublished_count = 0
        canary_expired_count = 0

        schedules_to_publish = db.scalars(
            select(PublishingSchedule).where(
                PublishingSchedule.is_published.is_(False),
                PublishingSchedule.scheduled_publish_at <= now,
            )
        ).all()

        for schedule in schedules_to_publish:
            states = activate_scheduled_publish(db, schedule)
            write_audit_log(
                db,
                action=AuditAction.UPDATE,
                entity_type="publishing_schedule",
                entity_id=str(schedule.id),
                actor=None,
                request=None,
                before_data=states[0] if states else None,
                after_data={
                    "operation": "scheduled_publish",
                    "content_id": str(schedule.content_id),
                    "published_at": schedule.published_at.isoformat() if schedule.published_at else None,
                    "state": states[1] if states else None,
                },
                description="Scheduled publishing executed by scheduler",
            )
            published_count += 1

        schedules_to_unpublish = db.scalars(
            select(PublishingSchedule).where(
                PublishingSchedule.scheduled_unpublish_at.is_not(None),
                PublishingSchedule.is_unpublished.is_(False),
                PublishingSchedule.scheduled_unpublish_at <= now,
            )
        ).all()

        for schedule in schedules_to_unpublish:
            states = activate_scheduled_unpublish(db, schedule)
            write_audit_log(
                db,
                action=AuditAction.UPDATE,
                entity_type="publishing_schedule",
                entity_id=str(schedule.id),
                actor=None,
                request=None,
                before_data=states[0] if states else None,
                after_data={
                    "operation": "scheduled_unpublish",
                    "content_id": str(schedule.content_id),
                    "unpublished_at": schedule.unpublished_at.isoformat() if schedule.unpublished_at else None,
                    "state": states[1] if states else None,
                },
                description="Scheduled unpublishing executed by scheduler",
            )
            unpublished_count += 1

        active_canaries = db.scalars(
            select(CanaryReleaseConfig).where(
                CanaryReleaseConfig.is_enabled.is_(True),
                CanaryReleaseConfig.is_active.is_(True),
            )
        ).all()
        for canary in active_canaries:
            was_active = canary.is_active
            before = {
                "is_active": canary.is_active,
                "started_at": canary.started_at.isoformat() if canary.started_at else None,
                "completed_at": canary.completed_at.isoformat() if canary.completed_at else None,
            }
            expire_canary_if_due(db, canary)
            if was_active and not canary.is_active:
                after = {
                    "is_active": canary.is_active,
                    "started_at": canary.started_at.isoformat() if canary.started_at else None,
                    "completed_at": canary.completed_at.isoformat() if canary.completed_at else None,
                }
                record_publishing_history(
                    db,
                    content_id=canary.content_id,
                    action="canary_completed",
                    actor_id=canary.created_by_id,
                    reason="canary_duration_elapsed",
                    before_state=before,
                    after_state=after,
                )
                write_audit_log(
                    db,
                    action=AuditAction.UPDATE,
                    entity_type="canary_release",
                    entity_id=str(canary.id),
                    actor=None,
                    request=None,
                    before_data=before,
                    after_data=after,
                    description="Canary release completed by scheduler",
                )
                canary_expired_count += 1

        db.commit()
        return {
            "published_count": published_count,
            "unpublished_count": unpublished_count,
            "canary_expired_count": canary_expired_count,
        }
    finally:
        db.close()
