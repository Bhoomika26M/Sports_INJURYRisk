from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class CategoryRiskDetail(BaseModel):
    category_name: str
    probability: float # 0.0 to 1.0
    risk_level: str # Low, Moderate, High, Critical
    risk_score: float # 0 - 100
    primary_factors: List[str]
    description: str

class CorrectiveExerciseItem(BaseModel):
    name: str
    target_area: str
    sets: str
    reps: str
    frequency: str
    difficulty: str
    coaching_cues: List[str]
    equipment: Optional[str] = "Bodyweight / Resistance Band"

class AnomalyEvent(BaseModel):
    frame_index: int
    timestamp_sec: float
    anomaly_type: str # e.g. "Severe Dynamic Valgus", "Excessive Trunk Tilt", "Deceleration Asymmetry"
    severity: str # Medium, High, Critical
    metric_value: float
    threshold_value: float
    description: str

class InjuryRiskResponse(BaseModel):
    id: int
    video_id: int
    athlete_id: Optional[int] = None
    analysis_id: int
    overall_injury_risk_score: float
    risk_category: str
    
    # Weighted Scoring Components (Biomechanical 35%, Historical 20%, Asymmetry 20%, Training Load 15%, Fatigue 10%)
    biomechanical_deviation_score: float
    historical_injury_factor_score: float
    movement_asymmetry_score: float
    training_load_indicator_score: float
    fatigue_indicator_score: float
    
    movement_quality_score: float
    biomechanical_efficiency_score: float
    fatigue_risk_score: float
    overall_athlete_health_score: float
    
    category_risks: Dict[str, Any]
    anomalies_detected: List[Dict[str, Any]]
    corrective_recommendations: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True
