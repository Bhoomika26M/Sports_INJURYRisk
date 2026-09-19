import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import CameraView, MovementType, ProcessingStatus, RiskTier


class Video(Base):
    __tablename__ = "videos"
    __table_args__ = (
        CheckConstraint(
            "overall_risk_score IS NULL OR (overall_risk_score >= 0 AND overall_risk_score <= 100)",
            name="chk_video_risk_score_range",
        ),
        Index("idx_videos_athlete_id", "athlete_id"),
        Index(
            "idx_videos_status",
            "processing_status",
            postgresql_where=text("processing_status != 'completed'"),
        ),
        Index("idx_videos_risk_tier", "risk_tier"),
        Index("idx_videos_movement_created", "movement_type", text("created_at DESC")),
        Index("idx_videos_metrics_gin", "calculated_metrics_summary", postgresql_using="gin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    athlete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False
    )
    assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("physical_assessments.id", ondelete="SET NULL"), nullable=True
    )
    uploaded_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(50), default="video/mp4", nullable=False)
    duration_seconds: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    frame_rate_fps: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    frame_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    frame_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    movement_type: Mapped[MovementType] = mapped_column(
        Enum(MovementType, name="movement_type_enum", native_enum=True, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    camera_view: Mapped[CameraView] = mapped_column(
        Enum(CameraView, name="camera_view_enum", native_enum=True, values_callable=lambda obj: [e.value for e in obj]),
        default=CameraView.FRONTAL,
        nullable=False,
    )
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus, name="processing_status_enum", native_enum=True, values_callable=lambda obj: [e.value for e in obj]),
        default=ProcessingStatus.PENDING_UPLOAD,
        nullable=False,
    )
    calculated_metrics_summary: Mapped[Dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    overall_risk_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    risk_tier: Mapped[RiskTier | None] = mapped_column(
        Enum(RiskTier, name="risk_tier_enum", native_enum=True, values_callable=lambda obj: [e.value for e in obj]),
        nullable=True,
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    athlete = relationship("Athlete", back_populates="videos")
    assessment = relationship("PhysicalAssessment", back_populates="videos")
    uploaded_by_user = relationship("User", back_populates="uploaded_videos", foreign_keys=[uploaded_by_user_id])
