from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class InvitationCreate(BaseModel):
    professional_user_id: int
    notes: Optional[str] = None


class InvitationRespond(BaseModel):
    action: str  # "accept" or "reject"


class ProfessionalUserSummary(BaseModel):
    id: int
    full_name: str
    email: str
    role: str

    class Config:
        from_attributes = True


class InvitationResponse(BaseModel):
    id: int
    athlete_id: int
    professional_user_id: int
    status: str
    invited_role: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    professional: Optional[ProfessionalUserSummary] = None
    athlete_public_id: Optional[str] = None

    class Config:
        from_attributes = True
