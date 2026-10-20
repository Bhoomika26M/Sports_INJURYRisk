from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# Administrators are created by an existing administrator (or bootstrapped from
# environment variables), never through public self-registration.
SelfRegisterRole = Literal["athlete", "coach", "physiotherapist", "sports_scientist"]
AnyRole = Literal["athlete", "coach", "physiotherapist", "sports_scientist", "administrator"]


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    role: SelfRegisterRole = "athlete"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


class UserProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)


class AdminUserUpdate(BaseModel):
    role: AnyRole | None = None
    is_active: bool | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class OAuthGoogleRequest(BaseModel):
    id_token: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
