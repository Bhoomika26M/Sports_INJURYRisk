from pydantic import BaseModel
from typing import Optional


class UserRegister(BaseModel):
    email: str
    password: str
    full_name: str
    role: str  # athlete, coach, physiotherapist, sports_scientist, administrator


class UserLogin(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None
