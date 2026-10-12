from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base


class MovementWindow(Base):
    __tablename__ = "movement_windows"
    
    id = Column(Integer, primary_key=True, index=True)
    pose_analysis_id = Column(Integer, ForeignKey("pose_analyses.id"), nullable=False, index=True)
    
    # Window boundaries
    start_frame = Column(Integer, nullable=True)
    end_frame = Column(Integer, nullable=True)
    start_time = Column(Float, nullable=True)  # in seconds
    end_time = Column(Float, nullable=True)  # in seconds
    
    # Movement type and phase
    phase = Column(String, nullable=True)  # e.g., "squat", "jump_landing", "running"
    repetition_number = Column(Integer, nullable=True)
    jump_number = Column(Integer, nullable=True)
    stride_number = Column(Integer, nullable=True)
    
    # Additional phase-specific metrics (stored as JSON for flexibility)
    # For squat: bottom_frame, bottom_time, minimum_knee_angle, maximum_knee_angle
    # For jump: takeoff_frame, landing_frame, flight_duration, landing_knee_angle
    # For running: side (left/right)
    metrics = Column(JSON, nullable=True)
    
    # Quality information
    quality_score = Column(Float, nullable=True)
    quality_notes = Column(JSON, nullable=True)  # Additional quality information
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    pose_analysis = relationship("PoseAnalysis", back_populates="movement_windows")
