from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.enums import ContentStatus, SegmentationType


class CanaryConfigInput(BaseModel):
    enabled: bool = False
    percentage: int | None = Field(default=None, ge=0, le=100)
    duration_minutes: int | None = Field(default=None, ge=1)
    segmentation_type: SegmentationType | None = None
    target_cohort_ids: list[UUID] | None = None


class SchedulePublishRequest(BaseModel):
    scheduled_publish_at: datetime
    scheduled_unpublish_at: datetime | None = None
    canary: CanaryConfigInput | None = None


class SchedulePublishOut(BaseModel):
    content_id: UUID
    status: ContentStatus
    scheduled_publish_at: datetime
    scheduled_unpublish_at: datetime | None
    canary_enabled: bool
    canary_percentage: int
    canary_duration_minutes: int
    canary_segmentation_type: SegmentationType


class TakedownRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class TakedownOut(BaseModel):
    content_id: UUID
    status: ContentStatus
    notice: str
    retracted_at: datetime


class CanaryVisibilityOut(BaseModel):
    content_id: UUID
    user_id: UUID
    visible: bool
    reason: str


class PublishingHistoryOut(BaseModel):
    id: UUID
    action: str
    actor_id: UUID | None
    reason: str | None
    before_state: dict | None
    after_state: dict | None
    created_at: datetime
