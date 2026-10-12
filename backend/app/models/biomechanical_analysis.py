from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base


class BiomechanicalAnalysis(Base):
    __tablename__ = "biomechanical_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    pose_analysis_id = Column(Integer, ForeignKey("pose_analyses.id"), nullable=False, unique=True)
    
    # Joint angles (stored as JSON for flexibility)
    # Structure: {knee_left: {min, max, mean, std}, knee_right: {...}, ...}
    joint_angles = Column(JSON, nullable=True)
    
    # Range of motion
    rom = Column(JSON, nullable=True)  # {joint: {min_angle, max_angle, rom}}
    
    # Left-right symmetry
    symmetry = Column(JSON, nullable=True)  # {knee_asymmetry: {...}, hip_asymmetry: {...}}
    
    # Knee alignment / valgus proxy
    knee_alignment = Column(JSON, nullable=True)
    
    # Trunk metrics
    trunk_lean = Column(JSON, nullable=True)  # {mean, max, std, ...}
    
    # Hip stability
    hip_stability = Column(JSON, nullable=True)
    
    # Balance indicators
    balance = Column(JSON, nullable=True)
    
    # Velocity and acceleration
    velocity = Column(JSON, nullable=True)
    acceleration = Column(JSON, nullable=True)
    
    # Movement smoothness
    smoothness = Column(JSON, nullable=True)
    
    # Landing mechanics (for jumping activities)
    landing_mechanics = Column(JSON, nullable=True)
    
    # Running/sprint features
    running_features = Column(JSON, nullable=True)
    
    # Fatigue-related changes (comparison between early and late repetitions)
    fatigue_analysis = Column(JSON, nullable=True)
    
    # Overall movement quality
    movement_quality = Column(JSON, nullable=True)  # {score, components: {...}}
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    pose_analysis = relationship("PoseAnalysis", back_populates="biomechanical_analysis")
