from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class NotificationCreate(BaseModel):
    athlete_id: Optional[str] = None
    athlete_name: Optional[str] = None
    severity: str = "INFO"  # CRITICAL, WARNING, INFO
    category: str = "GENERAL"
    title: str
    message: str


class NotificationOut(BaseModel):
    id: int
    athlete_id: Optional[str] = None
    athlete_name: Optional[str] = None
    severity: str
    category: str
    title: str
    message: str
    is_read: bool
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
