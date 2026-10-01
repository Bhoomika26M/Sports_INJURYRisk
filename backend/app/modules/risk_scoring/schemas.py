"""Risk scoring Pydantic schemas."""

from typing import Literal
from pydantic import BaseModel, Field


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


class BaselineUnitCoverage(BaseModel):
    have: int
    need: int


class InsufficientBaselineResponse(BaseModel):
    """HTTP 202 body. ``unit`` says what ``have``/``need`` count: distinct videos or athletes,
    or per-metric frames -- never an unlabelled "samples"."""

    status: Literal["insufficient_baseline_data"] = "insufficient_baseline_data"
    metric_name: str
    unit: Literal["videos", "athletes", "frames"]
    have: int
    need: int
    coverage: dict[Literal["videos", "athletes", "frames"], BaselineUnitCoverage]
    message: str
