from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

class AthleteProfile(Base):
    __tablename__ = "athlete_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    sport_type = Column(String, index=True)
    position = Column(String)
    age = Column(Integer)
    height_cm = Column(Float)
    weight_kg = Column(Float)
    
    # JSON columns for flexible data structures
    injury_history = Column(JSON, default=list)
    training_load = Column(JSON, default=dict)
    physical_assessments = Column(JSON, default=list)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Persistent Assigned Coach
    coach_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # Relationships
    user = relationship("User", back_populates="athlete_profile", foreign_keys=[user_id])
    assigned_coach = relationship("User", foreign_keys=[coach_id])
    assignments = relationship("AthleteAssignment", back_populates="athlete", cascade="all, delete-orphan")

    @property
    def name(self) -> str:
        if self.user and self.user.full_name:
            return self.user.full_name
        if self.user and self.user.email:
            return self.user.email.split("@")[0].title()
        return f"Athlete #{self.id}"

    @property
    def assigned_staff(self) -> list:
        staff_list = []
        # If coach_id is set, ensure it's in the assigned staff list
        if self.assigned_coach:
            staff_list.append({
                "id": self.assigned_coach.id,
                "full_name": self.assigned_coach.full_name or self.assigned_coach.email.split("@")[0].title(),
                "email": self.assigned_coach.email,
                "role": self.assigned_coach.role,
                "organization": getattr(self.assigned_coach, "organization", None),
                "specialization": getattr(self.assigned_coach, "specialization", None),
            })
        if self.assignments:
            for a in self.assignments:
                if a.staff and not any(s["id"] == a.staff.id for s in staff_list):
                    staff_list.append({
                        "id": a.staff.id,
                        "full_name": a.staff.full_name or a.staff.email.split("@")[0].title(),
                        "email": a.staff.email,
                        "role": a.staff.role,
                        "organization": getattr(a.staff, "organization", None),
                        "specialization": getattr(a.staff, "specialization", None),
                    })
        return staff_list

    @property
    def coach(self) -> dict | None:
        if self.assigned_coach:
            return {
                "id": self.assigned_coach.id,
                "full_name": self.assigned_coach.full_name or self.assigned_coach.email.split("@")[0].title(),
                "email": self.assigned_coach.email,
                "role": self.assigned_coach.role,
                "organization": getattr(self.assigned_coach, "organization", None),
                "specialization": getattr(self.assigned_coach, "specialization", None),
            }
        for staff in self.assigned_staff:
            if staff.get("role") == "coach":
                return staff
        return None

    @property
    def physiotherapist(self) -> dict | None:
        for staff in self.assigned_staff:
            if staff.get("role") == "physiotherapist":
                return staff
        return None
