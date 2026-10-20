from pydantic import BaseModel, field_validator
from typing import Optional

from app.core.config import settings


class UserRegister(BaseModel):
    email: str
    password: str
    full_name: str
    role: str  # athlete, coach, physiotherapist, sports_scientist, administrator
    # Optional athlete-specific fields
    sport_type: Optional[str] = None
    position: Optional[str] = None
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None

    @field_validator('password')
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

    @field_validator('email')
    @classmethod
    def email_format(cls, v):
        if '@' not in v or '.' not in v.split('@')[-1]:
            raise ValueError('Invalid email format')
        return v


class UserLogin(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


class PasswordResetRequest(BaseModel):
    email: str


def _validate_otp(v: str) -> str:
    """OTPs are always handled as strings so leading zeros are preserved."""
    v = (v or "").strip()
    if not v.isdigit() or len(v) != settings.OTP_LENGTH:
        raise ValueError(f"Verification code must be {settings.OTP_LENGTH} digits")
    return v


def _validate_new_password(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters long")
    return v


class ResetPasswordOTP(BaseModel):
    """Verify a recovery OTP and set a new password."""

    email: str
    otp: str
    new_password: str

    @field_validator("otp")
    @classmethod
    def otp_format(cls, v):
        return _validate_otp(v)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v):
        return _validate_new_password(v)


class ChangePasswordOTP(BaseModel):
    """Verify identity (current password + emailed OTP) and set a new password."""

    otp: str
    current_password: str
    new_password: str

    @field_validator("otp")
    @classmethod
    def otp_format(cls, v):
        return _validate_otp(v)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v):
        return _validate_new_password(v)


class GoogleAuthorizeUrlResponse(BaseModel):
    """Authorization URL the browser should be sent to."""

    authorization_url: str
    state: str


class GoogleCallbackRequest(BaseModel):
    """Authorization code returned to the frontend by Google."""

    code: str
    state: str
