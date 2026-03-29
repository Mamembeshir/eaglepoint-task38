from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    display_name: str | None = Field(default=None, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserAuthOut(BaseModel):
    id: UUID
    email: EmailStr
    first_name: str | None
    last_name: str | None
    display_name: str | None
    role: str | None
    created_at: datetime


class AuthResponse(BaseModel):
    user: UserAuthOut
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime
    token_type: str = "bearer"


class LogoutResponse(BaseModel):
    message: str


class StepUpRequest(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class StepUpResponse(BaseModel):
    message: str
