from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, JSON
from datetime import datetime
from app.database import Base

class BiomechanicalAnalysis(Base):
    __tablename__ = "biomechanical_analyses"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=True)
    total_frames_analyzed = Column(Integer, default=0)
    mean_fps = Column(Float, default=30.0)
    
    # Biomechanical Metrics Summary
    knee_valgus_left_max = Column(Float, default=0.0) # degrees
    knee_valgus_right_max = Column(Float, default=0.0)
    knee_valgus_avg = Column(Float, default=0.0)
    hip_stability_score = Column(Float, default=0.0) # 0-100
    pelvic_drop_deg = Column(Float, default=0.0)
    trunk_lean_lateral_max = Column(Float, default=0.0) # degrees
    trunk_lean_forward_max = Column(Float, default=0.0)
    landing_mechanics_score = Column(Float, default=0.0) # 0-100
    initial_contact_knee_flexion_deg = Column(Float, default=0.0)
    stride_length_est = Column(Float, default=0.0) # meters
    joint_alignment_score = Column(Float, default=0.0) # 0-100
    balance_stability_index = Column(Float, default=0.0) # 0-100
    movement_symmetry_score = Column(Float, default=0.0) # 0-100% (100 is ideal)
    range_of_motion_score = Column(Float, default=0.0) # 0-100
    force_impact_estimation_g = Column(Float, default=0.0) # estimated G-force
    
    # Time-series frame telemetry (downsampled or complete)
    time_series_data = Column(JSON, default=list) # [{frame, time, knee_l, knee_r, valgus_l, valgus_r, hip_l, hip_r, trunk_lean, ankle_l, ankle_r}]
    
    created_at = Column(DateTime, default=datetime.utcnow)
