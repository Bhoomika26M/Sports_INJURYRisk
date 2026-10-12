from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base


class PoseAnalysis(Base):
    __tablename__ = "pose_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False, unique=True)
    
    # Pose model information
    pose_model = Column(String, nullable=False)  # e.g., "MoveNet Lightning"
    pose_model_version = Column(String, nullable=True)
    analysis_version = Column(String, nullable=False)  # For tracking algorithm changes
    
    # Frame information
    total_frames = Column(Integer, nullable=True)
    processed_frames = Column(Integer, nullable=True)
    frame_sample_rate = Column(Float, nullable=True)  # FPS used for analysis
    
    # Pose quality metrics
    pose_quality = Column(JSON, nullable=True)  # valid_frames, low_confidence_frames, interpolated_frames, mean_confidence
    
    # Keypoint data (stored as JSON for flexibility)
    # Structure: [{frame: 0, timestamp: 0.0, keypoints: [{x, y, confidence, name}, ...]}, ...]
    keypoints_data = Column(JSON, nullable=True)
    
    # Tracking data (YOLO11n + ByteTrack)
    # Structure: [{frame: 0, timestamp: 0.0, tracked_objects: [{track_id, bbox, confidence, ...}]}, ...]
    tracking_data = Column(JSON, nullable=True)
    
    # ROI data (bounding box expansion and cropping)
    # Structure: [{frame: 0, original_bbox, expanded_bbox, roi_width, roi_height}, ...]
    roi_data = Column(JSON, nullable=True)
    
    # Movement-change analysis (early vs late comparison)
    # Structure: {status, total_repetitions, early_metrics, late_metrics, early_vs_late_comparison}
    movement_change_analysis = Column(JSON, nullable=True)
    
    # Normalized skeleton data
    normalized_skeleton = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    video = relationship("Video", back_populates="pose_analysis")
    movement_windows = relationship("MovementWindow", back_populates="pose_analysis")
    biomechanical_analysis = relationship("BiomechanicalAnalysis", back_populates="pose_analysis", uselist=False)
