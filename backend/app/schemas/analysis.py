from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AnalysisSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    video_id: int
    athlete_id: int
    activity: str
    risk_score: float
    risk_category: str
    movement_quality: float
    created_at: datetime


class AnalysisOut(AnalysisSummary):
    biomechanics: dict
    deviations: list
    anomalies: dict
    injury_risks: list
    scores: dict
    recommendations: dict
