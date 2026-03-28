from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.enums import ApplicationStatus


class JobPostCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    employer_name: str = Field(min_length=2, max_length=255)
    description: str | None = None
    location: str | None = Field(default=None, max_length=255)
    location_type: str | None = Field(default=None, max_length=50)
    department: str | None = Field(default=None, max_length=100)
    employment_type: str | None = Field(default=None, max_length=50)
    salary_min: Decimal | None = None
    salary_max: Decimal | None = None
    salary_currency: str | None = Field(default=None, max_length=3)
    requirements: str | None = None
    benefits: str | None = None
    application_deadline: date | None = None


class JobPostUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    employer_name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None
    location: str | None = Field(default=None, max_length=255)
    location_type: str | None = Field(default=None, max_length=50)
    department: str | None = Field(default=None, max_length=100)
    employment_type: str | None = Field(default=None, max_length=50)
    salary_min: Decimal | None = None
    salary_max: Decimal | None = None
    salary_currency: str | None = Field(default=None, max_length=3)
    requirements: str | None = None
    benefits: str | None = None
    application_deadline: date | None = None
    is_active: bool | None = None


class JobPostOut(BaseModel):
    id: UUID
    content_id: UUID
    title: str
    employer_name: str
    location: str | None
    employment_type: str | None
    application_deadline: date | None
    is_active: bool
    created_at: datetime


class ApplicationOut(BaseModel):
    id: UUID
    job_post_id: UUID
    applicant_id: UUID
    status: ApplicationStatus
    submitted_at: datetime | None
    reviewed_at: datetime | None
    created_at: datetime


class ApplicationStatusUpdateRequest(BaseModel):
    status: ApplicationStatus
    notes: str | None = None


class JobMilestoneTemplateCreateRequest(BaseModel):
    key: str = Field(min_length=2, max_length=100)
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None
    threshold_count: int = Field(default=1, ge=1)


class StudentMilestoneProgressCreateRequest(BaseModel):
    milestone_template_id: UUID
    milestone_name: str = Field(min_length=2, max_length=255)
    description: str | None = None
    progress_value: int = Field(default=0, ge=0)
    target_value: int = Field(default=1, ge=1)
    achievement_date: date | None = None
    metadata_json: dict | None = None


class VerifyMilestoneRequest(BaseModel):
    is_verified: bool
    note: str | None = None


class JobMilestoneOut(BaseModel):
    id: UUID
    student_id: UUID
    application_id: UUID | None
    milestone_name: str
    progress_value: int
    target_value: int
    is_verified: bool
    updated_at: datetime
