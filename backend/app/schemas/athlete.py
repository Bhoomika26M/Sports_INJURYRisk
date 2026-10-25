from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class AthleteProfileBase(BaseModel):
    sport_type: Optional[str] = None
    position: Optional[str] = None
    age: Optional[int] = Field(None, gt=0, description="Age must be positive")
    height_cm: Optional[float] = Field(None, gt=0, description="Height must be positive")
    weight_kg: Optional[float] = Field(None, gt=0, description="Weight must be positive")
    injury_history: Optional[List[Dict[str, Any]]] = None
    training_load: Optional[Dict[str, Any]] = None
    physical_assessments: Optional[List[Dict[str, Any]]] = None

class AthleteProfileCreate(AthleteProfileBase):
    coach_id: Optional[int] = None
    physiotherapist_id: Optional[int] = None

class AthleteProfileUpdate(AthleteProfileBase):
    coach_id: Optional[int] = None
    physiotherapist_id: Optional[int] = None

class AthleteProfileResponse(AthleteProfileBase):
    id: int
    user_id: int
    name: Optional[str] = None
    assigned_staff: Optional[List[Dict[str, Any]]] = None
    coach: Optional[Dict[str, Any]] = None
    physiotherapist: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}

class AthleteAssignmentBase(BaseModel):
    athlete_id: int
    staff_id: int

class AthleteAssignmentResponse(AthleteAssignmentBase):
    id: int
    created_at: datetime
    
    model_config = {"from_attributes": True}
