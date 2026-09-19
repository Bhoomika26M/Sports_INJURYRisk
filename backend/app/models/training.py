import uuid
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TrainingProfile(Base):
    __tablename__ = "training_profiles"
    __table_args__ = (
        CheckConstraint("weekly_training_hours >= 0", name="chk_training_hours"),
        CheckConstraint("sessions_per_week >= 1", name="chk_sessions_per_week"),
        CheckConstraint(
            "acute_chronic_workload_ratio IS NULL OR acute_chronic_workload_ratio >= 0",
            name="chk_acwr_positive",
        ),
        Index("idx_training_profiles_athlete_id", "athlete_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    athlete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False
    )
    effective_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    weekly_training_hours: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)
    sessions_per_week: Mapped[int] = mapped_column(Integer, nullable=False)
    strength_sessions_per_week: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    current_training_phase: Mapped[str] = mapped_column(String(50), default="in_season", nullable=False)
    acute_chronic_workload_ratio: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    resting_heart_rate_bpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship
    athlete = relationship("Athlete", back_populates="training_profiles")
