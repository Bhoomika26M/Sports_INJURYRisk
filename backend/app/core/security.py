"""JWT encoding/decoding and password hashing."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

from app.config import settings

ph = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a password using Argon2."""
    return ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    try:
        ph.verify(password_hash, password)
        return True
    except VerificationError:
        return False


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"sub": subject, "exp": expire, "type": "access"}
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str) -> tuple[str, str]:
    """Create a JWT refresh token and return (token, token_hash)."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_password(raw_token)
    to_encode = {"sub": subject, "exp": expire, "type": "refresh", "jti": token_hash}
    encoded = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded, token_hash


def decode_access_token(token: str) -> dict:
    """Decode and validate an access token."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "access":
            raise jwt.PyJWTError("Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise jwt.PyJWTError("Token expired")
    except jwt.PyJWTError:
        raise


def decode_refresh_token(token: str) -> dict:
    """Decode and validate a refresh token."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "refresh":
            raise jwt.PyJWTError("Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise jwt.PyJWTError("Token expired")
    except jwt.PyJWTError:
        raise


def generate_state_token() -> str:
    """Generate a secure random state token for OAuth2."""
    return secrets.token_urlsafe(32)