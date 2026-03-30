from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BookmarkUpsertRequest(BaseModel):
    content_id: UUID
    is_favorite: bool = False
    folder: str | None = Field(default=None, max_length=100)
    notes: str | None = None


class BookmarkOut(BaseModel):
    id: UUID
    content_id: UUID
    is_favorite: bool
    folder: str | None
    notes: str | None
    updated_at: datetime
