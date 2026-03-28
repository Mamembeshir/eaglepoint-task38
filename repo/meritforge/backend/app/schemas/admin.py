from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RiskDictionaryCreateRequest(BaseModel):
    term: str = Field(min_length=1, max_length=255)
    category: str = Field(min_length=1, max_length=100)
    severity: str = Field(min_length=1, max_length=20)
    description: str | None = None
    replacement_suggestion: str | None = Field(default=None, max_length=255)
    is_regex: bool = False


class RiskDictionaryUpdateRequest(BaseModel):
    term: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    severity: str | None = Field(default=None, min_length=1, max_length=20)
    description: str | None = None
    replacement_suggestion: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    is_regex: bool | None = None


class RiskDictionaryOut(BaseModel):
    id: UUID
    term: str
    category: str
    severity: str
    description: str | None
    replacement_suggestion: str | None
    is_active: bool
    is_regex: bool
    match_count: int
    created_at: datetime


class CohortMemberOut(BaseModel):
    id: UUID
    email: str
    display_name: str | None


class CohortWithMembersOut(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str | None
    is_admin_defined: bool
    is_active: bool
    created_at: datetime
    members: list[CohortMemberOut]
