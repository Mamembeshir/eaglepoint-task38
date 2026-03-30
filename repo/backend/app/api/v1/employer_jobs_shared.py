from uuid import UUID
import re

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import RoleType
from app.models.application import Application
from app.models.content import Content
from app.models.in_app_notification import InAppNotification
from app.models.job_post import JobPost
from app.models.user import User
from app.schemas.employer_jobs import ApplicationOut, JobPostOut


def role_name(user: User) -> str | None:
    if user.role is None:
        return None
    return user.role.name.value if hasattr(user.role.name, "value") else str(user.role.name)


def ensure_employer_or_admin(user: User) -> None:
    if role_name(user) not in {RoleType.EMPLOYER_MANAGER.value, RoleType.SYSTEM_ADMINISTRATOR.value}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Employer manager or admin role required")


def ensure_student(user: User) -> None:
    if role_name(user) != RoleType.STUDENT.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student role required")


def slugify_title(title: str, db: Session) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "job"
    slug = base
    count = 2
    while db.scalar(select(Content).where(Content.slug == slug)):
        slug = f"{base}-{count}"
        count += 1
    return slug


def can_manage_job_post(user: User, job_post: JobPost) -> bool:
    if role_name(user) == RoleType.SYSTEM_ADMINISTRATOR.value:
        return True
    return job_post.created_by_id == user.id


def notify(user_id: UUID, category: str, title: str, body: str, entity_type: str, entity_id: str, db: Session) -> None:
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


def to_job_post_out(job_post: JobPost, content: Content) -> JobPostOut:
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


def to_application_out(application: Application) -> ApplicationOut:
    return ApplicationOut(
        id=application.id,
        job_post_id=application.job_post_id,
        applicant_id=application.applicant_id,
        status=application.status,
        submitted_at=application.submitted_at,
        reviewed_at=application.reviewed_at,
        created_at=application.created_at,
    )
