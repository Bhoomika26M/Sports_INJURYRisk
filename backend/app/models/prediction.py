from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from datetime import datetime, timezone
from app.database import Base


class InjuryAssessmentRecord(Base):
    __tablename__ = "injury_assessments"

    id = Column(Integer, primary_key=True, index=True)
    athlete_id = Column(String, nullable=True, index=True)
    video_name = Column(String, default="Movement_Scan")
    movement_type = Column(String, default="SQUAT")

    overall_risk_score = Column(Float, nullable=False)
    risk_level = Column(String, nullable=False)  # LOW, MODERATE, HIGH

    acl_risk = Column(Float, default=0.0)
    hamstring_risk = Column(Float, default=0.0)
    ankle_risk = Column(Float, default=0.0)
    patellar_risk = Column(Float, default=0.0)

    early_warnings = Column(Text, default="[]")
    recommendations = Column(Text, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
