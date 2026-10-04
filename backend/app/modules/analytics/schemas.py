"""Analytics Pydantic schemas."""

from pydantic import BaseModel

from app.modules.risk_scoring.scoring import METHODOLOGY_NOTE


class TeamOverviewResponse(BaseModel):
    total_athletes: int
    total_videos: int
    videos_completed: int
    videos_failed: int
    videos_processing: int
    avg_risk_score: float | None = None
    high_risk_count: int
    critical_risk_count: int
    low_risk_count: int
    moderate_risk_count: int


class RiskTrendPoint(BaseModel):
    video_id: str
    movement_type: str
    overall_score: float
    risk_category: str
    created_at: str


class AthleteTrendResponse(BaseModel):
    athlete_id: str
    points: list[RiskTrendPoint]
    total: int
    trend: dict | None = None
    methodology_note: str = METHODOLOGY_NOTE


class MovementAnalyticsResponse(BaseModel):
    movement_type: str | None
    videos_analyzed: int
    baselines: dict
    anomaly_distribution: dict