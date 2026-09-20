from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional


class AthleteBase(BaseModel):
    sport_type: str
    position: Optional[str] = None
    age: int
    height: float
    weight: float
    injury_history: Optional[str] = None
    training_load: Optional[str] = None
    
    @field_validator('age')
    @classmethod
    def age_must_be_valid(cls, v):
        if v <= 0 or v >= 100:
            raise ValueError('Age must be between 1 and 99')
        return v
    
    @field_validator('height', 'weight')
    @classmethod
    def must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Value must be positive')
        return v


class AthleteCreate(AthleteBase):
    athlete_id: str
    user_id: Optional[int] = None


class AthleteUpdate(BaseModel):
    sport_type: Optional[str] = None
    position: Optional[str] = None
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    injury_history: Optional[str] = None
    training_load: Optional[str] = None


class AthleteResponse(BaseModel):
    id: int
    athlete_id: str
    user_id: Optional[int]
    sport_type: str
    position: Optional[str]
    age: int
    height: float
    weight: float
    injury_history: Optional[str]
    training_load: Optional[str]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
