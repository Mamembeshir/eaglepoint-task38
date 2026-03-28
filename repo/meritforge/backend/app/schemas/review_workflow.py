from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.enums import ContentStatus, ReviewDecisionType


class TemplateStageCreateRequest(BaseModel):
    stage_name: str = Field(min_length=2, max_length=100)
    stage_order: int = Field(ge=1)
    description: str | None = None
    is_required: bool = True
    is_parallel: bool = False


class TemplateStageOut(BaseModel):
    id: UUID
    stage_name: str
    stage_order: int
    description: str | None
    is_required: bool
    is_parallel: bool
    is_active: bool
    created_by_id: UUID | None
    created_at: datetime


class InitializeWorkflowResponse(BaseModel):
    content_id: UUID
    stages_created: int
    status: ContentStatus


class ReviewDecisionRequest(BaseModel):
    decision: ReviewDecisionType
    comments: str | None = None


class ReviewDecisionOut(BaseModel):
    stage_id: UUID
    decision: ReviewDecisionType
    content_status: ContentStatus
    stage_completed: bool
    required_distinct_reviewers: int
    distinct_approvers: int
    created_at: datetime
