"""Auth service — register, login, refresh, logout, OAuth2."""

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.modules.auth.schemas import GoogleUserInfo
from app.modules.users.models import RefreshToken, User, UserRole

logger = logging.getLogger(__name__)


async def register_user(db: AsyncSession, email: str, password: str, full_name: str, role: str) -> User:
    """Register a new user."""
    existing = await db.scalar(select(User).where(User.email == email))
    if existing:
        raise ValueError("Email already registered")

    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        role=UserRole(role),
    )
    db.add(user)
    await db.flush()

    # Create default notification preferences
    from app.modules.users.models import NotificationPreference
    for ntype in ["high_risk_flag", "insufficient_baseline", "processing_failed", "training_load_spike", "assessment_due"]:
        db.add(NotificationPreference(user_id=user.id, notification_type=ntype))

    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    """Authenticate user with email and password."""
    user = await db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user


async def create_token_pair(db: AsyncSession, user: User) -> tuple[str, str]:
    """Create access + refresh token pair, store refresh token hash."""
    access_token = create_access_token(user.id)
    refresh_token, token_hash = create_refresh_token(user.id)

    from datetime import timedelta

    rt = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(rt)
    await db.commit()
    return access_token, refresh_token


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> Optional[tuple[str, str]]:
    """Refresh access token using refresh token (rotation)."""
    try:
        payload = decode_refresh_token(refresh_token)
    except Exception:
        return None

    user_id = payload.get("sub")
    jti = payload.get("jti")
    if not user_id or not jti:
        return None

    # Find and validate refresh token
    result = await db.execute(select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.token_hash == jti))
    rt = result.scalar_one_or_none()
    if not rt or rt.revoked or rt.expires_at < datetime.now(timezone.utc):
        return None

    # Rotate: revoke old, create new
    rt.revoked = True
    new_access, new_refresh = await create_token_pair(db, await db.get(User, user_id))
    return new_access, new_refresh


async def revoke_refresh_token(db: AsyncSession, refresh_token: str) -> None:
    """Revoke a refresh token."""
    try:
        payload = decode_refresh_token(refresh_token)
        jti = payload.get("jti")
        if jti:
            await db.execute(
                RefreshToken.__table__.update()
                .where(RefreshToken.token_hash == jti)
                .values(revoked=True)
            )
            await db.commit()
    except Exception:
        pass  # Best effort


class OAuthError(Exception):
    """A Google sign-in failure that is safe to show the user. ``code`` is a stable machine value."""

    def __init__(self, code: str, message: str):
        self.code, self.message = code, message
        super().__init__(f"{code}: {message}")


GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


async def get_google_user_info(access_token: str) -> GoogleUserInfo:
    """Fetch user info from Google using the Google access token."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}, timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
        return GoogleUserInfo(
            sub=data["sub"],
            email=data["email"],
            name=data.get("name"),
            picture=data.get("picture"),
            email_verified=data.get("email_verified", False),
        )
    except httpx.HTTPStatusError as e:
        raise OAuthError("oauth_userinfo_failed", "Google rejected the profile request") from e
    except (httpx.RequestError, KeyError, ValueError) as e:
        raise OAuthError("oauth_provider_unavailable", "Could not read the Google profile") from e


async def exchange_google_code(code: str, redirect_uri: str) -> str:
    """Exchange an authorization code for a Google access token. Single-use, short-lived codes mean an
    expired/replayed/forged code fails here as ``oauth_code_invalid``."""
    from app.config import settings

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json()["access_token"]
    except httpx.HTTPStatusError as e:
        raise OAuthError("oauth_code_invalid", "The Google sign-in code was rejected or has expired") from e
    except (httpx.RequestError, KeyError, ValueError) as e:
        raise OAuthError("oauth_provider_unavailable", "Could not reach Google") from e


async def handle_google_callback(db: AsyncSession, code: str, redirect_uri: str) -> tuple[User, str, str]:
    """Exchange Google auth code, find/link/create the user, return user + token pair.

    Account linking is unchanged (google_id first, then email), with three guards that an
    unauthenticated sign-in path needs:
      * Google must assert the email is verified -- otherwise anyone could claim an existing
        password account by registering its address at an IdP that does not verify it.
      * An account already linked to a DIFFERENT Google subject is never silently re-used.
      * Deactivated accounts cannot sign in this way either.
    """
    google_access_token = await exchange_google_code(code, redirect_uri)
    google_user = await get_google_user_info(google_access_token)

    if not google_user.email_verified:
        raise OAuthError("oauth_email_unverified", "Your Google account email is not verified")

    user = await db.scalar(select(User).where(User.google_id == google_user.sub))
    if not user:
        user = await db.scalar(select(User).where(User.email == google_user.email))

    if user:
        if user.google_id and user.google_id != google_user.sub:
            raise OAuthError("oauth_account_conflict", "This email is linked to a different Google account")
        if not user.is_active:
            raise OAuthError("oauth_account_disabled", "This account is deactivated")
        if not user.google_id:
            user.google_id = google_user.sub
            user.avatar_url = google_user.picture
            await db.commit()
            await db.refresh(user)
    else:
        user = User(
            email=google_user.email,
            password_hash="",
            full_name=google_user.name or google_user.email.split("@")[0],
            role=UserRole.athlete,
            google_id=google_user.sub,
            avatar_url=google_user.picture,
        )
        db.add(user)
        await db.flush()

        # Default notification prefs
        from app.modules.users.models import NotificationPreference
        for ntype in ["high_risk_flag", "insufficient_baseline", "processing_failed", "training_load_spike", "assessment_due"]:
            db.add(NotificationPreference(user_id=user.id, notification_type=ntype))

        await db.commit()
        await db.refresh(user)

    access_token, refresh_token = await create_token_pair(db, user)
    return user, access_token, refresh_token
