"""Athlete schemas — Pydantic request/response models for athlete endpoints."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# --- Athlete ---

class AthleteCreate(BaseModel):
    user_id: Optional[str] = None
    coach_id: Optional[str] = None
    sport_type: str = Field(min_length=1, max_length=100)
    position: Optional[str] = Field(None, max_length=100)
    date_of_birth: date
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    dominant_side: Optional[str] = Field(None, pattern=r"^(left|right)$")


class AthleteUpdate(BaseModel):
    sport_type: Optional[str] = Field(None, min_length=1, max_length=100)
    position: Optional[str] = Field(None, max_length=100)
    date_of_birth: Optional[date] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    dominant_side: Optional[str] = Field(None, pattern=r"^(left|right)$")
    coach_id: Optional[str] = None


class AthleteResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    coach_id: Optional[str] = None
    full_name: Optional[str] = None
    sport_type: str
    position: Optional[str] = None
    date_of_birth: date
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    dominant_side: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AthleteListResponse(BaseModel):
    items: list[AthleteResponse]
    total: int
    page: int
    page_size: int


# --- Injury History ---

class InjuryHistoryCreate(BaseModel):
    injury_type: str = Field(min_length=1, max_length=255)
    body_part: str = Field(min_length=1, max_length=100)
    injury_date: date
    recovery_date: Optional[date] = None
    severity: Optional[str] = Field(None, pattern=r"^(minor|moderate|severe)$")
    notes: Optional[str] = None


class InjuryHistoryResponse(BaseModel):
    id: str
    athlete_id: str
    injury_type: str
    body_part: str
    injury_date: date
    recovery_date: Optional[date] = None
    severity: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class InjuryHistoryListResponse(BaseModel):
    items: list[InjuryHistoryResponse]
    total: int
    page: int
    page_size: int


# --- Training Load ---

class TrainingLoadCreate(BaseModel):
    entry_date: date
    session_type: Optional[str] = Field(None, max_length=100)
    duration_minutes: Optional[int] = Field(None, gt=0)
    rpe: Optional[int] = Field(None, ge=1, le=10)
    notes: Optional[str] = None


class TrainingLoadResponse(BaseModel):
    id: str
    athlete_id: str
    entry_date: date
    session_type: Optional[str] = None
    duration_minutes: Optional[int] = None
    rpe: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TrainingLoadListResponse(BaseModel):
    items: list[TrainingLoadResponse]
    total: int
    page: int
    page_size: int
