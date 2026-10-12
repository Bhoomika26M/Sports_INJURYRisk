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
    
    @field_validator('sport_type', 'position')
    @classmethod
    def sanitize_string(cls, v):
        if v is not None:
            if len(v) > 100:
                raise ValueError('Field too long (max 100 characters)')
            return v.strip()
        return v
    
    @field_validator('injury_history')
    @classmethod
    def sanitize_text(cls, v):
        if v is not None:
            if len(v) > 5000:
                raise ValueError('Field too long (max 5000 characters)')
            return v.strip()
        return v
    
    @field_validator('training_load')
    @classmethod
    def sanitize_load(cls, v):
        if v is not None:
            if len(v) > 500:
                raise ValueError('Field too long (max 500 characters)')
            return v.strip()
        return v
    
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
        if v > 300:  # Reasonable limits
            raise ValueError('Value exceeds reasonable limit')
        return v


class AthleteCreate(AthleteBase):
    athlete_id: str
    user_id: Optional[int] = None
    
    @field_validator('athlete_id')
    @classmethod
    def athlete_id_format(cls, v):
        if len(v) < 3 or len(v) > 50:
            raise ValueError('Athlete ID must be between 3 and 50 characters')
        return v.strip()


class AthleteUpdate(BaseModel):
    sport_type: Optional[str] = None
    position: Optional[str] = None
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    injury_history: Optional[str] = None
    training_load: Optional[str] = None
    
    @field_validator('sport_type', 'position')
    @classmethod
    def sanitize_string(cls, v):
        if v is not None:
            if len(v) > 100:
                raise ValueError('Field too long (max 100 characters)')
            return v.strip()
        return v
    
    @field_validator('injury_history')
    @classmethod
    def sanitize_text(cls, v):
        if v is not None:
            if len(v) > 5000:
                raise ValueError('Field too long (max 5000 characters)')
            return v.strip()
        return v
    
    @field_validator('training_load')
    @classmethod
    def sanitize_load(cls, v):
        if v is not None:
            if len(v) > 500:
                raise ValueError('Field too long (max 500 characters)')
            return v.strip()
        return v
    
    @field_validator('age')
    @classmethod
    def age_must_be_valid(cls, v):
        if v is not None:
            if v <= 0 or v >= 100:
                raise ValueError('Age must be between 1 and 99')
        return v
    
    @field_validator('height', 'weight')
    @classmethod
    def must_be_positive(cls, v):
        if v is not None:
            if v <= 0:
                raise ValueError('Value must be positive')
            if v > 300:
                raise ValueError('Value exceeds reasonable limit')
        return v


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
