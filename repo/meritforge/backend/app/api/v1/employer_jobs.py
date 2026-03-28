from datetime import datetime, timezone
from uuid import UUID
import re

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.database import get_db
from app.core.enums import ApplicationStatus, AuditAction, ContentStatus, ContentType, RoleType
from app.dependencies.auth import get_current_user
from app.models.application import Application
from app.models.content import Content
from app.models.in_app_notification import InAppNotification
from app.models.job_post import JobPost
from app.models.student_milestone_template import StudentMilestoneTemplate
from app.models.student_progress_milestone import StudentProgressMilestone
from app.models.user import User
from app.schemas.employer_jobs import (
    ApplicationOut,
    ApplicationStatusUpdateRequest,
    JobMilestoneOut,
    JobMilestoneTemplateCreateRequest,
    JobPostCreateRequest,
    JobPostOut,
    JobPostUpdateRequest,
    StudentMilestoneProgressCreateRequest,
    VerifyMilestoneRequest,
)

router = APIRouter(tags=["Employer Jobs"])


def _role_name(user: User) -> str | None:
    if user.role is None:
        return None
    return user.role.name.value if hasattr(user.role.name, "value") else str(user.role.name)


def _is_employer_or_admin(user: User) -> bool:
    return _role_name(user) in {RoleType.EMPLOYER_MANAGER.value, RoleType.SYSTEM_ADMINISTRATOR.value}


def _ensure_employer_or_admin(user: User) -> None:
    if not _is_employer_or_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Employer manager or admin role required")


def _slugify(title: str, db: Session) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "job"
    slug = base
    count = 2
    while db.scalar(select(Content).where(Content.slug == slug)):
        slug = f"{base}-{count}"
        count += 1
    return slug


def _can_manage_job_post(user: User, job_post: JobPost) -> bool:
    if _role_name(user) == RoleType.SYSTEM_ADMINISTRATOR.value:
        return True
    return job_post.created_by_id == user.id


def _notify(user_id: UUID, category: str, title: str, body: str, entity_type: str, entity_id: str, db: Session) -> None:
    db.add(
        InAppNotification(
            user_id=user_id,
            category=category,
            title=title,
            body=body,
            related_entity_type=entity_type,
            related_entity_id=entity_id,
        )
    )


