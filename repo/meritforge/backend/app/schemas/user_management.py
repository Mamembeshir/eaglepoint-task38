from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class UserProfileUpdateRequest(BaseModel):
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    display_name: str | None = Field(default=None, max_length=100)
    bio: str | None = None
    avatar_url: str | None = Field(default=None, max_length=500)
    phone_number: str | None = Field(default=None, max_length=30)
    consent_contact_info_visible: bool | None = None
    consent_photo_visible: bool | None = None
    consent_analytics: bool | None = None
    consent_data_portability: bool | None = None


class UserProfileOut(BaseModel):
    id: UUID
    email: str | None
    first_name: str | None
    last_name: str | None
    display_name: str | None
    bio: str | None
    avatar_url: str | None
    phone_number: str | None
    consent_contact_info_visible: bool
    consent_photo_visible: bool
    consent_analytics: bool
    consent_data_portability: bool
    created_at: datetime
    updated_at: datetime


class UserDataImportPayload(BaseModel):
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    display_name: str | None = Field(default=None, max_length=100)
    bio: str | None = None
    avatar_url: str | None = Field(default=None, max_length=500)
    phone_number: str | None = Field(default=None, max_length=30)
    consent_contact_info_visible: bool | None = None
    consent_photo_visible: bool | None = None
    consent_analytics: bool | None = None
    consent_data_portability: bool | None = None


class ImportUserDataRequest(BaseModel):
    user: UserDataImportPayload
    source: str | None = Field(default="local_fallback", max_length=100)


class CohortCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    slug: str = Field(min_length=2, max_length=100)
    description: str | None = None
    is_admin_defined: bool = False


class CohortOut(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str | None
    is_active: bool
    is_admin_defined: bool
    created_by_id: UUID | None
    created_at: datetime


class AssignUserCohortRequest(BaseModel):
    user_id: UUID


class ExportUserDataOut(BaseModel):
    exported_at: datetime
    user: dict
    cohorts: list[dict]


class MarkDeletionRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class DeletionStatusOut(BaseModel):
    user_id: UUID
    is_marked_for_deletion: bool
    deletion_requested_at: datetime | None
    scheduled_deletion_at: datetime | None
    reason: str | None


class ProcessDeletionResult(BaseModel):
    deleted_count: int
    deleted_user_ids: list[UUID]
