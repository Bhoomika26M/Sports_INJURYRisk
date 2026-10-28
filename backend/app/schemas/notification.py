from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict
from enum import Enum

class NotificationType(str, Enum):
    HIGH_RISK_MOVEMENT = "high_risk_movement"
    INJURY_RISK = "injury_risk"
    TRAINING_LOAD = "training_load"
    RECOVERY_REMINDER = "recovery_reminder"
    ASSESSMENT_COMPLETION = "assessment_completion"

class NotificationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class NotificationBase(BaseModel):
    athlete_id: Optional[int] = None
    video_id: Optional[int] = None
    notification_type: str
    severity: str = "info"
    title: str
    message: str
    data: Optional[Dict[str, Any]] = None

class NotificationCreate(NotificationBase):
    user_id: Optional[int] = None

class NotificationResponse(NotificationBase):
    id: int
    user_id: Optional[int] = None
    is_read: bool
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class NotificationSummaryResponse(BaseModel):
    total_count: int
    unread_count: int
    critical_count: int
    warning_count: int
    info_count: int
    notifications: List[NotificationResponse]
