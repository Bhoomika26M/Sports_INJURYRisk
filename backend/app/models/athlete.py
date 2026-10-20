import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import User, utcnow


def new_athlete_code() -> str:
    return "ATH-" + uuid.uuid4().hex[:8].upper()


class Athlete(Base):
    __tablename__ = "athletes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), unique=True, nullable=True
    )
    athlete_code: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, default=new_athlete_code
    )
    full_name: Mapped[str] = mapped_column(String(255))
    sport_type: Mapped[str] = mapped_column(String(64))
    position: Mapped[str | None] = mapped_column(String(64), nullable=True)
    age: Mapped[int]
    height_cm: Mapped[float] = mapped_column(Float)
    weight_kg: Mapped[float] = mapped_column(Float)
    weekly_training_load: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User | None] = relationship()
    injuries: Mapped[list["InjuryRecord"]] = relationship(
        back_populates="athlete",
        cascade="all, delete-orphan",
        order_by="InjuryRecord.injury_date.desc()",
    )
    training_loads: Mapped[list["TrainingLoadEntry"]] = relationship(
        cascade="all, delete-orphan", order_by="TrainingLoadEntry.entry_date.desc()"
    )
    assessments: Mapped[list["PhysicalAssessment"]] = relationship(
        cascade="all, delete-orphan", order_by="PhysicalAssessment.assessed_at.desc()"
    )
    access: Mapped[list["AthleteAccess"]] = relationship(cascade="all, delete-orphan")


class InjuryRecord(Base):
    __tablename__ = "injury_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("athletes.id"), index=True)
    injury_type: Mapped[str] = mapped_column(String(120))
    body_part: Mapped[str] = mapped_column(String(64))
    injury_date: Mapped[date] = mapped_column(Date)
    severity: Mapped[str] = mapped_column(String(16), default="moderate")  # minor|moderate|severe
    status: Mapped[str] = mapped_column(String(16), default="recovered")  # active|recovering|recovered
    recovered_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    athlete: Mapped[Athlete] = relationship(back_populates="injuries")


class TrainingLoadEntry(Base):
    __tablename__ = "training_load_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("athletes.id"), index=True)
    entry_date: Mapped[date] = mapped_column(Date)
    duration_min: Mapped[float] = mapped_column(Float)
    rpe: Mapped[float] = mapped_column(Float)  # session RPE, 1-10
    load_au: Mapped[float] = mapped_column(Float)  # duration * rpe (arbitrary units)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class PhysicalAssessment(Base):
    __tablename__ = "physical_assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("athletes.id"), index=True)
    assessed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)


class AthleteAccess(Base):
    """Grants a coach / physiotherapist / sports scientist access to an athlete."""

    __tablename__ = "athlete_access"
    __table_args__ = (UniqueConstraint("athlete_id", "user_id", name="uq_athlete_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("athletes.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    access_role: Mapped[str] = mapped_column(String(32))

    user: Mapped[User] = relationship()
