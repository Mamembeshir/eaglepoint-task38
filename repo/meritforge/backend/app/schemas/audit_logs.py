from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: UUID
    action: str
    entity_type: str
    entity_id: str | None
    user_id: UUID | None
    user_email: str | None
    ip_address: str | None
    before_data: dict | list | str | int | float | bool | None
    after_data: dict | list | str | int | float | bool | None
    changes: dict | list | str | int | float | bool | None
    description: str | None
    request_url: str | None
    request_method: str | None
    created_at: datetime


class AuditSearchResponse(BaseModel):
    total: int
    items: list[AuditLogOut]
