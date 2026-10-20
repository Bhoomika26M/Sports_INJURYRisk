"""Schemas for explainable risk assessment."""

from pydantic import BaseModel
from typing import Dict, List, Optional, Any


class Evidence(BaseModel):
    metric: str
    value: float | int | None = None
    unit: str = ""


class MuscleGroups(BaseModel):
    primary: List[str] = []
    stabilizers: List[str] = []


class RiskFinding(BaseModel):
    severity: str
    risk_type: str
    risk_tag: str = ""
    body_parts: List[str]
    issue: str
    rationale: str
    evidence: List[Evidence]
    recommended_actions: List[str]
    score_contribution: float
    # Anatomical context (scientific terms + muscles involved)
    scientific_term: str = ""
    structures_at_risk: List[str] = []
    muscles: MuscleGroups = MuscleGroups()
    muscles_overactive: List[str] = []
    muscles_underactive: List[str] = []
    mechanism: str = ""


class JointMuscleInfo(BaseModel):
    """A measured joint/angle plus the muscles that act on it."""

    joint: str
    side: str
    muscles_primary: List[str] = []
    muscles_stabilizers: List[str] = []
    samples: int = 0
    mean_deg: Optional[float] = None
    min_deg: Optional[float] = None
    max_deg: Optional[float] = None
    rom_deg: Optional[float] = None


class RiskExplanation(BaseModel):
    how_score_arrived_at: List[str]
    components: Dict[str, float]
    weights: Dict[str, float]


class RiskAssessment(BaseModel):
    overall_risk_score: float
    risk_level: str
    risk_of: List[str]
    findings: List[RiskFinding]
    joints_and_muscles: List[JointMuscleInfo] = []
    explanation: RiskExplanation
    suggestions: List[str]
    frame_insights: List[Dict[str, Any]] = []
