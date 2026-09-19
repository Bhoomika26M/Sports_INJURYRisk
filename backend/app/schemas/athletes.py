"""
Pydantic schemas for athlete management endpoints.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import (
    AnatomicalSide,
    BiologicalSex,
    DominantLeg,
    InjuryType,
)


# ---------------------------------------------------------------------------
# Age / anthropometric helpers
# ---------------------------------------------------------------------------
def _validate_positive(v: Decimal | float | None, name: str) -> Decimal | None:
    if v is not None and float(v) <= 0:
        raise ValueError(f"{name} must be positive")
    return v


# ---------------------------------------------------------------------------
# Athlete schemas
# ---------------------------------------------------------------------------
class AthleteCreate(BaseModel):
    date_of_birth: date
    biological_sex: BiologicalSex
    height_cm: Decimal = Field(..., gt=0, description="Height in centimetres (positive)")
    weight_kg: Decimal = Field(..., gt=0, description="Weight in kilograms (positive)")
    dominant_leg: DominantLeg = DominantLeg.RIGHT
    primary_sport: str = Field(..., min_length=1, max_length=100)
    team_affiliation: Optional[str] = Field(None, max_length=150)
    position: Optional[str] = Field(None, max_length=80)
    competitive_level: str = "collegiate"

    @field_validator("date_of_birth")
    @classmethod
    def validate_age(cls, v: date) -> date:
        today = date.today()
        age = (today - v).days // 365
        if age < 10 or age > 70:
            raise ValueError("Athlete age must be between 10 and 70 years")
        return v


class AthleteUpdate(BaseModel):
    date_of_birth: Optional[date] = None
    biological_sex: Optional[BiologicalSex] = None
    height_cm: Optional[Decimal] = Field(None, gt=0)
    weight_kg: Optional[Decimal] = Field(None, gt=0)
    dominant_leg: Optional[DominantLeg] = None
    primary_sport: Optional[str] = Field(None, min_length=1, max_length=100)
    team_affiliation: Optional[str] = Field(None, max_length=150)
    position: Optional[str] = Field(None, max_length=80)
    competitive_level: Optional[str] = None

    @field_validator("date_of_birth")
    @classmethod
    def validate_age(cls, v: Optional[date]) -> Optional[date]:
        if v is None:
            return v
        today = date.today()
        age = (today - v).days // 365
        if age < 10 or age > 70:
            raise ValueError("Athlete age must be between 10 and 70 years")
        return v


class AthleteRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    date_of_birth: date
    biological_sex: BiologicalSex
    height_cm: Decimal
    weight_kg: Decimal
    dominant_leg: DominantLeg
    primary_sport: str
    team_affiliation: Optional[str]
    position: Optional[str]
    competitive_level: str
    created_at: datetime
    updated_at: datetime


class PaginatedAthletes(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[AthleteRead]


# ---------------------------------------------------------------------------
# Injury history schemas
# ---------------------------------------------------------------------------
class InjuryCreate(BaseModel):
    injury_type: InjuryType
    anatomical_side: AnatomicalSide
    diagnosis_details: Optional[str] = Field(None, max_length=255)
    injury_date: date
    severity_grade: Optional[str] = Field(None, max_length=20)
    surgical_intervention: bool = False
    return_to_play_date: Optional[date] = None
    fully_resolved: bool = True
    clinical_notes: Optional[str] = None


class InjuryRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    athlete_id: uuid.UUID
    injury_type: InjuryType
    anatomical_side: AnatomicalSide
    diagnosis_details: Optional[str]
    injury_date: date
    severity_grade: Optional[str]
    surgical_intervention: bool
    return_to_play_date: Optional[date]
    fully_resolved: bool
    clinical_notes: Optional[str]
    created_at: datetime


# ---------------------------------------------------------------------------
# Training profile schemas
# ---------------------------------------------------------------------------
class TrainingProfileCreate(BaseModel):
    effective_date: date = Field(default_factory=date.today)
    weekly_training_hours: Decimal = Field(..., ge=0)
    sessions_per_week: int = Field(..., ge=1)
    strength_sessions_per_week: int = Field(2, ge=0)
    current_training_phase: str = "in_season"
    acute_chronic_workload_ratio: Optional[Decimal] = Field(None, ge=0)
    resting_heart_rate_bpm: Optional[int] = Field(None, ge=30, le=220)
    is_current: bool = True


class TrainingProfileRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    athlete_id: uuid.UUID
    effective_date: date
    weekly_training_hours: Decimal
    sessions_per_week: int
    strength_sessions_per_week: int
    current_training_phase: str
    acute_chronic_workload_ratio: Optional[Decimal]
    resting_heart_rate_bpm: Optional[int]
    is_current: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Physical assessment schemas
# ---------------------------------------------------------------------------
class AssessmentCreate(BaseModel):
    assessment_date: date = Field(default_factory=date.today)
    assessment_type: str = "pre_season_baseline"
    weight_at_assessment_kg: Optional[Decimal] = Field(None, gt=0)
    ankle_dorsiflexion_left_cm: Optional[Decimal] = Field(None, ge=0)
    ankle_dorsiflexion_right_cm: Optional[Decimal] = Field(None, ge=0)
    single_leg_hop_left_cm: Optional[Decimal] = Field(None, ge=0)
    single_leg_hop_right_cm: Optional[Decimal] = Field(None, ge=0)
    y_balance_composite_score: Optional[Decimal] = Field(None, ge=0, le=200)
    clinical_observations: Optional[str] = None


class AssessmentRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    athlete_id: uuid.UUID
    assessor_id: uuid.UUID
    assessment_date: date
    assessment_type: str
    weight_at_assessment_kg: Optional[Decimal]
    ankle_dorsiflexion_left_cm: Optional[Decimal]
    ankle_dorsiflexion_right_cm: Optional[Decimal]
    single_leg_hop_left_cm: Optional[Decimal]
    single_leg_hop_right_cm: Optional[Decimal]
    y_balance_composite_score: Optional[Decimal]
    clinical_observations: Optional[str]
    created_at: datetime


# ---------------------------------------------------------------------------
# Assignment schemas
# ---------------------------------------------------------------------------
class AssignmentCreate(BaseModel):
    athlete_id: uuid.UUID
    coach_id: uuid.UUID
    assignment_role: str = "head_coach"


class AssignmentRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    coach_id: uuid.UUID
    athlete_id: uuid.UUID
    assignment_role: str
    assigned_at: date
    is_active: bool
    created_at: datetime
