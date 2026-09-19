import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base

def now():
    return datetime.now(tz=ZoneInfo("UTC"))

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    risk_score_id = Column(UUID(as_uuid=True), ForeignKey("risk_scores.id", ondelete="CASCADE"), nullable=False)
    category = Column(String(30), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)
