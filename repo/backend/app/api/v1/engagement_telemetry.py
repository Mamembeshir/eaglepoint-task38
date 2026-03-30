from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.database import get_db
from app.core.enums import AuditAction, EventType
from app.dependencies.auth import get_current_user
from app.models.event_telemetry import EventTelemetry
from app.models.student_milestone_template import StudentMilestoneTemplate
from app.models.student_progress_milestone import StudentProgressMilestone
from app.models.user import User
from app.schemas.engagement import PlaybackProgressOut, TelemetryEventOut, TelemetryEventRequest

router = APIRouter(tags=["Engagement"])


def _apply_automated_milestones(db: Session, user: User, event: EventTelemetry) -> None:
    templates = db.scalars(
        select(StudentMilestoneTemplate).where(
            StudentMilestoneTemplate.is_active.is_(True),
            StudentMilestoneTemplate.automation_event_type == event.event_type,
        )
    ).all()

    if not templates:
        return

    for template in templates:
        event_count = db.scalar(
            select(func.count(EventTelemetry.id)).where(
                EventTelemetry.user_id == user.id,
                EventTelemetry.event_type == event.event_type,
            )
        ) or 0

        milestone = db.scalar(
            select(StudentProgressMilestone).where(
                StudentProgressMilestone.student_id == user.id,
                StudentProgressMilestone.milestone_template_id == template.id,
            )
        )

        achieved = int(event_count) >= template.threshold_count

        if milestone:
            milestone.progress_value = int(event_count)
            milestone.target_value = template.threshold_count
            milestone.source = "automated"
            milestone.is_custom = False
            milestone.last_event_at = event.created_at
            if achieved and milestone.achievement_date is None:
                milestone.achievement_date = event.created_at.date()
            milestone.version += 1
        else:
            db.add(
                StudentProgressMilestone(
                    student_id=user.id,
                    milestone_template_id=template.id,
                    milestone_type="predefined",
                    milestone_name=template.name,
                    description=template.description,
                    achievement_date=event.created_at.date() if achieved else None,
                    metadata_json={"template_key": template.key, "threshold_count": template.threshold_count},
                    is_custom=False,
                    source="automated",
                    progress_value=int(event_count),
                    target_value=template.threshold_count,
                    last_event_at=event.created_at,
                )
            )


@router.post("/telemetry/events", response_model=TelemetryEventOut, status_code=status.HTTP_201_CREATED)
def create_telemetry_event(
    payload: TelemetryEventRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TelemetryEventOut:
    event = EventTelemetry(
        event_type=payload.event_type,
        user_id=current_user.id,
        session_id=payload.session_id,
        content_id=payload.content_id,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        event_data=payload.event_data,
        duration_seconds=payload.duration_seconds,
        progress_percentage=payload.progress_percentage,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(event)
    db.flush()

    _apply_automated_milestones(db, current_user, event)

    write_audit_log(
        db,
        action=AuditAction.CREATE,
        entity_type="event_telemetry",
        entity_id=str(event.id),
        actor=current_user,
        request=request,
        after_data={
            "event_type": payload.event_type.value,
            "content_id": str(payload.content_id) if payload.content_id else None,
            "resource_type": payload.resource_type,
            "resource_id": payload.resource_id,
        },
        description="Created telemetry event and processed milestone automation",
    )
    db.commit()

    return TelemetryEventOut(
        id=event.id,
        event_type=event.event_type,
        user_id=event.user_id,
        content_id=event.content_id,
        created_at=event.created_at,
    )


@router.get("/telemetry/progress", response_model=list[PlaybackProgressOut])
def get_playback_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PlaybackProgressOut]:
    rows = db.scalars(
        select(EventTelemetry)
        .where(
            EventTelemetry.user_id == current_user.id,
            EventTelemetry.event_type == EventType.PLAY,
            EventTelemetry.content_id.is_not(None),
        )
        .order_by(EventTelemetry.created_at.desc())
    ).all()

    latest: dict[str, PlaybackProgressOut] = {}
    for row in rows:
        key = str(row.content_id)
        if key in latest:
            continue
        progress_value = 0
        if isinstance(row.event_data, dict):
            try:
                progress_value = int(row.event_data.get("position_seconds", 0) or 0)
            except Exception:
                progress_value = 0
        latest[key] = PlaybackProgressOut(
            content_id=row.content_id,
            progress_seconds=progress_value,
            updated_at=row.created_at,
        )

    return list(latest.values())
