from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.core.enums import ContentStatus, ContentType


class ReviewerQueueItemOut(BaseModel):
    stage_id: UUID
    content_id: UUID
    title: str
    content_type: ContentType
    status: ContentStatus
    stage_name: str
    stage_order: int
    is_parallel: bool
    required_distinct_reviewers: int
    current_distinct_approvers: int
    latest_comment: str | None
    updated_at: datetime
