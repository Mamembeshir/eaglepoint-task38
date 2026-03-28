from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.enums import AnnotationVisibility, EventType


class TelemetryEventRequest(BaseModel):
    event_type: EventType
    content_id: UUID | None = None
    session_id: str | None = Field(default=None, max_length=100)
    resource_type: str | None = Field(default=None, max_length=50)
    resource_id: str | None = Field(default=None, max_length=100)
    event_data: dict | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    progress_percentage: int | None = Field(default=None, ge=0, le=100)


class TelemetryEventOut(BaseModel):
    id: UUID
    event_type: EventType
    user_id: UUID | None
    content_id: UUID | None
    created_at: datetime


class PlaybackProgressOut(BaseModel):
    content_id: UUID
    progress_seconds: int
    updated_at: datetime


class MilestoneTemplateCreateRequest(BaseModel):
    key: str = Field(min_length=2, max_length=100)
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None
    is_predefined: bool = True
    automation_event_type: EventType | None = None
    threshold_count: int = Field(default=1, ge=1)


class MilestoneTemplateOut(BaseModel):
    id: UUID
    key: str
    name: str
    description: str | None
    is_predefined: bool
    is_active: bool
    automation_event_type: EventType | None
    threshold_count: int
    created_at: datetime


class ManualMilestoneCreateRequest(BaseModel):
    milestone_template_id: UUID | None = None
    milestone_name: str = Field(min_length=2, max_length=255)
    milestone_type: str = Field(default="custom", max_length=100)
    description: str | None = None
    achievement_date: date | None = None
    metadata_json: dict | None = None
    progress_value: int = Field(default=0, ge=0)
    target_value: int = Field(default=1, ge=1)


class MilestoneUpdateRequest(BaseModel):
    client_updated_at: datetime
    milestone_name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None
    achievement_date: date | None = None
    metadata_json: dict | None = None
    progress_value: int | None = Field(default=None, ge=0)
    target_value: int | None = Field(default=None, ge=1)


class MilestoneOut(BaseModel):
    id: UUID
    student_id: UUID
    milestone_template_id: UUID | None
    milestone_type: str
    milestone_name: str
    is_custom: bool
    source: str
    progress_value: int
    target_value: int
    achievement_date: date | None
    updated_at: datetime
    version: int


class AnnotationCreateRequest(BaseModel):
    content_id: UUID
    visibility: AnnotationVisibility = AnnotationVisibility.PRIVATE
    cohort_id: UUID | None = None
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)
    highlighted_text: str | None = None
    annotation_text: str | None = None
    color: str | None = Field(default=None, max_length=20)
    tags: list[str] | None = None


class AnnotationUpdateRequest(BaseModel):
    client_updated_at: datetime
    visibility: AnnotationVisibility | None = None
    cohort_id: UUID | None = None
    annotation_text: str | None = None
    color: str | None = Field(default=None, max_length=20)
    tags: list[str] | None = None


class AnnotationOut(BaseModel):
    id: UUID
    content_id: UUID
    author_id: UUID
    visibility: AnnotationVisibility
    cohort_id: UUID | None
    start_offset: int
    end_offset: int
    highlighted_text: str | None
    annotation_text: str | None
    color: str | None
    tags: list[str] | None
    updated_at: datetime
    version: int
