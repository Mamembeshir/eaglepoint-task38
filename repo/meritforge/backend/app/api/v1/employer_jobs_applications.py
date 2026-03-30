from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.employer_jobs_shared import (
    can_manage_job_post,
    ensure_employer_or_admin,
    ensure_student,
    notify,
    to_application_out,
)
from app.core.audit import write_audit_log
from app.core.database import get_db
from app.core.enums import ApplicationStatus, AuditAction, ContentStatus
from app.dependencies.auth import get_current_user
from app.models.application import Application
from app.models.content import Content
from app.models.job_post import JobPost
from app.models.user import User
from app.schemas.employer_jobs import ApplicationOut, ApplicationStatusUpdateRequest, StudentApplicationCreateRequest

router = APIRouter(tags=["Employer Jobs"])


@router.get("/employer/job-posts/{job_post_id}/applications", response_model=list[ApplicationOut])
def list_job_applications(
    job_post_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ApplicationOut]:
    ensure_employer_or_admin(current_user)

    job_post = db.scalar(select(JobPost).where(JobPost.id == job_post_id))
    if not job_post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job post not found")
    if not can_manage_job_post(current_user, job_post):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view this job post")

    applications = db.scalars(select(Application).where(Application.job_post_id == job_post_id).order_by(Application.created_at.desc())).all()
    return [to_application_out(application) for application in applications]


@router.patch("/employer/applications/{application_id}/status", response_model=ApplicationOut)
def update_application_status(
    application_id: UUID,
    payload: ApplicationStatusUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplicationOut:
    ensure_employer_or_admin(current_user)

    application = db.scalar(select(Application).where(Application.id == application_id))
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    job_post = db.scalar(select(JobPost).where(JobPost.id == application.job_post_id))
    if not job_post or not can_manage_job_post(current_user, job_post):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to update this application")

    before = {
        "status": application.status.value if hasattr(application.status, "value") else str(application.status),
        "notes": application.notes,
    }
    application.status = payload.status
    application.notes = payload.notes
    application.reviewed_at = datetime.now(timezone.utc)
    application.status_changed_by_id = current_user.id

    notify(
        user_id=application.applicant_id,
        category="application_status",
        title="Application status updated",
        body=f"Your application status is now '{payload.status.value}'.",
        entity_type="application",
        entity_id=str(application.id),
        db=db,
    )

    write_audit_log(
        db,
        action=AuditAction.UPDATE,
        entity_type="application",
        entity_id=str(application.id),
        actor=current_user,
        request=request,
        before_data=before,
        after_data={"status": payload.status.value, "notes": payload.notes},
        description="Updated application status",
    )
    db.commit()

    return to_application_out(application)


@router.post("/student/job-posts/{job_post_id}/applications", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
def create_student_application(
    job_post_id: UUID,
    payload: StudentApplicationCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplicationOut:
    ensure_student(current_user)

    job_post = db.scalar(select(JobPost).where(JobPost.id == job_post_id))
    if not job_post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job post not found")
    if not job_post.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job post is not active")

    content = db.scalar(select(Content).where(Content.id == job_post.content_id))
    if not content or content.status != ContentStatus.PUBLISHED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job post is not open for applications")

    existing = db.scalar(
        select(Application).where(
            Application.job_post_id == job_post_id,
            Application.applicant_id == current_user.id,
            Application.status != ApplicationStatus.WITHDRAWN,
        )
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Active application already exists for this job post")

    if not payload.cover_letter or not payload.cover_letter.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Please add a brief cover letter before submitting your application.",
        )

    application = db.scalar(
        select(Application).where(
            Application.job_post_id == job_post_id,
            Application.applicant_id == current_user.id,
        )
    )
    if application:
        application.status = ApplicationStatus.SUBMITTED
        application.cover_letter = payload.cover_letter
        application.resume_url = payload.resume_url
        application.portfolio_url = payload.portfolio_url
        application.custom_fields = payload.custom_fields
        application.submitted_at = datetime.now(timezone.utc)
        application.notes = None
    else:
        application = Application(
            job_post_id=job_post_id,
            applicant_id=current_user.id,
            status=ApplicationStatus.SUBMITTED,
            cover_letter=payload.cover_letter,
            resume_url=payload.resume_url,
            portfolio_url=payload.portfolio_url,
            custom_fields=payload.custom_fields,
            submitted_at=datetime.now(timezone.utc),
        )
        db.add(application)
        db.flush()

    if job_post.created_by_id:
        notify(
            user_id=job_post.created_by_id,
            category="application_submitted",
            title="New application submitted",
            body=f"A student applied to job post {job_post.id}.",
            entity_type="application",
            entity_id=str(application.id),
            db=db,
        )

    write_audit_log(
        db,
        action=AuditAction.CREATE,
        entity_type="application",
        entity_id=str(application.id),
        actor=current_user,
        request=request,
        after_data={
            "job_post_id": str(job_post_id),
            "status": application.status.value,
            "submitted_at": application.submitted_at.isoformat() if application.submitted_at else None,
        },
        description="Student submitted job application",
    )
    db.commit()

    return to_application_out(application)


@router.get("/student/applications", response_model=list[ApplicationOut])
def list_my_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ApplicationOut]:
    rows = db.scalars(
        select(Application)
        .where(Application.applicant_id == current_user.id)
        .order_by(Application.created_at.desc())
    ).all()
    return [to_application_out(row) for row in rows]
