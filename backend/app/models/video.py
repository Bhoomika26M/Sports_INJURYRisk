from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base
import enum


class ProcessingStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    PREPROCESSING = "preprocessing"
    POSE_ESTIMATION = "pose_estimation"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class Video(Base):
    __tablename__ = "videos"
    
    id = Column(Integer, primary_key=True, index=True)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False, index=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Safe server-side filename (never expose original filename to frontend)
    filename = Column(String, nullable=False, unique=True)
    original_filename = Column(String, nullable=False)  # For display purposes only
    storage_path = Column(String, nullable=False)
    
    activity_type = Column(String, nullable=False)
    
    # Video metadata
    file_size = Column(Integer, nullable=True)  # in bytes
    duration = Column(Float, nullable=True)  # in seconds
    fps = Column(Float, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    
    # Processing status
    processing_status = Column(SQLEnum(ProcessingStatus), default=ProcessingStatus.UPLOADED, nullable=False)
    processing_error = Column(String, nullable=True)
    processing_started_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    athlete = relationship("Athlete", backref="videos")
    uploader = relationship("User", foreign_keys=[uploaded_by], backref="uploaded_videos")
    pose_analysis = relationship("PoseAnalysis", back_populates="video", uselist=False)
