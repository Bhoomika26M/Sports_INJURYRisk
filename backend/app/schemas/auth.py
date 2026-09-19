"""
Pydantic schemas for authentication endpoints.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator, model_validator

from app.models.enums import UserRole


# ---------------------------------------------------------------------------
# Registration / login request bodies
# ---------------------------------------------------------------------------
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone_number: str | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("full_name")
    @classmethod
    def full_name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("full_name must not be blank")
        return v.strip()


class UserLogin(BaseModel):
    email: EmailStr
    password: str


# ---------------------------------------------------------------------------
# Token response
# ---------------------------------------------------------------------------
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    role: str
    exp: int
    type: str


# ---------------------------------------------------------------------------
# User read / update schemas
# ---------------------------------------------------------------------------
class UserRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    phone_number: str | None
    is_active: bool
    is_verified: bool
    google_id: str | None = None
    avatar_url: str | None = None
    is_oauth_user: bool = False
    created_at: datetime


class UserUpdate(BaseModel):
    full_name: str | None = None
    phone_number: str | None = None
    password: str | None = None

    @field_validator("password", mode="before")
    @classmethod
    def password_strength(cls, v: str | None) -> str | None:
        if v is not None and len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


# ---------------------------------------------------------------------------
# Admin-only user creation
# ---------------------------------------------------------------------------
class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole
    phone_number: str | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v
