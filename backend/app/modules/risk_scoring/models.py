import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import Column, String, Float, Integer, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base

def now():
    return datetime.now(tz=ZoneInfo("UTC"))

class MovementBaseline(Base):
    __tablename__ = "movement_baselines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    athlete_id = Column(UUID(as_uuid=True), ForeignKey("athletes.id"), nullable=True)
    movement_type = Column(String(50), nullable=False)
    metric_name = Column(String(50), nullable=False)
    mean_value = Column(Float, nullable=False)
    std_dev = Column(Float, nullable=False)
    sample_size = Column(Integer, nullable=False)
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
    methodology_note = Column(Text, nullable=False, default="Composite of movement-pattern anomaly vs. population baseline, a bounded symmetry flag, and a bounded prior-injury flag. Not a trained injury-prediction model. See docs/SCIENCE_CONSTRAINTS.md.")
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)
