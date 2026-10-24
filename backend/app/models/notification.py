from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from datetime import datetime, timezone
from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    athlete_id = Column(String, nullable=True, index=True)
    athlete_name = Column(String, nullable=True)
    severity = Column(String, default="INFO")  # CRITICAL, WARNING, INFO
    category = Column(String, default="GENERAL")  # HIGH_RISK_MOVEMENT, TRAINING_OVERLOAD, RECOVERY_REMINDER, ASSESSMENT_COMPLETE
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
