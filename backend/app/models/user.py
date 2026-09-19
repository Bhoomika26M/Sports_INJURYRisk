import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import UserRole


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    # Nullable: Google-SSO users have no password
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role_enum", native_enum=True, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=UserRole.ATHLETE,
    )
    phone_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # OAuth fields
    google_id: Mapped[str | None] = mapped_column(
        String(128), unique=True, index=True, nullable=True
    )
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    athlete_profile = relationship(
        "Athlete", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    coach_assignments = relationship(
        "CoachAthleteAssignment", back_populates="coach", foreign_keys="CoachAthleteAssignment.coach_id"
    )
    conducted_assessments = relationship(
        "PhysicalAssessment", back_populates="assessor", foreign_keys="PhysicalAssessment.assessor_id"
    )
    uploaded_videos = relationship(
        "Video", back_populates="uploaded_by_user", foreign_keys="Video.uploaded_by_user_id"
    )

    # ── helpers ──────────────────────────────────────────────────────────────
    @property
    def is_oauth_user(self) -> bool:
        """True when the account was created via an OAuth provider."""
        return self.hashed_password is None
