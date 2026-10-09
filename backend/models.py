from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String) # Athlete, Coach, Physiotherapist, Sports Scientist, Administrator
    
    athlete_profile = relationship("AthleteProfile", back_populates="user", uselist=False)

class AthleteProfile(Base):
    __tablename__ = "athlete_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    sport_type = Column(String)
    position = Column(String)
    age = Column(Integer)
    height = Column(Float)
    weight = Column(Float)
    injury_history = Column(String)
    training_load = Column(String)

    user = relationship("User", back_populates="athlete_profile")

class PhysicalAssessment(Base):
    __tablename__ = "physical_assessments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(String)
    test_name = Column(String)
    score = Column(Float)
    notes = Column(String)

    user = relationship("User")

class PerformanceRecord(Base):
    __tablename__ = "performance_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(String)
    metric = Column(String)
    value = Column(Float)
    unit = Column(String)

    user = relationship("User")

class VideoAnalysis(Base):
    __tablename__ = "video_analyses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    activity = Column(String)
    surface_type = Column(String)
    footwear = Column(String)
    rpe = Column(Integer)
    sleep_quality = Column(Integer)
    risk_score = Column(Float)
    risk_level = Column(String)
    injury_probabilities = Column(String)
    corrective_recommendation = Column(String)
    created_at = Column(String)

    user = relationship("User")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    message = Column(String)
    type = Column(String) # alert, warning, info
    is_read = Column(Integer, default=0)
    created_at = Column(String)

    user = relationship("User")
