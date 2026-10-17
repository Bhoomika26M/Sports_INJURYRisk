from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any, Optional
from datetime import datetime


class EarlyWarningItem(BaseModel):
    severity: str  # CRITICAL, WARNING, INFO
    title: str
    message: str


class RiskBreakdown(BaseModel):
    acl_risk: float
    hamstring_risk: float
    ankle_risk: float
    patellar_risk: float


class CorrectiveExerciseItem(BaseModel):
    name: str
    category: str
    target: str
    frequency: str
    purpose: str
    difficulty: str


class RecommendationPlan(BaseModel):
    prescribed_exercises: List[CorrectiveExerciseItem]
    training_load_recommendation: str
    recovery_status: str
    recovery_guidelines: List[str]


class InjuryAssessmentResponse(BaseModel):
    id: Optional[int] = None
    athlete_id: Optional[str] = None
    movement_type: str = "SQUAT"
    overall_risk_score: float
    risk_level: str
    risk_breakdown: RiskBreakdown
    early_warnings: List[EarlyWarningItem]
    recommendations: RecommendationPlan
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class InjuryAssessmentRequest(BaseModel):
    athlete_id: Optional[str] = None
    movement_type: Optional[str] = "SQUAT"
    biomechanics: Optional[Dict[str, Any]] = None
