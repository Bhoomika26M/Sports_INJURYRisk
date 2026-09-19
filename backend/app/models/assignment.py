import uuid
from datetime import date, datetime
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CoachAthleteAssignment(Base):
    __tablename__ = "coach_athlete_assignments"
    __table_args__ = (
        UniqueConstraint("coach_id", "athlete_id", "assignment_role", name="uq_coach_athlete_role"),
        Index("idx_coach_athlete_coach_id", "coach_id"),
        Index("idx_coach_athlete_athlete_id", "athlete_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    coach_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    athlete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False
    )
    assignment_role: Mapped[str] = mapped_column(
        String(50), default="head_coach", nullable=False
    )
    assigned_at: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    coach = relationship("User", foreign_keys=[coach_id], back_populates="coach_assignments")
    athlete = relationship("Athlete", foreign_keys=[athlete_id], back_populates="coach_assignments")
