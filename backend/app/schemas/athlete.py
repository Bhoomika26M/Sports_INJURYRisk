from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class InjuryHistoryItem(BaseModel):
    injury_name: str
    body_part: str # e.g. "Right Knee (ACL)", "Left Hamstring", "Right Ankle"
    year_or_date: str
    severity: str # Mild, Moderate, Severe, Surgical
    status: str # Fully Recovered, Ongoing Rehab, Vulnerable

class AthleteBase(BaseModel):
    athlete_code: str
    name: str
    sport_type: str
    position: Optional[str] = None
    age: int
    height: float # cm
    weight: float # kg
    training_load: float = 12.0 # hours/week
    acwr: float = 1.15 # acute-to-chronic workload ratio
    injury_history: List[Dict[str, Any]] = []
    physical_assessment: Dict[str, Any] = {}

class AthleteCreate(AthleteBase):
    pass

class AthleteUpdate(BaseModel):
    name: Optional[str] = None
    sport_type: Optional[str] = None
    position: Optional[str] = None
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    training_load: Optional[float] = None
    acwr: Optional[float] = None
    injury_history: Optional[List[Dict[str, Any]]] = None
    physical_assessment: Optional[Dict[str, Any]] = None

class AthleteResponse(AthleteBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
