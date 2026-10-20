from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AthleteCreate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    sport_type: str = Field(min_length=2, max_length=64)
    position: str | None = Field(default=None, max_length=64)
    age: int = Field(ge=5, le=100)
    height_cm: float = Field(ge=80, le=250)
    weight_kg: float = Field(ge=20, le=250)
    weekly_training_load: float | None = Field(default=None, ge=0)


class AthleteUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    sport_type: str | None = Field(default=None, min_length=2, max_length=64)
    position: str | None = Field(default=None, max_length=64)
    age: int | None = Field(default=None, ge=5, le=100)
    height_cm: float | None = Field(default=None, ge=80, le=250)
    weight_kg: float | None = Field(default=None, ge=20, le=250)
    weekly_training_load: float | None = Field(default=None, ge=0)


class AthleteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    athlete_code: str
    full_name: str
    sport_type: str
    position: str | None
    age: int
    height_cm: float
    weight_kg: float
    weekly_training_load: float | None
    created_at: datetime


class InjuryCreate(BaseModel):
    injury_type: str = Field(min_length=2, max_length=120)
    body_part: str = Field(min_length=2, max_length=64)
    injury_date: date
    severity: Literal["minor", "moderate", "severe"] = "moderate"
    status: Literal["active", "recovering", "recovered"] = "recovered"
    recovered_date: date | None = None
    notes: str | None = None


class InjuryOut(InjuryCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    athlete_id: int


class TrainingLoadCreate(BaseModel):
    entry_date: date
    duration_min: float = Field(gt=0, le=600)
    rpe: float = Field(ge=1, le=10)
    notes: str | None = None


class TrainingLoadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    athlete_id: int
    entry_date: date
    duration_min: float
    rpe: float
    load_au: float
    notes: str | None


class AssessmentCreate(BaseModel):
    notes: str | None = None
    metrics: dict = Field(default_factory=dict)


class AssessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    athlete_id: int
    assessed_by: int | None
    assessed_at: datetime
    notes: str | None
    metrics: dict


class AccessGrant(BaseModel):
    email: EmailStr


class AccessOut(BaseModel):
    user_id: int
    email: EmailStr
    full_name: str
    access_role: str
