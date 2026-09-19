import uuid
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import BiologicalSex, DominantLeg


class Athlete(Base):
    __tablename__ = "athletes"
    __table_args__ = (
        CheckConstraint("height_cm > 50 AND height_cm < 260", name="chk_athlete_height"),
        CheckConstraint("weight_kg > 20 AND weight_kg < 300", name="chk_athlete_weight"),
        Index("idx_athletes_user_id", "user_id"),
        Index("idx_athletes_team", "team_affiliation"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    biological_sex: Mapped[BiologicalSex] = mapped_column(
        Enum(BiologicalSex, name="biological_sex_enum", native_enum=True, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    height_cm: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    dominant_leg: Mapped[DominantLeg] = mapped_column(
        Enum(DominantLeg, name="dominant_leg_enum", native_enum=True, values_callable=lambda obj: [e.value for e in obj]),
        default=DominantLeg.RIGHT,
        nullable=False,
    )
    primary_sport: Mapped[str] = mapped_column(String(100), nullable=False)
    team_affiliation: Mapped[str | None] = mapped_column(String(150), nullable=True)
    position: Mapped[str | None] = mapped_column(String(80), nullable=True)
    competitive_level: Mapped[str] = mapped_column(String(50), default="collegiate", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="athlete_profile")
    injuries = relationship("InjuryHistory", back_populates="athlete", cascade="all, delete-orphan")
    training_profiles = relationship("TrainingProfile", back_populates="athlete", cascade="all, delete-orphan")
    assessments = relationship("PhysicalAssessment", back_populates="athlete", cascade="all, delete-orphan")
    coach_assignments = relationship(
        "CoachAthleteAssignment", back_populates="athlete", foreign_keys="CoachAthleteAssignment.athlete_id"
    )
    videos = relationship("Video", back_populates="athlete", cascade="all, delete-orphan")
