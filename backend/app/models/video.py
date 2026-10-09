from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from datetime import datetime
from app.database import Base

class VideoRecord(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=True)
    title = Column(String(255), nullable=False)
    activity_type = Column(String(100), nullable=False) # Running, Sprinting, Jumping, Squatting, Landing, Throwing, Cutting Movements, Sport-Specific Drills
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    processed_video_path = Column(String(500), nullable=True)
    file_size = Column(Integer, default=0) # Bytes
    duration_seconds = Column(Float, default=0.0)
    fps = Column(Float, default=30.0)
    frame_count = Column(Integer, default=0)
    resolution = Column(String(50), default="1280x720")
    status = Column(String(50), default="uploaded") # uploaded, processing, analyzed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
