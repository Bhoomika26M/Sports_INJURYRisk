"""Auth router — register, login, refresh, logout, me, Google OAuth2."""

import logging
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import get_current_user
from app.core.errors import api_error
from app.core.security import hash_password, verify_password
from app.database import get_db
from app.modules.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from app.modules.auth.cookies import (
    clear_oauth_role_cookie,
    clear_oauth_state_cookie,
    clear_refresh_cookie,
    clear_session_hint_cookie,
    set_oauth_role_cookie,
    set_oauth_state_cookie,
    set_refresh_cookie,
    set_session_hint_cookie,
)
from app.modules.auth.service import (
    OAuthError,
    authenticate_user,
    create_token_pair,
    handle_google_callback,
    register_user,
    refresh_access_token,
    revoke_refresh_token,
)
from app.modules.users.models import PasswordResetOtp, RefreshToken, User

logger = logging.getLogger(__name__)

# In-process rate limiting map: key -> list of timestamp epochs
_rate_limits: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(key: str, max_calls: int = 5, window_sec: float = 300.0) -> bool:
    """Sliding-window rate limiter in process memory."""
    now = time.time()
    cutoff = now - window_sec
    calls = [t for t in _rate_limits[key] if t > cutoff]
    if len(calls) >= max_calls:
        _rate_limits[key] = calls
        return False
    calls.append(now)
    _rate_limits[key] = calls
    return True


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Register a new user."""
    try:
        user = await register_user(db, data.email, data.password, data.full_name, data.role)
    except ValueError:
        raise api_error(409, "DUPLICATE_EMAIL", "Email already registered")
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Authenticate user and return access token. Refresh token set as httpOnly cookie."""
    user = await authenticate_user(db, data.email, data.password)
    if user is None:
        raise api_error(401, "INVALID_CREDENTIALS", "Invalid email or password")

    access_token, refresh_token = await create_token_pair(db, user)

    # Refresh token only ever travels as an httpOnly cookie — never in the response body
    set_refresh_cookie(response, refresh_token)

    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    refresh_token: Annotated[str | None, Cookie()] = None,
):
    """Refresh access token using the refresh token from the httpOnly cookie."""
    if refresh_token is None:
        raise api_error(401, "NO_REFRESH_TOKEN", "No refresh token provided")

    result = await refresh_access_token(db, refresh_token)
    if result is None:
        raise api_error(401, "INVALID_REFRESH_TOKEN", "Invalid or expired refresh token")

    new_access_token, new_refresh_token = result

    set_refresh_cookie(response, new_refresh_token)

    return TokenResponse(access_token=new_access_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    refresh_token: Annotated[str | None, Cookie()] = None,
):
    """Logout — revoke the refresh token and clear the cookie."""
    if refresh_token:
        await revoke_refresh_token(db, refresh_token)

    clear_refresh_cookie(response)
    clear_session_hint_cookie(response)
    return MessageResponse(message="Logged out successfully")


