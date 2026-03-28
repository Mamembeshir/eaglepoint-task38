from datetime import datetime
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, Field


class WebhookConfigCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    url: AnyHttpUrl
    secret: str | None = Field(default=None, max_length=255)
    events: list[str] = Field(min_length=1)
    headers: dict[str, str] | None = None
    retry_count: int = Field(default=3, ge=0, le=10)
    retry_delay_seconds: int = Field(default=60, ge=1, le=3600)
    timeout_seconds: int = Field(default=30, ge=1, le=300)


class WebhookConfigOut(BaseModel):
    id: UUID
    name: str
    url: str
    events: list[str]
    is_active: bool
    retry_count: int
    retry_delay_seconds: int
    timeout_seconds: int
    created_by_id: UUID | None
    created_at: datetime


class WebhookDispatchRequest(BaseModel):
    event_name: str = Field(min_length=1, max_length=100)
    payload: dict


class WebhookDispatchOut(BaseModel):
    queued_deliveries: int
    delivery_ids: list[UUID]


class WebhookDeliveryOut(BaseModel):
    id: UUID
    webhook_config_id: UUID
    event_name: str
    status: str
    attempts: int
    response_status: int | None
    last_error: str | None
    queued_at: datetime
    delivered_at: datetime | None
    created_at: datetime


class WebhookRetryOut(BaseModel):
    original_delivery_id: UUID
    retried_delivery_id: UUID
    status: str
