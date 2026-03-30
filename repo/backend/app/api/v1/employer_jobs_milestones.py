from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.employer_jobs_shared import can_manage_job_post, ensure_employer_or_admin, notify
from app.core.audit import write_audit_log
from app.core.database import get_db
from app.core.enums import AuditAction
from app.dependencies.auth import get_current_user
from app.models.application import Application
from app.models.job_post import JobPost
from app.models.student_milestone_template import StudentMilestoneTemplate
from app.models.student_progress_milestone import StudentProgressMilestone
from app.models.user import User
from app.schemas.employer_jobs import (
    JobMilestoneOut,
    JobMilestoneTemplateCreateRequest,
    StudentMilestoneProgressCreateRequest,
    VerifyMilestoneRequest,
)

router = APIRouter(tags=["Employer Jobs"])


@router.post("/employer/job-posts/{job_post_id}/milestone-templates", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_job_custom_milestone_template(
    job_post_id: UUID,
    payload: JobMilestoneTemplateCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    ensure_employer_or_admin(current_user)

    job_post = db.scalar(select(JobPost).where(JobPost.id == job_post_id))
    if not job_post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job post not found")
    if not can_manage_job_post(current_user, job_post):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to manage this job post")

    template = StudentMilestoneTemplate(
        key=payload.key,
        name=payload.name,
        description=payload.description,
        is_predefined=False,
        threshold_count=payload.threshold_count,
        job_post_id=job_post_id,
        created_by_id=current_user.id,
    )
    db.add(template)
    db.flush()

    write_audit_log(
        db,
        action=AuditAction.CREATE,
        entity_type="job_milestone_template",
        entity_id=str(template.id),
        actor=current_user,
        request=request,
        after_data={"job_post_id": str(job_post_id), "key": payload.key, "name": payload.name},
        description="Created custom milestone template for job post",
    )
    db.commit()

    return {"id": str(template.id), "job_post_id": str(job_post_id), "key": template.key, "name": template.name}


@router.post("/student/applications/{application_id}/milestones", response_model=dict, status_code=status.HTTP_201_CREATED)
def student_report_milestone_progress(
    application_id: UUID,
    payload: StudentMilestoneProgressCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    application = db.scalar(select(Application).where(Application.id == application_id))
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    if application.applicant_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only applicant can self-report this milestone")

    template = db.scalar(select(StudentMilestoneTemplate).where(StudentMilestoneTemplate.id == payload.milestone_template_id, StudentMilestoneTemplate.is_active.is_(True)))
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone template not found")
    if template.job_post_id and template.job_post_id != application.job_post_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Milestone template does not belong to this job post")

    milestone = StudentProgressMilestone(
        student_id=current_user.id,
        job_post_id=application.job_post_id,
        application_id=application.id,
        milestone_template_id=template.id,
        milestone_type="job_progress",
        milestone_name=payload.milestone_name,
        description=payload.description,
        achievement_date=payload.achievement_date,
        metadata_json=payload.metadata_json,
        is_custom=not template.is_predefined,
        source="manual",
        progress_value=payload.progress_value,
        target_value=payload.target_value,
        version=1,
    )
    db.add(milestone)

    job_post = db.scalar(select(JobPost).where(JobPost.id == application.job_post_id))
    if job_post and job_post.created_by_id:
        notify(
            user_id=job_post.created_by_id,
            category="milestone_reported",
            title="Student milestone reported",
            body=f"Student reported milestone '{payload.milestone_name}' for application {application.id}.",
            entity_type="student_progress_milestone",
            entity_id=str(milestone.id),
            db=db,
        )

    write_audit_log(
        db,
        action=AuditAction.CREATE,
        entity_type="student_progress_milestone",
        entity_id=str(milestone.id),
        actor=current_user,
        request=request,
        after_data={
            "application_id": str(application.id),
            "job_post_id": str(application.job_post_id),
            "milestone_template_id": str(template.id),
            "progress_value": payload.progress_value,
            "target_value": payload.target_value,
        },
        description="Student self-reported milestone progress",
    )
    db.commit()

    return {"id": str(milestone.id), "application_id": str(application.id), "verified": milestone.is_verified}


@router.patch("/employer/milestones/{milestone_id}/verify", response_model=dict)
def verify_student_milestone(
    milestone_id: UUID,
    payload: VerifyMilestoneRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    ensure_employer_or_admin(current_user)

    milestone = db.scalar(select(StudentProgressMilestone).where(StudentProgressMilestone.id == milestone_id))
    if not milestone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found")
    if not milestone.job_post_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Milestone is not job-related")

    job_post = db.scalar(select(JobPost).where(JobPost.id == milestone.job_post_id))
    if not job_post or not can_manage_job_post(current_user, job_post):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to verify this milestone")

    before = {
        "is_verified": milestone.is_verified,
        "verified_by_id": str(milestone.verified_by_id) if milestone.verified_by_id else None,
        "verified_at": milestone.verified_at.isoformat() if milestone.verified_at else None,
    }

    milestone.is_verified = payload.is_verified
    milestone.verified_by_id = current_user.id if payload.is_verified else None
    milestone.verified_at = datetime.now(timezone.utc) if payload.is_verified else None
    milestone.version += 1

    notify(
        user_id=milestone.student_id,
        category="milestone_verification",
        title="Milestone verification updated",
        body=f"Your milestone '{milestone.milestone_name}' verification is now {payload.is_verified}.",
        entity_type="student_progress_milestone",
        entity_id=str(milestone.id),
        db=db,
    )

    write_audit_log(
        db,
        action=AuditAction.UPDATE,
        entity_type="student_progress_milestone_verification",
        entity_id=str(milestone.id),
        actor=current_user,
        request=request,
        before_data=before,
        after_data={
            "is_verified": milestone.is_verified,
            "verified_by_id": str(milestone.verified_by_id) if milestone.verified_by_id else None,
            "verified_at": milestone.verified_at.isoformat() if milestone.verified_at else None,
            "note": payload.note,
        },
        description="Employer/admin verified student milestone",
    )
    db.commit()

    return {"id": str(milestone.id), "is_verified": milestone.is_verified, "verified_at": milestone.verified_at}


@router.get("/employer/job-posts/{job_post_id}/milestones", response_model=list[JobMilestoneOut])
def list_job_post_milestones(
    job_post_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[JobMilestoneOut]:
    ensure_employer_or_admin(current_user)

    job_post = db.scalar(select(JobPost).where(JobPost.id == job_post_id))
    if not job_post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job post not found")
    if not can_manage_job_post(current_user, job_post):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view this job post")

    rows = db.scalars(
        select(StudentProgressMilestone)
        .where(StudentProgressMilestone.job_post_id == job_post_id)
        .order_by(StudentProgressMilestone.updated_at.desc())
    ).all()

    return [
        JobMilestoneOut(
            id=row.id,
            student_id=row.student_id,
            application_id=row.application_id,
            milestone_name=row.milestone_name,
            progress_value=row.progress_value,
            target_value=row.target_value,
            is_verified=row.is_verified,
            updated_at=row.updated_at,
        )
        for row in rows
    ]
