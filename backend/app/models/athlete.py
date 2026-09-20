from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base


class Athlete(Base):
    __tablename__ = "athletes"
    
    id = Column(Integer, primary_key=True, index=True)
    athlete_id = Column(String, unique=True, index=True, nullable=False)  # Public athlete identifier
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Optional link to user account
    sport_type = Column(String, nullable=False)
    position = Column(String, nullable=True)
    age = Column(Integer, nullable=False)
    height = Column(Float, nullable=False)  # in cm
    weight = Column(Float, nullable=False)  # in kg
    injury_history = Column(Text, nullable=True)
    training_load = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", backref="athletes")
