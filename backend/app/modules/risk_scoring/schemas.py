from typing import Literal
from pydantic import BaseModel

SupportedMovementType = Literal[
    "running", "sprinting", "jumping", "squatting", "landing",
    "throwing", "cutting_movements", "sport_specific",
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

class ScoreBreakdown(BaseModel):
    movement_anomaly: ScoreComponent
    asymmetry_flag: ScoreComponent
    prior_injury_flag: ScoreComponent
