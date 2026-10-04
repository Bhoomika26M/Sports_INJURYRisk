"""Risk scoring Pydantic schemas."""

from typing import Any, Literal, Optional
from pydantic import BaseModel


SupportedMovementType = Literal[
    "running", "sprinting", "jumping", "squatting", "landing",
    "throwing", "cutting", "sport_specific",
]


class BaselineRecomputeRequest(BaseModel):
    movement_type: SupportedMovementType


class ScoreComponent(BaseModel):
    """One weighted component. `points`/`max` are its contribution to / share of the 0-100 total."""
    points: float
    max: float
    score: Optional[float] = None
    weight: float
    effective_weight: float
    available: bool
    detail: dict[str, Any] = {}


class ScoreBreakdown(BaseModel):
    biomechanical_deviations: ScoreComponent
    historical_injury_factors: ScoreComponent
    movement_asymmetry: ScoreComponent
    training_load_indicators: ScoreComponent
    fatigue_indicators: ScoreComponent


class RiskScoreResponse(BaseModel):
    overall_score: float
    risk_category: str
    score_breakdown: ScoreBreakdown
    methodology_note: str
    engine_version: str
    data_completeness: float
    missing_components: list[str]
    sub_scores: dict[str, Any]
    injury_categories: dict[str, Any]
    baseline: dict[str, Any]
    quality: Optional[dict[str, Any]] = None
    movement: Optional[dict[str, Any]] = None
    reliability: str
    anomaly_features: list[dict[str, Any]] = []
    data_quality: Optional[dict[str, Any]] = None  # pose-pipeline coverage: detection_rate, person count, caveat
