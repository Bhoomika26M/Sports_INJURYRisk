from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Union
from enum import Enum

class DataSource(str, Enum):
    MEASURED = "measured"
    ESTIMATED = "estimated"
    MANUAL = "manual"

class RiskComponentInput(BaseModel):
    value: Optional[float] = Field(None, ge=0, le=100, description="Component value normalized from 0 to 100")
    source: DataSource = Field(DataSource.ESTIMATED, description="Source of the data")
    is_missing: bool = Field(False, description="Flag to indicate if this data is explicitly missing")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Raw input that contributed to this component")

class RiskScoreInput(BaseModel):
    biomechanical_deviations: RiskComponentInput
    historical_injury_factors: RiskComponentInput
    movement_asymmetry: RiskComponentInput
    training_load: RiskComponentInput
    fatigue_indicators: RiskComponentInput

class ComponentScore(BaseModel):
    score: Optional[float] = None
    weight: float
    weighted_score: Optional[float] = None
    source: str
    is_missing: bool
    explanation: str

class RiskScoreResponse(BaseModel):
    composite_score: Optional[float] = Field(None, ge=0, le=100)
    risk_band: str = Field(..., description="Provisional low, moderate, high and critical bands, labelled as unvalidated screening thresholds.")
    confidence_score: float = Field(..., ge=0, le=100, description="Based on data completeness and measurement sources")
    data_completeness: float = Field(..., ge=0, le=100, description="Percentage of components provided")
    components: Dict[str, ComponentScore]
    contributing_factors: List[str]
    disclaimer: str = "This score is NOT an injury probability or a clinically validated prediction. It is a preliminary, unvalidated screening threshold."
    injury_categories: Optional[Dict[str, Any]] = None

    # Module 8: Risk Scoring Engine Enhanced Attributes
    injury_risk_score: Optional[float] = None
    movement_quality_score: float = 100.0
    biomechanical_efficiency_score: float = 100.0
    fatigue_risk_score: float = 0.0
    overall_athlete_health_score: float = 100.0
    risk_category: str = "Low Risk"

# ==========================================
# Module 6: Injury Risk Prediction Schemas
# ==========================================

class HighRiskMovement(BaseModel):
    timestamp_ms: int
    time_sec: float
    movement_name: str
    observed_metric: str
    value: str
    severity: str = "high" # moderate, high, critical
    clinical_mechanism: str

class InjuryCategoryPrediction(BaseModel):
    category_id: str # acl_risk, hamstring_risk, ankle_sprain_risk, shoulder_risk, lower_back_risk, overuse_risk
    name: str # e.g. "ACL Injury Risk"
    probability_pct: float = Field(..., ge=0, le=100, description="Predicted injury probability percentage")
    risk_level: str = Field(..., description="Low, Moderate, High, Critical")
    risk_factors: List[str]
    high_risk_movements: List[HighRiskMovement] = []
    clinical_evidence: str
    prevention_protocols: List[str]

class InjuryRiskPredictionResponse(BaseModel):
    athlete_id: int
    video_id: Optional[int] = None
    overall_risk_score: float = Field(..., ge=0, le=100)
    overall_risk_band: str
    confidence_score: float = Field(..., ge=0, le=100)
    categories: Dict[str, InjuryCategoryPrediction]
    personalized_factors: Dict[str, Any]
    high_risk_alerts_count: int
    disclaimer: str = "Evidence-based injury risk predictions derived from kinematic video analytics and epidemiological models. For screening and injury prevention use; not an orthopaedic diagnostic tool."

class RiskTrendPoint(BaseModel):
    date: str
    video_id: int
    movement_type: str
    composite_score: float
    risk_band: str
    acl_probability: float
    hamstring_probability: float
    ankle_probability: float
    shoulder_probability: float
    lower_back_probability: float
    overuse_probability: float

class RiskTrendResponse(BaseModel):
    athlete_id: int
    trend_points: List[RiskTrendPoint]
    overall_trajectory: str # "improving", "stable", "deteriorating"
    trajectory_explanation: str