@router.post("/employer/job-posts", response_model=JobPostOut, status_code=status.HTTP_201_CREATED)
def create_job_post(
    payload: JobPostCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobPostOut:
    _ensure_employer_or_admin(current_user)

    content = Content(
        title=payload.title,
        slug=_slugify(payload.title, db),
        content_type=ContentType.JOB_ANNOUNCEMENT,
        status=ContentStatus.DRAFT,
        author_id=current_user.id,
    )
    db.add(content)
    db.flush()

    job_post = JobPost(
        content_id=content.id,
        employer_name=payload.employer_name,
        created_by_id=current_user.id,
        location=payload.location,
        location_type=payload.location_type,
        department=payload.department,
        employment_type=payload.employment_type,
        salary_min=payload.salary_min,
        salary_max=payload.salary_max,
        salary_currency=payload.salary_currency,
        requirements=payload.requirements,
        benefits=payload.benefits,
        application_deadline=payload.application_deadline,
    )
    db.add(job_post)

    write_audit_log(
        db,
        action=AuditAction.CREATE,
        entity_type="job_post",
        entity_id=str(job_post.id),
        actor=current_user,
        request=request,
        after_data={
            "content_id": str(content.id),
            "title": content.title,
            "employer_name": payload.employer_name,
        },
        description="Created job post",
    )
    db.commit()
    db.refresh(job_post)
    db.refresh(content)

    return JobPostOut(
        id=job_post.id,
        content_id=job_post.content_id,
        title=content.title,
        employer_name=job_post.employer_name,
        location=job_post.location,
        employment_type=job_post.employment_type,
        application_deadline=job_post.application_deadline,
        is_active=job_post.is_active,
        created_at=job_post.created_at,
    )


@router.get("/employer/job-posts", response_model=list[JobPostOut])
def list_my_job_posts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[JobPostOut]:
    _ensure_employer_or_admin(current_user)

    posts = db.scalars(
        select(JobPost)
        .where(JobPost.created_by_id == current_user.id)
        .order_by(JobPost.created_at.desc())
    ).all()

    output: list[JobPostOut] = []
    for post in posts:
        content = db.scalar(select(Content).where(Content.id == post.content_id))
        if not content:
            continue
        output.append(
            JobPostOut(
                id=post.id,
                content_id=post.content_id,
                title=content.title,
                employer_name=post.employer_name,
                location=post.location,
                employment_type=post.employment_type,
                application_deadline=post.application_deadline,
                is_active=post.is_active,
                created_at=post.created_at,
            )
        )
    return output


@router.patch("/employer/job-posts/{job_post_id}", response_model=JobPostOut)
def update_job_post(
    job_post_id: UUID,
    payload: JobPostUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobPostOut:
    _ensure_employer_or_admin(current_user)

    job_post = db.scalar(select(JobPost).where(JobPost.id == job_post_id))
    if not job_post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job post not found")
    if not _can_manage_job_post(current_user, job_post):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to manage this job post")

    content = db.scalar(select(Content).where(Content.id == job_post.content_id))
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Related content not found")

    before = {
        "title": content.title,
        "employer_name": job_post.employer_name,
        "is_active": job_post.is_active,
    }

    updates = payload.model_dump(exclude_unset=True)
    if "title" in updates:
        content.title = updates.pop("title")
    for key, value in updates.items():
        setattr(job_post, key, value)

    after = {
        "title": content.title,
        "employer_name": job_post.employer_name,
        "is_active": job_post.is_active,
    }

    write_audit_log(
        db,
        action=AuditAction.UPDATE,
        entity_type="job_post",
        entity_id=str(job_post.id),
        actor=current_user,
        request=request,
        before_data=before,
        after_data=after,
        changes=updates,
        description="Updated job post",
    )
    db.commit()

    return JobPostOut(
        id=job_post.id,
        content_id=job_post.content_id,
        title=content.title,
        employer_name=job_post.employer_name,
        location=job_post.location,
        employment_type=job_post.employment_type,
        application_deadline=job_post.application_deadline,
        is_active=job_post.is_active,
        created_at=job_post.created_at,
    )


@router.get("/employer/job-posts/{job_post_id}/applications", response_model=list[ApplicationOut])
def list_job_applications(
    job_post_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ApplicationOut]:
    _ensure_employer_or_admin(current_user)

    job_post = db.scalar(select(JobPost).where(JobPost.id == job_post_id))
    if not job_post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job post not found")
    if not _can_manage_job_post(current_user, job_post):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view this job post")

    applications = db.scalars(select(Application).where(Application.job_post_id == job_post_id).order_by(Application.created_at.desc())).all()
    return [
        ApplicationOut(
            id=a.id,
            job_post_id=a.job_post_id,
            applicant_id=a.applicant_id,
            status=a.status,
            submitted_at=a.submitted_at,
            reviewed_at=a.reviewed_at,
            created_at=a.created_at,
        )
        for a in applications
    ]


@router.patch("/employer/applications/{application_id}/status", response_model=ApplicationOut)
def update_application_status(
    application_id: UUID,
    payload: ApplicationStatusUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplicationOut:
    _ensure_employer_or_admin(current_user)

    application = db.scalar(select(Application).where(Application.id == application_id))
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    job_post = db.scalar(select(JobPost).where(JobPost.id == application.job_post_id))
    if not job_post or not _can_manage_job_post(current_user, job_post):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to update this application")

    before = {"status": application.status.value if hasattr(application.status, "value") else str(application.status), "notes": application.notes}
    application.status = payload.status
    application.notes = payload.notes
    application.reviewed_at = datetime.now(timezone.utc)
    application.status_changed_by_id = current_user.id

    _notify(
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

    return ApplicationOut(
        id=application.id,
        job_post_id=application.job_post_id,
        applicant_id=application.applicant_id,
        status=application.status,
        submitted_at=application.submitted_at,
        reviewed_at=application.reviewed_at,
        created_at=application.created_at,
    )


@router.post("/employer/job-posts/{job_post_id}/milestone-templates", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_job_custom_milestone_template(
    job_post_id: UUID,
    payload: JobMilestoneTemplateCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    _ensure_employer_or_admin(current_user)

    job_post = db.scalar(select(JobPost).where(JobPost.id == job_post_id))
    if not job_post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job post not found")
    if not _can_manage_job_post(current_user, job_post):
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
        _notify(
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
    _ensure_employer_or_admin(current_user)

    milestone = db.scalar(select(StudentProgressMilestone).where(StudentProgressMilestone.id == milestone_id))
    if not milestone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found")
    if not milestone.job_post_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Milestone is not job-related")

    job_post = db.scalar(select(JobPost).where(JobPost.id == milestone.job_post_id))
    if not job_post or not _can_manage_job_post(current_user, job_post):
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

    _notify(
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
    _ensure_employer_or_admin(current_user)

    job_post = db.scalar(select(JobPost).where(JobPost.id == job_post_id))
    if not job_post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job post not found")
    if not _can_manage_job_post(current_user, job_post):
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
