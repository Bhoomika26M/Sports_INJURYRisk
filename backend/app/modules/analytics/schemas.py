from pydantic import BaseModel


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
    methodology_note: str = (
        "Composite of movement-pattern anomaly vs. population baseline, "
        "a bounded symmetry flag, and a bounded prior-injury flag. "
        "Not a trained injury-prediction model. See docs/SCIENCE_CONSTRAINTS.md."
    )
