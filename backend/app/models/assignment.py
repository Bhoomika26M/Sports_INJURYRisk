from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

class AthleteAssignment(Base):
    """
    Defines the assignment policy associating an athlete profile with a staff member
    (e.g., Coach, Physiotherapist, Sports Scientist).
    """
    __tablename__ = "athlete_assignments"

    id = Column(Integer, primary_key=True, index=True)
    athlete_id = Column(Integer, ForeignKey("athlete_profiles.id"), nullable=False)
    staff_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    athlete = relationship("AthleteProfile", back_populates="assignments")
    staff = relationship("User")
