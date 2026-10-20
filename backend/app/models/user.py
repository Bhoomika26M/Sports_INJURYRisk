from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from datetime import datetime
from app.db.base import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False)  # athlete, coach, physiotherapist, sports_scientist, administrator
    is_active = Column(Boolean, default=True)
    # Federated identity (e.g. Google Sign-In). Null for password-only accounts.
    # oauth_subject is the provider's stable user id ("sub"), not the email.
    oauth_provider = Column(String, nullable=True, index=True)
    oauth_subject = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
