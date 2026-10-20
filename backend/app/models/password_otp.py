from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.db.base import Base


class PasswordOTP(Base):
    """
    A purpose-scoped, single-use, expiring email OTP.

    Only a keyed HMAC digest of the code is stored (see app/core/otp.py); the
    raw code never touches the database. Outstanding codes for the same account
    and purpose are invalidated whenever a new one is issued.
    """

    __tablename__ = "password_otps"

    id = Column(Integer, primary_key=True, index=True)
    # Nullable only to allow future privacy-preserving flows where the account
    # is unknown; current flows always set it.
    user_id = Column(Integer, nullable=True, index=True)
    # "password_recovery" or "password_change"
    purpose = Column(String, nullable=False, index=True)
    otp_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    attempt_count = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=5, nullable=False)
    used_at = Column(DateTime, nullable=True)
    invalidated_at = Column(DateTime, nullable=True)
