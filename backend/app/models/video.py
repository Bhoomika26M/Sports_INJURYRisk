from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    athlete_id = Column(Integer, ForeignKey("athlete_profiles.id"), nullable=False)
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    filename = Column(String, unique=True, index=True, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    format = Column(String, nullable=False)
    
    size_bytes = Column(Integer, nullable=False)
    duration_sec = Column(Float)
    fps = Column(Float)
    width = Column(Integer)
    height = Column(Integer)
    
    status = Column(String, default="uploaded") # uploaded, processing, completed, error
    error_message = Column(String, nullable=True)
    movement_type = Column(String, default="general")
    processing_progress = Column(Integer, default=0)
    quality_score = Column(Float, nullable=True)
    quality_issues = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    athlete = relationship("AthleteProfile")
    uploader = relationship("User")
