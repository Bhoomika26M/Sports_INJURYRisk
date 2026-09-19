import uuid
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PhysicalAssessment(Base):
    __tablename__ = "physical_assessments"
    __table_args__ = (
        Index("idx_assessments_athlete_id", "athlete_id"),
        Index("idx_assessments_assessor_id", "assessor_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    athlete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False
    )
    assessor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    assessment_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    assessment_type: Mapped[str] = mapped_column(
        String(80), default="pre_season_baseline", nullable=False
    )
    weight_at_assessment_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    ankle_dorsiflexion_left_cm: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)
    ankle_dorsiflexion_right_cm: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)
    single_leg_hop_left_cm: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    single_leg_hop_right_cm: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    y_balance_composite_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    clinical_observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    athlete = relationship("Athlete", back_populates="assessments")
    assessor = relationship("User", back_populates="conducted_assessments", foreign_keys=[assessor_id])
    videos = relationship("Video", back_populates="assessment")
