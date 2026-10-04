"""SQLAlchemy models for risk_scoring tables."""

import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import Column, String, Float, Integer, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base
from app.modules.risk_scoring.scoring import METHODOLOGY_NOTE

def now():
    return datetime.now(tz=ZoneInfo("UTC"))


class MovementBaseline(Base):
    __tablename__ = "movement_baselines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    athlete_id = Column(UUID(as_uuid=True), ForeignKey("athletes.id"), nullable=True)
    movement_type = Column(String(50), nullable=False)
    metric_name = Column(String(50), nullable=False)
    # NULL = insufficient baseline ("we don't know"). Never store a fabricated 0.0 +/- 0.0.
    mean_value = Column(Float, nullable=True)
    std_dev = Column(Float, nullable=True)
    sample_size = Column(Integer, nullable=False)  # unit: VIDEOS (one video-level feature value per video; == video_count)
    video_count = Column(Integer, nullable=False, default=0, server_default="0")    # distinct completed videos
    athlete_count = Column(Integer, nullable=False, default=0, server_default="0")  # distinct athletes
    computed_at = Column(DateTime(timezone=True), default=now, nullable=False)


class AnomalyScore(Base):
    __tablename__ = "anomaly_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    frame_number = Column(Integer, nullable=True)
    anomaly_score = Column(Float, nullable=False)
    method = Column(String(30), nullable=False, default='isolation_forest')
    baseline_sample_size = Column(Integer, nullable=False)
    flagged = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)


class RiskScore(Base):
    __tablename__ = "risk_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, unique=True)
    athlete_id = Column(UUID(as_uuid=True), ForeignKey("athletes.id"), nullable=False)
    overall_score = Column(Float, nullable=False)
    risk_category = Column(String(20), nullable=False)
    score_breakdown = Column(JSONB, nullable=False)
    methodology_note = Column(Text, nullable=False, default=METHODOLOGY_NOTE)
    # Full AI-engine assessment (sub-scores, injury categories, baseline info, quality, engine version).
    assessment = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)