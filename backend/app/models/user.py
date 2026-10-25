import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

class UserRole(str, enum.Enum):
    ATHLETE = "athlete"
    COACH = "coach"
    PHYSIOTHERAPIST = "physiotherapist"
    SPORTS_SCIENTIST = "sports_scientist"
    ADMINISTRATOR = "administrator"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, index=True)
    role = Column(String, default=UserRole.ATHLETE.value) # athlete, coach, physiotherapist, sports_scientist, administrator
    is_active = Column(Boolean, default=True)
    auth_provider = Column(String, default="local", nullable=True) # local, google, or both
    google_id = Column(String, unique=True, index=True, nullable=True)
    bio = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    organization = Column(String, nullable=True)
    specialization = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    athlete_profile = relationship("AthleteProfile", back_populates="user", uselist=False)
