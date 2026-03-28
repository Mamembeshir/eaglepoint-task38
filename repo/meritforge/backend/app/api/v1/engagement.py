from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.database import get_db
from app.core.enums import AnnotationVisibility, AuditAction, EventType, RoleType
from app.dependencies.auth import get_current_user
from app.models.annotation import Annotation
from app.models.annotation_revision import AnnotationRevision
from app.models.content import Content
from app.models.event_telemetry import EventTelemetry
from app.models.student_milestone_template import StudentMilestoneTemplate
from app.models.student_progress_milestone import StudentProgressMilestone
from app.models.student_progress_milestone_revision import StudentProgressMilestoneRevision
from app.models.user import User
from app.schemas.engagement import (
    AnnotationCreateRequest,
    AnnotationOut,
    AnnotationUpdateRequest,
    ManualMilestoneCreateRequest,
    MilestoneOut,
    MilestoneTemplateCreateRequest,
    MilestoneTemplateOut,
    MilestoneUpdateRequest,
    PlaybackProgressOut,
    TelemetryEventOut,
    TelemetryEventRequest,
)

router = APIRouter(tags=["Engagement"])


def _role_name(user: User) -> str | None:
    if user.role is None:
        return None
    return user.role.name.value if hasattr(user.role.name, "value") else str(user.role.name)