@router.post("/password/forgot", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password_endpoint(
    data: ForgotPasswordRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Request a password reset OTP by email.

    Always returns 202 with identical body to prevent user enumeration attacks.
    """
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(f"forgot_{client_ip}", max_calls=5, window_sec=300.0):
        raise api_error(429, "RATE_LIMIT_EXCEEDED", "Too many requests. Please wait a few minutes.")

    user = await db.scalar(select(User).where(User.email == data.email.lower().strip()))
    if user and user.is_active:
        code = f"{secrets.randbelow(1_000_000):06d}"
        code_hash = hash_password(code)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        otp = PasswordResetOtp(
            user_id=user.id,
            code_hash=code_hash,
            expires_at=expires_at,
            attempts=0,
        )
        db.add(otp)
        await db.commit()

        # In development or when SendGrid is absent, log OTP to console
        logger.info("[AUTH_OTP] Password reset OTP for %s: %s (expires in 10m)", user.email, code)

        if settings.sendgrid_api_key:
            try:
                from sendgrid import SendGridAPIClient
                from sendgrid.helpers.mail import Mail
                message = Mail(
                    from_email=settings.sendgrid_from_email,
                    to_emails=user.email,
                    subject="Your Sports Injury Risk Platform Reset Code",
                    plain_text_content=f"Your verification code is: {code}\n\nThis code expires in 10 minutes.",
                )
                sg = SendGridAPIClient(settings.sendgrid_api_key)
                sg.send(message)
            except Exception as e:
                logger.warning("SendGrid dispatch failed: %s", e)

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"message": "If that email address is registered, a password reset code has been sent."},
    )


@router.post("/password/reset", response_model=MessageResponse)
async def reset_password_endpoint(
    data: ResetPasswordRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Verify OTP and reset password. Revokes all active refresh tokens on success."""
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(f"reset_{client_ip}", max_calls=10, window_sec=300.0):
        raise api_error(429, "RATE_LIMIT_EXCEEDED", "Too many reset attempts. Please wait a few minutes.")

    user = await db.scalar(select(User).where(User.email == data.email.lower().strip()))
    if not user:
        raise api_error(400, "INVALID_CODE", "Invalid or expired reset code")

    now = datetime.now(timezone.utc)
    stmt = (
        select(PasswordResetOtp)
        .where(
            PasswordResetOtp.user_id == user.id,
            PasswordResetOtp.used_at.is_(None),
            PasswordResetOtp.expires_at > now,
        )
        .order_by(PasswordResetOtp.created_at.desc())
    )
    otp = await db.scalar(stmt)
    if not otp:
        raise api_error(400, "INVALID_CODE", "Invalid or expired reset code")

    if otp.attempts >= 5:
        raise api_error(429, "TOO_MANY_ATTEMPTS", "Too many failed attempts. Please request a new code.")

    if not verify_password(data.code, otp.code_hash):
        otp.attempts += 1
        await db.commit()
        raise api_error(400, "INVALID_CODE", "Invalid or expired reset code")

    # Code is valid! Mark used, update password, and revoke refresh tokens
    otp.used_at = now
    user.password_hash = hash_password(data.new_password)
    await db.execute(
        update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True)
    )
    await db.commit()

    return MessageResponse(message="Password reset successful. Please log in with your new password.")


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get current authenticated user."""
    return current_user


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"


def _login_error_redirect(code: str) -> RedirectResponse:
    """Browser-facing failure: back to the login page with a stable error code (no provider text)."""
    logger.warning("google oauth rejected: %s", code)
    resp = RedirectResponse(f"{settings.frontend_url}/login?{urlencode({'error': code})}", status_code=status.HTTP_302_FOUND)
    clear_oauth_state_cookie(resp)
    clear_oauth_role_cookie(resp)
    clear_session_hint_cookie(resp)
    return resp


@router.get("/google", response_class=RedirectResponse, status_code=status.HTTP_302_FOUND)
async def google_login(
    role: Annotated[str | None, Query(max_length=50)] = None,
):
    """Start Google sign-in: 302 to Google's consent screen with a fresh CSRF ``state``.

    ``state`` is also set as a short-lived httpOnly cookie; the callback only proceeds when the two match.
    If a self-service signup role was selected (e.g. coach, athlete, physio), it is held in a short-lived
    httpOnly cookie so newly provisioned accounts take that role.
    """
    if not settings.google_client_id or not settings.google_client_secret:
        raise api_error(503, "OAUTH_NOT_CONFIGURED", "Google sign-in is not configured on this server")

    state = secrets.token_urlsafe(32)
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    resp = RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}", status_code=status.HTTP_302_FOUND)
    set_oauth_state_cookie(resp, state)
    if role:
        set_oauth_role_cookie(resp, role)
    else:
        clear_oauth_role_cookie(resp)
    return resp


@router.get("/google/callback", response_class=RedirectResponse, status_code=status.HTTP_302_FOUND)
async def google_callback(
    db: Annotated[AsyncSession, Depends(get_db)],
    code: Annotated[str | None, Query(max_length=2048)] = None,
    state: Annotated[str | None, Query(max_length=512)] = None,
    error: Annotated[str | None, Query(max_length=256)] = None,
    oauth_state: Annotated[str | None, Cookie()] = None,
    oauth_role: Annotated[str | None, Cookie()] = None,
):
    """Google redirects the BROWSER here with ``?code=...&state=...`` (authorization-code flow).

    Order matters: ``state`` is validated before anything else, including before acting on ``error``.
    On success the refresh token is set as an httpOnly cookie on this redirect and the browser lands on
    the frontend callback page, which obtains the in-memory access token via POST /auth/refresh.
    Nothing secret ever appears in a URL.
    """
    if not state or not oauth_state or not secrets.compare_digest(state, oauth_state):
        return _login_error_redirect("oauth_state_mismatch")
    if error:
        return _login_error_redirect("oauth_denied")
    if not code:
        return _login_error_redirect("oauth_missing_code")

    try:
        _user, _access_token, refresh_token = await handle_google_callback(
            db, code, settings.google_redirect_uri, role=oauth_role
        )
    except OAuthError as e:
        return _login_error_redirect(e.code)

    resp = RedirectResponse(f"{settings.frontend_url}/auth/callback", status_code=status.HTTP_302_FOUND)
    set_refresh_cookie(resp, refresh_token)
    set_session_hint_cookie(resp)
    clear_oauth_state_cookie(resp)
    clear_oauth_role_cookie(resp)
    return resp


@router.get("/google/userinfo", response_model=UserResponse)
async def google_userinfo(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get current user info (for frontend to check Google linkage)."""
    return current_user