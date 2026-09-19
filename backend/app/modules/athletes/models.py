"""SQLAlchemy models for athletes, injury_history, training_load_entries tables.

Matches /docs/SCHEMA.md exactly — field names, types, constraints.
"""

from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Athlete(Base):
    __tablename__ = "athletes"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        unique=True,
        nullable=True,
    )
    coach_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id"),
        nullable=True,
    )
    sport_type: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[str | None] = mapped_column(String(100), nullable=True)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    height_cm: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    dominant_side: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    injury_history = relationship("InjuryHistory", back_populates="athlete", cascade="all, delete-orphan")
    training_load_entries = relationship("TrainingLoadEntry", back_populates="athlete", cascade="all, delete-orphan")
    videos = relationship("Video", back_populates="athlete", cascade="all, delete-orphan")
    user = relationship("app.modules.users.models.User", foreign_keys=[user_id], lazy="selectin")

    @property
    def full_name(self) -> str | None:
        return self.user.full_name if self.user else None

    __table_args__ = (
        CheckConstraint("dominant_side IN ('left', 'right')", name="ck_athletes_dominant_side"),
        Index("idx_athletes_coach_id", "coach_id"),
    )


class InjuryHistory(Base):
    __tablename__ = "injury_history"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()
    )
    athlete_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
    )
    injury_type: Mapped[str] = mapped_column(String(255), nullable=False)
    body_part: Mapped[str] = mapped_column(String(100), nullable=False)
    injury_date: Mapped[date] = mapped_column(Date, nullable=False)
    recovery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    athlete = relationship("Athlete", back_populates="injury_history")

    __table_args__ = (
        CheckConstraint("severity IN ('minor', 'moderate', 'severe')", name="ck_injury_history_severity"),
        Index("idx_injury_history_athlete_id", "athlete_id"),
    )


class TrainingLoadEntry(Base):
    __tablename__ = "training_load_entries"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()
    )
    athlete_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
    )
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    session_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rpe: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    athlete = relationship("Athlete", back_populates="training_load_entries")

    __table_args__ = (
        CheckConstraint("rpe BETWEEN 1 AND 10", name="ck_training_load_rpe"),
        Index("idx_training_load_athlete_id", "athlete_id"),
    )
