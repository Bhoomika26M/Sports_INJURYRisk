from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class AnomalyEvent(BaseModel):
    timestamp_ms: int
    metric: str
    observed_value: Optional[float]
    reference_rule: str
    severity: str = Field(..., description="'low', 'medium', 'high', 'critical'")
    explanation: str
    is_data_quality_issue: bool = False

class TechniqueAssessment(BaseModel):
    technique_grade: str = Field(..., description="'Optimal', 'Good', 'Suboptimal', 'High Risk'")
    technique_score: float = Field(..., ge=0, le=100)
    execution_summary: str
    primary_faults: List[str] = []
    execution_faults: List[str] = []

class MotionInconsistency(BaseModel):
    coefficient_of_variation_pct: float
    smoothness_jerk_score: float = Field(..., ge=0, le=100)
    consistency_rating: str = Field(..., description="'Consistent', 'Mild Inconsistency', 'High Inconsistency'")
    jerk_index: Optional[float] = None

class AnomalyDetectionResponse(BaseModel):
    video_id: int
    total_anomalies: int
    events: List[AnomalyEvent]
    disclaimer: str = "These anomalies detect unusual kinematics or tracking errors. They do NOT directly detect fatigue or injury without clinical validation."
    
    # Module 7: Movement Anomaly Detection Engine Extensions
    movement_deviations_count: int = 0
    technique_assessment: Optional[TechniqueAssessment] = None
    motion_inconsistency: Optional[MotionInconsistency] = None
    fatigue_indicators: List[str] = []
    performance_decline_alerts: List[str] = []
