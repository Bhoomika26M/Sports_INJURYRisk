from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    athlete_id = Column(Integer, ForeignKey("athlete_profiles.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=True, index=True)
    
    # Types: high_risk_movement, injury_risk, training_load, recovery_reminder, assessment_completion
    notification_type = Column(String(50), nullable=False, index=True)
    
    # Severity: info, warning, critical
    severity = Column(String(20), default="info", index=True)
    
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    # Flexible structured payload: metric names, values, thresholds, suggested actions
    data = Column(JSON, default=dict)
    
    is_read = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    athlete = relationship("AthleteProfile")
    user = relationship("User")
    video = relationship("Video")
