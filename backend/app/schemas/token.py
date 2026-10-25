from typing import Optional
from pydantic import BaseModel, EmailStr
from app.schemas.user import UserResponse

class Token(BaseModel):
    access_token: str
    token_type: str
    user: Optional[UserResponse] = None

class TokenPayload(BaseModel):
    sub: str | None = None
    role: str | None = None

class OAuthLoginRequest(BaseModel):
    provider: str
    email: EmailStr
    full_name: Optional[str] = None
    token: Optional[str] = None
    role: Optional[str] = "athlete"

class GoogleOAuthRequest(BaseModel):
    credential: str
    role: Optional[str] = "athlete"
    admin_code: Optional[str] = None
