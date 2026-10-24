from pydantic import BaseModel, ConfigDict
from typing import Optional, Any, Dict
from datetime import datetime


class ReportCreate(BaseModel):
    report_title: str
    report_type: str = "BIOMECHANICAL_ASSESSMENT"
    athlete_id: Optional[str] = None
    athlete_name: Optional[str] = None
    generated_by: str = "System"
    summary: str = ""
    data: Optional[Dict[str, Any]] = None


class ReportOut(BaseModel):
    id: int
    report_title: str
    report_type: str
    athlete_id: Optional[str] = None
    athlete_name: Optional[str] = None
    generated_by: str
    summary: str
    data_json: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
