from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.enums import ContentType, ContentStatus


class ContentSubmissionRequest(BaseModel):
    content_type: ContentType
    title: str = Field(min_length=3, max_length=255)
    body: str | None = None
    media_url: str | None = Field(default=None, max_length=500)
    metadata: dict | None = None


class ContentRevisionRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    body: str | None = None
    media_url: str | None = Field(default=None, max_length=500)
    metadata: dict | None = None
    change_summary: str = Field(default="Revision submission", min_length=3, max_length=500)


class TriggeredWordOut(BaseModel):
    term: str
    severity: str
    weight: int
    match_count: int


class ContentSubmissionOut(BaseModel):
    content_id: UUID
    version_id: UUID
    content_type: ContentType
    status: ContentStatus
    risk_score: int
    risk_grade: str
    blocked_until_final_approval: bool
    required_distinct_reviewers: int
    triggering_words: list[TriggeredWordOut]
    created_at: datetime


class ContentRevisionOut(BaseModel):
    content_id: UUID
    version_id: UUID
    version_number: int
    status: ContentStatus
    stages_created: int
    created_at: datetime


class ReviewCommentOut(BaseModel):
    stage_name: str
    decision: str
    reviewer_id: UUID | None
    comments: str | None
    created_at: datetime


class ReviewStageSummaryOut(BaseModel):
    stage_name: str
    stage_order: int
    is_required: bool
    is_parallel: bool
    is_completed: bool


class ContentSubmissionListItemOut(BaseModel):
    content_id: UUID
    title: str
    content_type: ContentType
    status: ContentStatus
    risk_score: int | None
    risk_grade: str | None
    workflow_stage_count: int
    stages: list[ReviewStageSummaryOut]
    review_comments: list[ReviewCommentOut]
    created_at: datetime


class ContentCatalogItemOut(BaseModel):
    id: UUID
    title: str
    content_type: ContentType
    status: ContentStatus
    media_url: str | None
    metadata: dict | None
    summary: str | None
    retracted_at: datetime | None = None
    retraction_notice: str | None = None
    job_post_id: UUID | None = None
