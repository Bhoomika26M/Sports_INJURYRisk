from sqlalchemy import Column, Integer, String, Float, Text, DateTime, JSON
from datetime import datetime
from app.database import Base

class Athlete(Base):
    __tablename__ = "athletes"

    id = Column(Integer, primary_key=True, index=True)
    athlete_code = Column(String(50), unique=True, index=True, nullable=False) # e.g. ATH-101
    name = Column(String(255), nullable=False)
    sport_type = Column(String(100), nullable=False) # Football, Basketball, Track & Field, Tennis, etc.
    position = Column(String(100), nullable=True) # Striker, Point Guard, Sprinter, etc.
    age = Column(Integer, nullable=False)
    height = Column(Float, nullable=False) # in cm
    weight = Column(Float, nullable=False) # in kg
    injury_history = Column(JSON, default=list) # List of past injury records
    training_load = Column(Float, default=12.0) # Hours per week
    acwr = Column(Float, default=1.15) # Acute-to-Chronic Workload Ratio
    physical_assessment = Column(JSON, default=dict) # Assessment metrics: flexibility, VO2max, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
