from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from datetime import datetime, timezone
from app.database import Base


class AnalysisRecord(Base):
    __tablename__ = "analysis_records"

    id = Column(Integer, primary_key=True, index=True)
    video_name = Column(String, nullable=False)
    movement_type = Column(String, default="GENERAL")
    athlete_id = Column(String, nullable=True, index=True)
    
    # Movement Quality Scores (0 - 100)
    overall_score = Column(Float, nullable=False)
    grade = Column(String, nullable=False)
    valgus_stability_score = Column(Float, nullable=False)
    symmetry_score = Column(Float, nullable=False)
    rom_score = Column(Float, nullable=False)
    posture_score = Column(Float, nullable=False)
    
    # Biomechanical Kinematics Summary
    peak_valgus = Column(Float, default=0.0)
    mean_asymmetry = Column(Float, default=0.0)
    peak_flexion = Column(Float, default=0.0)
    peak_trunk_lean = Column(Float, default=0.0)
    
    # JSON or serialized text
    anomalies = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
