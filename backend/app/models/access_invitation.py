from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.db.base import Base


class AccessInvitation(Base):
    """
    Invitation / access grant between an Athlete and a professional user
    (coach, physiotherapist, sports_scientist, etc.).
    
    Status workflow:
      - 'pending': Sent by athlete, awaiting response from the professional.
      - 'accepted': Professional accepted, granted access to athlete profile & videos.
      - 'rejected': Professional declined.
      - 'revoked': Athlete revoked access.
    """
    __tablename__ = "access_invitations"

    id = Column(Integer, primary_key=True, index=True)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False, index=True)
    professional_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String, default="pending", nullable=False, index=True)  # pending, accepted, rejected, revoked
    invited_role = Column(String, nullable=True)  # coach, physiotherapist, etc.
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
