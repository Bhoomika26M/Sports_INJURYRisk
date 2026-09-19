"""SQLAlchemy models for videos, pose_frames, and biomechanical_metrics.

Matches /docs/SCHEMA.md exactly.
"""

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Integer,
    Numeric,
    String,
    Text,
    func,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class VideoProcessingStatus(str, enum.Enum):
    pending_upload = "pending_upload"
    uploaded = "uploaded"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()
    )
    athlete_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    uploaded_by: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=False
    )
    movement_type: Mapped[str] = mapped_column(String(50), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255))
    duration_seconds: Mapped[float | None] = mapped_column(Numeric(6, 2))
    fps: Mapped[float | None] = mapped_column(Numeric(5, 2))
    resolution_width: Mapped[int | None] = mapped_column(Integer)
    resolution_height: Mapped[int | None] = mapped_column(Integer)
    camera_view: Mapped[str] = mapped_column(String(20), nullable=False)
    processing_status: Mapped[VideoProcessingStatus] = mapped_column(
        Enum(VideoProcessingStatus, name="video_processing_status", create_constraint=True),
        nullable=False,
        server_default="pending_upload",
        index=True,
    )
    person_count_detected: Mapped[int | None] = mapped_column(Integer)
    detection_rate: Mapped[float | None] = mapped_column(Numeric(4, 3))
    error_code: Mapped[str | None] = mapped_column(String(50))
    error_message: Mapped[str | None] = mapped_column(Text)
    job_id: Mapped[str | None] = mapped_column(String(255))
    progress_pct: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    annotated_video_key: Mapped[str | None] = mapped_column(String(500))
    thumbnail_key: Mapped[str | None] = mapped_column(String(500))
    
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processing_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    athlete = relationship("Athlete", back_populates="videos")
    pose_frames = relationship("PoseFrame", back_populates="video", cascade="all, delete-orphan")
    biomechanical_metrics = relationship("BiomechanicalMetric", back_populates="video", cascade="all, delete-orphan")


class PoseFrame(Base):
    __tablename__ = "pose_frames"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()
    )
    video_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    frame_number: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    keypoints: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    model_used: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint('video_id', 'frame_number', name='uq_pose_frames_video_frame'),
    )

    video = relationship("Video", back_populates="pose_frames")


class BiomechanicalMetric(Base):
    __tablename__ = "biomechanical_metrics"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()
    )
    video_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    frame_number: Mapped[int] = mapped_column(Integer, nullable=False)
    metric_name: Mapped[str] = mapped_column(String(50), nullable=False)
    metric_value: Mapped[float] = mapped_column(Numeric(8, 3), nullable=False)
    plane: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    video = relationship("Video", back_populates="biomechanical_metrics")
