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

class AnomalyDetectionResponse(BaseModel):
    video_id: int
    total_anomalies: int
    events: List[AnomalyEvent]
    disclaimer: str = "These anomalies detect unusual kinematics or tracking errors. They do NOT directly detect fatigue or injury without clinical validation."