def _can_manage_student_progress(actor: User, student_id: UUID) -> bool:
    if actor.id == student_id:
        return True
    return _role_name(actor) in {RoleType.EMPLOYER_MANAGER.value, RoleType.SYSTEM_ADMINISTRATOR.value}


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
        achieved_date = date.today() if achieved else None

        if milestone:
            milestone.progress_value = int(event_count)
            milestone.target_value = template.threshold_count
            milestone.source = "automated"
            milestone.is_custom = False
            milestone.last_event_at = event.created_at
            if achieved and milestone.achievement_date is None:
                milestone.achievement_date = achieved_date
            milestone.version += 1
        else:
            db.add(
                StudentProgressMilestone(
                    student_id=user.id,
                    milestone_template_id=template.id,
                    milestone_type="predefined",
                    milestone_name=template.name,
                    description=template.description,
                    achievement_date=achieved_date,
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


@router.get('/telemetry/progress', response_model=list[PlaybackProgressOut])
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
                progress_value = int(row.event_data.get('position_seconds', 0) or 0)
            except Exception:
                progress_value = 0
        latest[key] = PlaybackProgressOut(
            content_id=row.content_id,
            progress_seconds=progress_value,
            updated_at=row.created_at,
        )

    return list(latest.values())


@router.post("/milestone-templates", response_model=MilestoneTemplateOut, status_code=status.HTTP_201_CREATED)
def create_milestone_template(
    payload: MilestoneTemplateCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MilestoneTemplateOut:
    if _role_name(current_user) not in {RoleType.SYSTEM_ADMINISTRATOR.value, RoleType.EMPLOYER_MANAGER.value}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role permissions")

    existing = db.scalar(select(StudentMilestoneTemplate).where(StudentMilestoneTemplate.key == payload.key))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Milestone template key already exists")

    template = StudentMilestoneTemplate(
        key=payload.key,
        name=payload.name,
        description=payload.description,
        is_predefined=payload.is_predefined,
        automation_event_type=payload.automation_event_type,
        threshold_count=payload.threshold_count,
        created_by_id=current_user.id,
    )
    db.add(template)
    db.flush()

    write_audit_log(
        db,
        action=AuditAction.CREATE,
        entity_type="student_milestone_template",
        entity_id=str(template.id),
        actor=current_user,
        request=request,
        after_data={
            "key": template.key,
            "automation_event_type": template.automation_event_type.value if template.automation_event_type else None,
            "threshold_count": template.threshold_count,
        },
        description="Created student milestone template",
    )
    db.commit()

    return MilestoneTemplateOut(
        id=template.id,
        key=template.key,
        name=template.name,
        description=template.description,
        is_predefined=template.is_predefined,
        is_active=template.is_active,
        automation_event_type=template.automation_event_type,
        threshold_count=template.threshold_count,
        created_at=template.created_at,
    )


@router.post("/students/{student_id}/milestones/manual", response_model=MilestoneOut, status_code=status.HTTP_201_CREATED)
def create_manual_milestone(
    student_id: UUID,
    payload: ManualMilestoneCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MilestoneOut:
    if not _can_manage_student_progress(current_user, student_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to update this student's milestones")

    student = db.scalar(select(User).where(User.id == student_id, User.is_active.is_(True)))
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    template = None
    if payload.milestone_template_id:
        template = db.scalar(select(StudentMilestoneTemplate).where(StudentMilestoneTemplate.id == payload.milestone_template_id))
        if not template:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone template not found")

    milestone = StudentProgressMilestone(
        student_id=student_id,
        milestone_template_id=payload.milestone_template_id,
        milestone_type=payload.milestone_type,
        milestone_name=payload.milestone_name,
        description=payload.description,
        achievement_date=payload.achievement_date,
        metadata_json=payload.metadata_json,
        is_custom=template is None,
        source="manual",
        progress_value=payload.progress_value,
        target_value=payload.target_value,
        version=1,
    )
    db.add(milestone)
    db.flush()

    write_audit_log(
        db,
        action=AuditAction.CREATE,
        entity_type="student_progress_milestone",
        entity_id=str(milestone.id),
        actor=current_user,
        request=request,
        after_data={
            "student_id": str(student_id),
            "milestone_name": milestone.milestone_name,
            "is_custom": milestone.is_custom,
            "source": milestone.source,
        },
        description="Created manual student milestone",
    )
    db.commit()

    return MilestoneOut(
        id=milestone.id,
        student_id=milestone.student_id,
        milestone_template_id=milestone.milestone_template_id,
        milestone_type=milestone.milestone_type,
        milestone_name=milestone.milestone_name,
        is_custom=milestone.is_custom,
        source=milestone.source,
        progress_value=milestone.progress_value,
        target_value=milestone.target_value,
        achievement_date=milestone.achievement_date,
        updated_at=milestone.updated_at,
        version=milestone.version,
    )


@router.patch("/students/{student_id}/milestones/{milestone_id}", response_model=MilestoneOut)
def update_milestone_latest_wins(
    student_id: UUID,
    milestone_id: UUID,
    payload: MilestoneUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MilestoneOut:
    if not _can_manage_student_progress(current_user, student_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to update this student's milestones")

    milestone = db.scalar(
        select(StudentProgressMilestone).where(
            StudentProgressMilestone.id == milestone_id,
            StudentProgressMilestone.student_id == student_id,
        )
    )
    if not milestone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found")

    # Latest-write-wins: server accepts later-arriving updates and records revisions.

    previous_data = {
        "milestone_name": milestone.milestone_name,
        "description": milestone.description,
        "achievement_date": milestone.achievement_date.isoformat() if milestone.achievement_date else None,
        "metadata_json": milestone.metadata_json,
        "progress_value": milestone.progress_value,
        "target_value": milestone.target_value,
        "updated_at": milestone.updated_at.isoformat(),
        "version": milestone.version,
    }
    db.add(
        StudentProgressMilestoneRevision(
            milestone_id=milestone.id,
            revision_number=milestone.version,
            previous_data=previous_data,
            changed_by_id=current_user.id,
        )
    )

    updates = payload.model_dump(exclude_unset=True)
    updates.pop("client_updated_at", None)
    for key, value in updates.items():
        setattr(milestone, key, value)
    milestone.version += 1

    write_audit_log(
        db,
        action=AuditAction.UPDATE,
        entity_type="student_progress_milestone",
        entity_id=str(milestone.id),
        actor=current_user,
        request=request,
        before_data=previous_data,
        after_data={
            "milestone_name": milestone.milestone_name,
            "description": milestone.description,
            "achievement_date": milestone.achievement_date.isoformat() if milestone.achievement_date else None,
            "metadata_json": milestone.metadata_json,
            "progress_value": milestone.progress_value,
            "target_value": milestone.target_value,
            "version": milestone.version,
        },
        changes=updates,
        description="Updated milestone using latest-update-wins policy",
    )
    db.commit()

    return MilestoneOut(
        id=milestone.id,
        student_id=milestone.student_id,
        milestone_template_id=milestone.milestone_template_id,
        milestone_type=milestone.milestone_type,
        milestone_name=milestone.milestone_name,
        is_custom=milestone.is_custom,
        source=milestone.source,
        progress_value=milestone.progress_value,
        target_value=milestone.target_value,
        achievement_date=milestone.achievement_date,
        updated_at=milestone.updated_at,
        version=milestone.version,
    )


@router.get('/students/{student_id}/milestones', response_model=list[MilestoneOut])
def list_student_milestones(
    student_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MilestoneOut]:
    if not _can_manage_student_progress(current_user, student_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view this student's milestones")

    milestones = db.scalars(
        select(StudentProgressMilestone)
        .where(StudentProgressMilestone.student_id == student_id)
        .order_by(StudentProgressMilestone.updated_at.desc())
    ).all()

    return [
        MilestoneOut(
            id=m.id,
            student_id=m.student_id,
            milestone_template_id=m.milestone_template_id,
            milestone_type=m.milestone_type,
            milestone_name=m.milestone_name,
            is_custom=m.is_custom,
            source=m.source,
            progress_value=m.progress_value,
            target_value=m.target_value,
            achievement_date=m.achievement_date,
            updated_at=m.updated_at,
            version=m.version,
        )
        for m in milestones
    ]


def _annotation_visible_to_user(annotation: Annotation, user: User) -> bool:
    if annotation.author_id == user.id:
        return True
    if annotation.visibility == AnnotationVisibility.PUBLIC:
        return True
    if annotation.visibility == AnnotationVisibility.PRIVATE:
        return False
    if annotation.visibility == AnnotationVisibility.COHORT:
        if not annotation.cohort_id:
            return False
        user_cohort_ids = {c.id for c in user.cohorts}
        return annotation.cohort_id in user_cohort_ids
    return False


def _annotation_source_text(content: Content) -> str:
    version = content.current_version
    if version and version.body:
        return version.body

    metadata_json = version.metadata_json if version and isinstance(version.metadata_json, dict) else {}
    transcript = metadata_json.get("transcript") or metadata_json.get("transcript_text")
    if isinstance(transcript, str) and transcript.strip():
        return transcript

    submission_metadata = metadata_json.get("submission_metadata")
    if isinstance(submission_metadata, dict):
        nested_transcript = submission_metadata.get("transcript") or submission_metadata.get("summary")
        if isinstance(nested_transcript, str) and nested_transcript.strip():
            return nested_transcript

    summary = metadata_json.get("summary")
    if isinstance(summary, str) and summary.strip():
        return summary

    return ""


@router.post("/annotations", response_model=AnnotationOut, status_code=status.HTTP_201_CREATED)
def create_annotation(
    payload: AnnotationCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnnotationOut:
    if payload.end_offset <= payload.start_offset:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="end_offset must be > start_offset")

    if payload.visibility == AnnotationVisibility.COHORT and not payload.cohort_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="cohort visibility requires cohort_id")

    content = db.scalar(select(Content).where(Content.id == payload.content_id))
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")

    source_text = _annotation_source_text(content)
    if not source_text:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No annotation source text available for this content")
    if payload.end_offset > len(source_text):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Annotation range is outside content text length")
    if payload.highlighted_text is not None:
        expected = source_text[payload.start_offset:payload.end_offset]
        if payload.highlighted_text != expected:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="highlighted_text does not match provided offsets")

    annotation = Annotation(
        content_id=payload.content_id,
        author_id=current_user.id,
        visibility=payload.visibility,
        cohort_id=payload.cohort_id,
        start_offset=payload.start_offset,
        end_offset=payload.end_offset,
        highlighted_text=payload.highlighted_text,
        annotation_text=payload.annotation_text,
        color=payload.color,
        tags=payload.tags,
        version=1,
    )
    db.add(annotation)
    db.flush()

    write_audit_log(
        db,
        action=AuditAction.CREATE,
        entity_type="annotation",
        entity_id=str(annotation.id),
        actor=current_user,
        request=request,
        after_data={
            "content_id": str(annotation.content_id),
            "visibility": annotation.visibility.value if hasattr(annotation.visibility, "value") else str(annotation.visibility),
            "cohort_id": str(annotation.cohort_id) if annotation.cohort_id else None,
        },
        description="Created annotation",
    )
    db.commit()

    return AnnotationOut(
        id=annotation.id,
        content_id=annotation.content_id,
        author_id=annotation.author_id,
        visibility=annotation.visibility,
        cohort_id=annotation.cohort_id,
        start_offset=annotation.start_offset,
        end_offset=annotation.end_offset,
        highlighted_text=annotation.highlighted_text,
        annotation_text=annotation.annotation_text,
        color=annotation.color,
        tags=annotation.tags,
        updated_at=annotation.updated_at,
        version=annotation.version,
    )


@router.get("/contents/{content_id}/annotations", response_model=list[AnnotationOut])
def list_visible_annotations(
    content_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AnnotationOut]:
    annotations = db.scalars(select(Annotation).where(Annotation.content_id == content_id)).all()
    visible = [a for a in annotations if _annotation_visible_to_user(a, current_user)]
    return [
        AnnotationOut(
            id=a.id,
            content_id=a.content_id,
            author_id=a.author_id,
            visibility=a.visibility,
            cohort_id=a.cohort_id,
            start_offset=a.start_offset,
            end_offset=a.end_offset,
            highlighted_text=a.highlighted_text,
            annotation_text=a.annotation_text,
            color=a.color,
            tags=a.tags,
            updated_at=a.updated_at,
            version=a.version,
        )
        for a in visible
    ]


@router.patch("/annotations/{annotation_id}", response_model=AnnotationOut)
def update_annotation_latest_wins(
    annotation_id: UUID,
    payload: AnnotationUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnnotationOut:
    annotation = db.scalar(select(Annotation).where(Annotation.id == annotation_id))
    if not annotation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Annotation not found")
    if annotation.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only author can update annotation")

    # Latest-write-wins: server accepts later-arriving updates and records revisions.

    previous_data = {
        "visibility": annotation.visibility.value if hasattr(annotation.visibility, "value") else str(annotation.visibility),
        "cohort_id": str(annotation.cohort_id) if annotation.cohort_id else None,
        "annotation_text": annotation.annotation_text,
        "color": annotation.color,
        "tags": annotation.tags,
        "updated_at": annotation.updated_at.isoformat(),
        "version": annotation.version,
    }
    db.add(
        AnnotationRevision(
            annotation_id=annotation.id,
            revision_number=annotation.version,
            previous_data=previous_data,
            changed_by_id=current_user.id,
        )
    )

    updates = payload.model_dump(exclude_unset=True)
    updates.pop("client_updated_at", None)
    if "visibility" in updates and updates["visibility"] == AnnotationVisibility.COHORT and not updates.get("cohort_id") and not annotation.cohort_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="cohort visibility requires cohort_id")

    for key, value in updates.items():
        setattr(annotation, key, value)
    annotation.version += 1

    write_audit_log(
        db,
        action=AuditAction.UPDATE,
        entity_type="annotation",
        entity_id=str(annotation.id),
        actor=current_user,
        request=request,
        before_data=previous_data,
        after_data={
            "visibility": annotation.visibility.value if hasattr(annotation.visibility, "value") else str(annotation.visibility),
            "cohort_id": str(annotation.cohort_id) if annotation.cohort_id else None,
            "annotation_text": annotation.annotation_text,
            "color": annotation.color,
            "tags": annotation.tags,
            "version": annotation.version,
        },
        changes=updates,
        description="Updated annotation using latest-update-wins policy",
    )
    db.commit()

    return AnnotationOut(
        id=annotation.id,
        content_id=annotation.content_id,
        author_id=annotation.author_id,
        visibility=annotation.visibility,
        cohort_id=annotation.cohort_id,
        start_offset=annotation.start_offset,
        end_offset=annotation.end_offset,
        highlighted_text=annotation.highlighted_text,
        annotation_text=annotation.annotation_text,
        color=annotation.color,
        tags=annotation.tags,
        updated_at=annotation.updated_at,
        version=annotation.version,
    )
