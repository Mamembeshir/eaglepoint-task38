from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.database import get_db
from app.core.enums import AuditAction, RoleType
from app.dependencies.auth import get_current_user
from app.models.application import Application
from app.models.job_post import JobPost
from app.models.student_milestone_template import StudentMilestoneTemplate
from app.models.student_progress_milestone import StudentProgressMilestone
from app.models.student_progress_milestone_revision import StudentProgressMilestoneRevision
from app.models.user import User
from app.schemas.engagement import (
    ManualMilestoneCreateRequest,
    MilestoneOut,
    MilestoneTemplateCreateRequest,
    MilestoneTemplateOut,
    MilestoneUpdateRequest,
)

router = APIRouter(tags=["Engagement"])


def _role_name(user: User) -> str | None:
    if user.role is None:
        return None
    return user.role.name.value if hasattr(user.role.name, "value") else str(user.role.name)


def _can_manage_student_progress(db: Session, actor: User, student_id: UUID) -> bool:
    if actor.id == student_id:
        return True

    role_name = _role_name(actor)
    if role_name == RoleType.SYSTEM_ADMINISTRATOR.value:
        return True

    if role_name != RoleType.EMPLOYER_MANAGER.value:
        return False

    linked_application = db.scalar(
        select(Application.id)
        .join(JobPost, JobPost.id == Application.job_post_id)
        .where(
            Application.applicant_id == student_id,
            JobPost.created_by_id == actor.id,
        )
    )
    return linked_application is not None


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
    if not _can_manage_student_progress(db, current_user, student_id):
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
    if not _can_manage_student_progress(db, current_user, student_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to update this student's milestones")

    milestone = db.scalar(
        select(StudentProgressMilestone).where(
            StudentProgressMilestone.id == milestone_id,
            StudentProgressMilestone.student_id == student_id,
        )
    )
    if not milestone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found")

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


@router.get("/students/{student_id}/milestones", response_model=list[MilestoneOut])
def list_student_milestones(
    student_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MilestoneOut]:
    if not _can_manage_student_progress(db, current_user, student_id):
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
