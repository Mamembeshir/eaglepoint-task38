from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import ContentStatus, SegmentationType
from app.models.canary_release_config import CanaryReleaseConfig
from app.models.content import Content
from app.models.publishing_history import PublishingHistory
from app.models.publishing_schedule import PublishingSchedule
from app.models.user import User


DEFAULT_CANARY_PERCENTAGE = 5
DEFAULT_CANARY_DURATION_MINUTES = 120


def deterministic_user_bucket(user_id: UUID) -> int:
    return user_id.int % 100


def is_user_in_canary(db: Session, content_id: UUID, user_id: UUID) -> tuple[bool, str]:
    content = db.scalar(select(Content).where(Content.id == content_id))
    if not content:
        return False, "content_not_found"
    if content.status == ContentStatus.RETRACTED:
        return False, "retracted"

    config = db.scalar(select(CanaryReleaseConfig).where(CanaryReleaseConfig.content_id == content_id))
    if not config or not config.is_enabled or not config.is_active:
        return True, "no_active_canary"

    if config.segmentation_type == SegmentationType.COHORT:
        user = db.scalar(select(User).where(User.id == user_id))
        if not user:
            return False, "user_not_found"
        target_ids = set(config.target_cohort_ids or [])
        user_cohorts = {str(c.id) for c in user.cohorts}
        visible = len(target_ids.intersection(user_cohorts)) > 0
        return visible, "cohort_match" if visible else "cohort_no_match"

    bucket = deterministic_user_bucket(user_id)
    visible = bucket < int(config.percentage)
    return visible, f"deterministic_bucket_{bucket}"


def record_publishing_history(
    db: Session,
    *,
    content_id: UUID,
    action: str,
    actor_id: UUID | None,
    reason: str | None,
    before_state: dict | None,
    after_state: dict | None,
) -> None:
    db.add(
        PublishingHistory(
            content_id=content_id,
            action=action,
            actor_id=actor_id,
            reason=reason,
            before_state=before_state,
            after_state=after_state,
        )
    )


def activate_scheduled_publish(db: Session, schedule: PublishingSchedule) -> tuple[dict, dict] | None:
    now = datetime.now(timezone.utc)
    content = db.scalar(select(Content).where(Content.id == schedule.content_id))
    if not content:
        return None

    before = {
        "status": content.status.value if hasattr(content.status, "value") else str(content.status),
        "published_at": content.published_at.isoformat() if content.published_at else None,
    }

    content.status = ContentStatus.PUBLISHED
    content.published_at = now
    schedule.is_published = True
    schedule.published_at = now

    canary = db.scalar(select(CanaryReleaseConfig).where(CanaryReleaseConfig.content_id == content.id))
    if canary and canary.is_enabled:
        canary.is_active = True
        canary.started_at = now

    after = {
        "status": content.status.value,
        "published_at": content.published_at.isoformat() if content.published_at else None,
    }
    record_publishing_history(
        db,
        content_id=content.id,
        action="scheduled_publish",
        actor_id=schedule.created_by_id,
        reason="scheduled_publish_triggered",
        before_state=before,
        after_state=after,
    )
    return before, after


def activate_scheduled_unpublish(db: Session, schedule: PublishingSchedule) -> tuple[dict, dict] | None:
    now = datetime.now(timezone.utc)
    content = db.scalar(select(Content).where(Content.id == schedule.content_id))
    if not content:
        return None

    before = {
        "status": content.status.value if hasattr(content.status, "value") else str(content.status),
        "retracted_at": content.retracted_at.isoformat() if content.retracted_at else None,
    }

    content.status = ContentStatus.RETRACTED
    content.retracted_at = now
    schedule.is_unpublished = True
    schedule.unpublished_at = now

    after = {
        "status": content.status.value,
        "retracted_at": content.retracted_at.isoformat() if content.retracted_at else None,
        "notice": "This content has been retracted.",
    }
    record_publishing_history(
        db,
        content_id=content.id,
        action="scheduled_unpublish",
        actor_id=schedule.created_by_id,
        reason="scheduled_unpublish_triggered",
        before_state=before,
        after_state=after,
    )
    return before, after


def expire_canary_if_due(db: Session, canary: CanaryReleaseConfig) -> None:
    if not canary.is_active or not canary.started_at:
        return
    duration = canary.duration_minutes or DEFAULT_CANARY_DURATION_MINUTES
    due_at = canary.started_at + timedelta(minutes=duration)
    if due_at <= datetime.now(timezone.utc):
        canary.is_active = False
        canary.completed_at = datetime.now(timezone.utc)
