from pydantic import BaseModel
from typing import Optional

# User Schemas
class UserBase(BaseModel):
    email: str
    role: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    class Config:
        from_attributes = True

# Athlete Schemas
class AthleteProfileBase(BaseModel):
    sport_type: str
    position: str
    age: int
    height: float
    weight: float
    injury_history: Optional[str] = None
    training_load: Optional[str] = None

class AthleteProfileCreate(AthleteProfileBase):
    pass

class AthleteProfileResponse(AthleteProfileBase):
    id: int
    user_id: int
    class Config:
        from_attributes = True

# Auth
class Token(BaseModel):
    access_token: str
    token_type: str
