"""Auth service — business logic for register, login, refresh, logout."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.modules.auth.schemas import RegisterRequest
from app.modules.users.models import RefreshToken, User

logger = logging.getLogger(__name__)


async def register_user(db: AsyncSession, data: RegisterRequest) -> User:
    """Register a new user. Raises ValueError if email already exists."""
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none() is not None:
        raise ValueError("Email already registered")

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        role=data.role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    """Validate email + password. Returns User if valid, None if not."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None

    return user


async def create_token_pair(db: AsyncSession, user: User) -> tuple[str, str]:
    """Create an access token and a refresh token, store refresh token hash in DB."""
    access_token = create_access_token(user.id, user.role.value)
    raw_refresh_token = create_refresh_token()
    token_hash = hash_refresh_token(raw_refresh_token)

    refresh_token_record = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days),
    )
    db.add(refresh_token_record)
    await db.flush()

    return access_token, raw_refresh_token


async def refresh_access_token(db: AsyncSession, raw_refresh_token: str) -> tuple[str, str] | None:
    """Validate a refresh token, revoke it, and issue a new token pair.

    Returns (new_access_token, new_refresh_token) or None if invalid.
    Implements refresh token rotation — each refresh token is single-use.
    """
    token_hash = hash_refresh_token(raw_refresh_token)

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,  # noqa: E712
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
    )
    refresh_record = result.scalar_one_or_none()

    if refresh_record is None:
        return None

    # Revoke the used token (rotation)
    refresh_record.revoked = True
    await db.flush()

    # Load the user
    user_result = await db.execute(select(User).where(User.id == refresh_record.user_id))
    user = user_result.scalar_one_or_none()

    if user is None or not user.is_active:
        return None

    # Issue new pair
    return await create_token_pair(db, user)


async def revoke_refresh_token(db: AsyncSession, raw_refresh_token: str) -> bool:
    """Revoke a refresh token (logout). Returns True if token was found and revoked."""
    token_hash = hash_refresh_token(raw_refresh_token)

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,  # noqa: E712
        )
    )
    refresh_record = result.scalar_one_or_none()

    if refresh_record is None:
        return False

    refresh_record.revoked = True
    await db.flush()
    return True
