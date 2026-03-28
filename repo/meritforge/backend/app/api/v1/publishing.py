from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.database import get_db
from app.core.enums import AuditAction, ContentStatus, RoleType, SegmentationType
from app.dependencies.auth import get_current_user, require_step_up_for_takedowns
from app.models.canary_release_config import CanaryReleaseConfig
from app.models.content import Content
from app.models.content_risk_assessment import ContentRiskAssessment
from app.models.publishing_history import PublishingHistory
from app.models.publishing_schedule import PublishingSchedule
from app.models.review_decision import ReviewDecision
from app.models.review_workflow_stage import ReviewWorkflowStage
from app.models.user import User
from app.schemas.publishing import (
    CanaryVisibilityOut,
    PublishingHistoryOut,
    SchedulePublishOut,
    SchedulePublishRequest,
    TakedownOut,
    TakedownRequest,
)
from app.services.publishing_service import (
    DEFAULT_CANARY_DURATION_MINUTES,
    DEFAULT_CANARY_PERCENTAGE,
    is_user_in_canary,
    record_publishing_history,
)

router = APIRouter(tags=["Publishing"])


def _role_name(user: User) -> str | None:
    if user.role is None:
        return None
    return user.role.name.value if hasattr(user.role.name, "value") else str(user.role.name)


def _assert_publishing_role(user: User) -> None:
    allowed = {
        RoleType.SYSTEM_ADMINISTRATOR.value,
        RoleType.CONTENT_AUTHOR.value,
        RoleType.EMPLOYER_MANAGER.value,
    }
    if _role_name(user) not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role permissions for publishing")


def _required_stages_complete(db: Session, content_id: UUID) -> bool:
    stages = db.scalars(
        select(ReviewWorkflowStage).where(ReviewWorkflowStage.content_id == content_id)
    ).all()
    required_stages = [stage for stage in stages if stage.is_required]
    if not required_stages:
        return False
    return all(stage.is_completed for stage in required_stages)


def _has_final_stage_approval(db: Session, content_id: UUID) -> bool:
    stages = db.scalars(
        select(ReviewWorkflowStage)
        .where(ReviewWorkflowStage.content_id == content_id)
        .order_by(ReviewWorkflowStage.stage_order.desc())
    ).all()
    if not stages:
        return False

    final_stage = stages[0]
    latest_decision = db.scalar(
        select(ReviewDecision)
        .where(ReviewDecision.stage_id == final_stage.id)
        .order_by(ReviewDecision.created_at.desc())
    )
    if not latest_decision:
        return False

    return str(latest_decision.decision).lower() == "approve"


@router.post("/publishing/content/{content_id}/schedule", response_model=SchedulePublishOut)
def schedule_publishing(
    content_id: UUID,
    payload: SchedulePublishRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SchedulePublishOut:
    _assert_publishing_role(current_user)

    content = db.scalar(select(Content).where(Content.id == content_id))
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")

    if payload.scheduled_unpublish_at and payload.scheduled_unpublish_at <= payload.scheduled_publish_at:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="scheduled_unpublish_at must be after scheduled_publish_at")

    if content.is_locked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Locked content cannot be scheduled")

    risk_assessment = db.scalar(select(ContentRiskAssessment).where(ContentRiskAssessment.content_id == content.id))
    if risk_assessment and risk_assessment.blocked_until_final_approval and not _has_final_stage_approval(db, content.id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Content is blocked until final-stage approval is recorded",
        )

    schedule = db.scalar(select(PublishingSchedule).where(PublishingSchedule.content_id == content.id))
    before_schedule = None
    if schedule:
        before_schedule = {
            "scheduled_publish_at": schedule.scheduled_publish_at.isoformat(),
            "scheduled_unpublish_at": schedule.scheduled_unpublish_at.isoformat() if schedule.scheduled_unpublish_at else None,
            "is_published": schedule.is_published,
            "is_unpublished": schedule.is_unpublished,
        }
        schedule.scheduled_publish_at = payload.scheduled_publish_at
        schedule.scheduled_unpublish_at = payload.scheduled_unpublish_at
        schedule.is_published = False
        schedule.is_unpublished = False
        schedule.published_at = None
        schedule.unpublished_at = None
        schedule.created_by_id = current_user.id
    else:
        schedule = PublishingSchedule(
            content_id=content.id,
            scheduled_publish_at=payload.scheduled_publish_at,
            scheduled_unpublish_at=payload.scheduled_unpublish_at,
            created_by_id=current_user.id,
        )
        db.add(schedule)

    canary_input = payload.canary
    canary_enabled = bool(canary_input and canary_input.enabled)
    canary = db.scalar(select(CanaryReleaseConfig).where(CanaryReleaseConfig.content_id == content.id))
    if canary_enabled:
        percentage = canary_input.percentage if canary_input and canary_input.percentage is not None else DEFAULT_CANARY_PERCENTAGE
        duration = canary_input.duration_minutes if canary_input and canary_input.duration_minutes is not None else DEFAULT_CANARY_DURATION_MINUTES
        segmentation_type = canary_input.segmentation_type if canary_input and canary_input.segmentation_type else SegmentationType.RANDOM
        target_cohort_ids = [str(x) for x in (canary_input.target_cohort_ids or [])] if canary_input else []

        if segmentation_type == SegmentationType.COHORT and not target_cohort_ids:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="cohort-based segmentation requires target_cohort_ids")

        if canary:
            canary.is_enabled = True
            canary.is_active = False
            canary.percentage = percentage
            canary.duration_minutes = duration
            canary.segmentation_type = segmentation_type
            canary.target_cohort_ids = target_cohort_ids if segmentation_type == SegmentationType.COHORT else None
            canary.started_at = None
            canary.completed_at = None
            canary.created_by_id = current_user.id
        else:
            canary = CanaryReleaseConfig(
                content_id=content.id,
                is_enabled=True,
                is_active=False,
                percentage=percentage,
                duration_minutes=duration,
                segmentation_type=segmentation_type,
                target_cohort_ids=target_cohort_ids if segmentation_type == SegmentationType.COHORT else None,
                created_by_id=current_user.id,
            )
            db.add(canary)
    else:
        if canary:
            canary.is_enabled = False
            canary.is_active = False
            canary.started_at = None
            canary.completed_at = None

    before_state = {
        "status": content.status.value if hasattr(content.status, "value") else str(content.status),
        "schedule": before_schedule,
    }
    after_state = {
        "status": content.status.value if hasattr(content.status, "value") else str(content.status),
        "schedule": {
            "scheduled_publish_at": schedule.scheduled_publish_at.isoformat(),
            "scheduled_unpublish_at": schedule.scheduled_unpublish_at.isoformat() if schedule.scheduled_unpublish_at else None,
        },
        "canary": {
            "enabled": canary.is_enabled if canary else False,
            "percentage": canary.percentage if canary else 0,
            "duration_minutes": canary.duration_minutes if canary else 0,
            "segmentation_type": (canary.segmentation_type.value if canary else SegmentationType.RANDOM.value),
        },
    }

    record_publishing_history(
        db,
        content_id=content.id,
        action="schedule_set",
        actor_id=current_user.id,
        reason="scheduled_publishing_configured",
        before_state=before_state,
        after_state=after_state,
    )
    write_audit_log(
        db,
        action=AuditAction.UPDATE,
        entity_type="publishing_schedule",
        entity_id=str(content.id),
        actor=current_user,
        request=request,
        before_data=before_state,
        after_data=after_state,
        description="Configured scheduled publishing and canary release",
    )

    if content.status == ContentStatus.UNDER_REVIEW:
        if _required_stages_complete(db, content.id) and _has_final_stage_approval(db, content.id):
            content.status = ContentStatus.APPROVED
    db.commit()
    db.refresh(schedule)
    if canary:
        db.refresh(canary)

    return SchedulePublishOut(
        content_id=content.id,
        status=content.status,
        scheduled_publish_at=schedule.scheduled_publish_at,
        scheduled_unpublish_at=schedule.scheduled_unpublish_at,
        canary_enabled=bool(canary and canary.is_enabled),
        canary_percentage=canary.percentage if canary else 0,
        canary_duration_minutes=canary.duration_minutes or 0 if canary else 0,
        canary_segmentation_type=canary.segmentation_type if canary else SegmentationType.RANDOM,
    )


