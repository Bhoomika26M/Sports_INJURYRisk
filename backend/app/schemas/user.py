from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum

class UserRoleEnum(str, Enum):
    ATHLETE = "athlete"
    COACH = "coach"
    PHYSIOTHERAPIST = "physiotherapist"
    SPORTS_SCIENTIST = "sports_scientist"
    ADMINISTRATOR = "administrator"

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    role: str = "athlete"
    auth_provider: Optional[str] = "local"
    bio: Optional[str] = None
    phone_number: Optional[str] = None
    organization: Optional[str] = None
    specialization: Optional[str] = None

class UserCreate(UserBase):
    password: str
    admin_code: Optional[str] = None

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    phone_number: Optional[str] = None
    organization: Optional[str] = None
    specialization: Optional[str] = None

class UserPasswordChange(BaseModel):
    current_password: str
    new_password: str

class UserRoleUpdate(BaseModel):
    role: str
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)
