from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class BiomechanicalMetricsSummary(BaseModel):
    knee_valgus_left_max: float
    knee_valgus_right_max: float
    knee_valgus_avg: float
    hip_stability_score: float
    pelvic_drop_deg: float
    trunk_lean_lateral_max: float
    trunk_lean_forward_max: float
    landing_mechanics_score: float
    initial_contact_knee_flexion_deg: float
    stride_length_est: float
    joint_alignment_score: float
    balance_stability_index: float
    movement_symmetry_score: float
    range_of_motion_score: float
    force_impact_estimation_g: float

class BiomechanicalAnalysisResponse(BaseModel):
    id: int
    video_id: int
    athlete_id: Optional[int] = None
    total_frames_analyzed: int
    mean_fps: float
    metrics: BiomechanicalMetricsSummary
    time_series_data: List[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True