@router.post("/publishing/content/{content_id}/takedown", response_model=TakedownOut)
def takedown_content(
    content_id: UUID,
    payload: TakedownRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_step_up_for_takedowns),
) -> TakedownOut:
    _assert_publishing_role(current_user)

    content = db.scalar(select(Content).where(Content.id == content_id))
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")

    now = datetime.now(timezone.utc)
    before = {
        "status": content.status.value if hasattr(content.status, "value") else str(content.status),
        "retracted_at": content.retracted_at.isoformat() if content.retracted_at else None,
    }

    content.status = ContentStatus.RETRACTED
    content.retracted_at = now
    content.is_locked = True

    schedule = db.scalar(select(PublishingSchedule).where(PublishingSchedule.content_id == content.id))
    if schedule:
        schedule.is_unpublished = True
        schedule.unpublished_at = now

    canary = db.scalar(select(CanaryReleaseConfig).where(CanaryReleaseConfig.content_id == content.id))
    if canary:
        canary.is_active = False
        canary.is_enabled = False
        canary.completed_at = now

    after = {
        "status": content.status.value,
        "retracted_at": content.retracted_at.isoformat(),
        "notice": "This content has been retracted.",
    }

    record_publishing_history(
        db,
        content_id=content.id,
        action="takedown_soft_delete",
        actor_id=current_user.id,
        reason=payload.reason,
        before_state=before,
        after_state=after,
    )
    write_audit_log(
        db,
        action=AuditAction.UPDATE,
        entity_type="content_takedown",
        entity_id=str(content.id),
        actor=current_user,
        request=request,
        before_data=before,
        after_data=after,
        changes={"reason": payload.reason},
        description="Soft takedown with retracted notice",
    )
    db.commit()

    return TakedownOut(
        content_id=content.id,
        status=content.status,
        notice="This content has been retracted.",
        retracted_at=content.retracted_at,
    )


@router.get("/publishing/content/{content_id}/visibility/{user_id}", response_model=CanaryVisibilityOut)
def check_canary_visibility(
    content_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CanaryVisibilityOut:
    current_role = _role_name(current_user)
    if user_id != current_user.id and current_role != RoleType.SYSTEM_ADMINISTRATOR.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot query visibility for another user")

    visible, reason = is_user_in_canary(db, content_id, user_id)
    return CanaryVisibilityOut(content_id=content_id, user_id=user_id, visible=visible, reason=reason)


@router.get("/publishing/content/{content_id}/history", response_model=list[PublishingHistoryOut])
def get_publishing_history(
    content_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[PublishingHistoryOut]:
    history_rows = db.scalars(
        select(PublishingHistory)
        .where(PublishingHistory.content_id == content_id)
        .order_by(PublishingHistory.created_at.desc())
    ).all()
    return [
        PublishingHistoryOut(
            id=h.id,
            action=h.action,
            actor_id=h.actor_id,
            reason=h.reason,
            before_state=h.before_state,
            after_state=h.after_state,
            created_at=h.created_at,
        )
        for h in history_rows
    ]
