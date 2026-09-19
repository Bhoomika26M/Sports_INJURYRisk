"""Auth schemas — Pydantic request/response models for auth endpoints."""

from pydantic import BaseModel, EmailStr, Field

from app.modules.users.models import UserRole


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    role: UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    message: str
