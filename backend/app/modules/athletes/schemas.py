"""Athlete Pydantic schemas."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class AthleteBase(BaseModel):
    sport_type: str = Field(min_length=1, max_length=100)
    position: Optional[str] = Field(default=None, max_length=100)
    date_of_birth: date
    height_cm: Optional[float] = Field(default=None, ge=50, le=300)
    weight_kg: Optional[float] = Field(default=None, ge=20, le=200)
    dominant_side: Optional[str] = Field(default=None, pattern="^(left|right)$")


class AthleteCreate(AthleteBase):
    pass


class AthleteUpdate(BaseModel):
    sport_type: Optional[str] = Field(default=None, min_length=1, max_length=100)
    position: Optional[str] = Field(default=None, max_length=100)
    date_of_birth: Optional[date] = None
    height_cm: Optional[float] = Field(default=None, ge=50, le=300)
    weight_kg: Optional[float] = Field(default=None, ge=20, le=200)
    dominant_side: Optional[str] = Field(default=None, pattern="^(left|right)$")


class AthleteResponse(AthleteBase):
    id: str
    user_id: Optional[str] = None
    coach_id: Optional[str] = None
    full_name: Optional[str] = None
    age: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AthleteListResponse(BaseModel):
    items: list[AthleteResponse]
    total: int
    page: int
    page_size: int


class InjuryHistoryBase(BaseModel):
    injury_type: str = Field(min_length=1, max_length=255)
    body_part: str = Field(min_length=1, max_length=100)
    injury_date: date
    recovery_date: Optional[date] = None
    severity: Optional[str] = Field(default=None, pattern="^(minor|moderate|severe)$")
    notes: Optional[str] = None


class InjuryHistoryCreate(InjuryHistoryBase):
    pass


class InjuryHistoryResponse(InjuryHistoryBase):
    id: str
    athlete_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class InjuryHistoryListResponse(BaseModel):
    items: list[InjuryHistoryResponse]
    total: int
    page: int
    page_size: int


class TrainingLoadBase(BaseModel):
    entry_date: date
    session_type: Optional[str] = Field(default=None, max_length=100)
    duration_minutes: Optional[int] = Field(default=None, ge=1, le=1440)
    rpe: Optional[int] = Field(default=None, ge=1, le=10)
    notes: Optional[str] = None


class TrainingLoadCreate(TrainingLoadBase):
    pass


class TrainingLoadResponse(TrainingLoadBase):
    id: str
    athlete_id: str
    session_load: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TrainingLoadListResponse(BaseModel):
    items: list[TrainingLoadResponse]
    total: int
    page: int
    page_size: int