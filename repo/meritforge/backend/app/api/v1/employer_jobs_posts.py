from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.employer_jobs_shared import can_manage_job_post, ensure_employer_or_admin, slugify_title, to_job_post_out
from app.core.audit import write_audit_log
from app.core.database import get_db
from app.core.enums import AuditAction, ContentStatus, ContentType
from app.dependencies.auth import get_current_user
from app.models.content import Content
from app.models.job_post import JobPost
from app.models.user import User
from app.schemas.employer_jobs import JobPostCreateRequest, JobPostOut, JobPostUpdateRequest

router = APIRouter(tags=["Employer Jobs"])


@router.post("/employer/job-posts", response_model=JobPostOut, status_code=status.HTTP_201_CREATED)
def create_job_post(
    payload: JobPostCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobPostOut:
    ensure_employer_or_admin(current_user)

    content = Content(
        title=payload.title,
        slug=slugify_title(payload.title, db),
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

    return to_job_post_out(job_post, content)


@router.get("/employer/job-posts", response_model=list[JobPostOut])
def list_my_job_posts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[JobPostOut]:
    ensure_employer_or_admin(current_user)

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
        output.append(to_job_post_out(post, content))
    return output


@router.patch("/employer/job-posts/{job_post_id}", response_model=JobPostOut)
def update_job_post(
    job_post_id: UUID,
    payload: JobPostUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobPostOut:
    ensure_employer_or_admin(current_user)

    job_post = db.scalar(select(JobPost).where(JobPost.id == job_post_id))
    if not job_post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job post not found")
    if not can_manage_job_post(current_user, job_post):
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

    return to_job_post_out(job_post, content)
