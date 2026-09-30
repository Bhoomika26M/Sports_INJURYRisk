"""Risk scoring Pydantic schemas."""

from typing import Literal
from pydantic import BaseModel


SupportedMovementType = Literal[
    "running", "sprinting", "jumping", "squatting", "landing",
    "throwing", "cutting", "sport_specific",
]


class BaselineRecomputeRequest(BaseModel):
    movement_type: SupportedMovementType


class ScoreComponent(BaseModel):
    points: float
    max: float
    detail: str | None = None
    flagged: bool | None = None
    lsi: float | None = None
    caveat: str | None = None
    acwr: float | None = None
    rpe_trend: float | None = None


class ScoreBreakdown(BaseModel):
    movement_anomaly: ScoreComponent
    asymmetry_flag: ScoreComponent
    prior_injury_flag: ScoreComponent
    acwr_flag: ScoreComponent | None = None
    fatigue_flag: ScoreComponent | None = None