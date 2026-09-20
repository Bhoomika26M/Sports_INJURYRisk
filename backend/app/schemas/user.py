from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class UserBase(BaseModel):
    email: str
    full_name: str
    role: str


class UserCreate(UserBase):
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
