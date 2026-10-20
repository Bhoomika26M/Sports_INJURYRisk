from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    athlete_id: int | None
    type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    athlete_id: int
    analysis_id: int | None
    report_type: str
    file_format: str
    created_at: datetime


ReportType = Literal["injury_risk", "biomechanical", "movement", "performance", "rehabilitation"]
ReportFormat = Literal["pdf", "xlsx"]
