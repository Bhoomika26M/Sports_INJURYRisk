import uuid
from datetime import date, datetime
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import AnatomicalSide, InjuryType


class InjuryHistory(Base):
    __tablename__ = "injury_history"
    __table_args__ = (
        Index("idx_injury_history_athlete_id", "athlete_id"),
        Index("idx_injury_history_type", "injury_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    athlete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False
    )
    injury_type: Mapped[InjuryType] = mapped_column(
        Enum(InjuryType, name="injury_type_enum", native_enum=True, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    anatomical_side: Mapped[AnatomicalSide] = mapped_column(
        Enum(AnatomicalSide, name="anatomical_side_enum", native_enum=True, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    diagnosis_details: Mapped[str | None] = mapped_column(String(255), nullable=True)
    injury_date: Mapped[date] = mapped_column(Date, nullable=False)
    severity_grade: Mapped[str | None] = mapped_column(String(20), nullable=True)
    surgical_intervention: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    return_to_play_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    fully_resolved: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    clinical_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship
    athlete = relationship("Athlete", back_populates="injuries")
