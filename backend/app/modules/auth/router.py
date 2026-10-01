"""Auth router — register, login, refresh, logout, me, Google OAuth2."""

import logging
import secrets
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import get_current_user
from app.core.errors import api_error
from app.database import get_db
from app.modules.auth.schemas import (
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.modules.auth.cookies import (
    clear_oauth_state_cookie,
    clear_refresh_cookie,
    set_oauth_state_cookie,
    set_refresh_cookie,
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
from app.modules.users.models import User

logger = logging.getLogger(__name__)

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
    return MessageResponse(message="Logged out successfully")


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
    return resp


@router.get("/google", response_class=RedirectResponse, status_code=status.HTTP_302_FOUND)
async def google_login():
    """Start Google sign-in: 302 to Google's consent screen with a fresh CSRF ``state``.

    ``state`` is also set as a short-lived httpOnly cookie; the callback only proceeds when the two match.
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
    return resp


@router.get("/google/callback", response_class=RedirectResponse, status_code=status.HTTP_302_FOUND)
async def google_callback(
    db: Annotated[AsyncSession, Depends(get_db)],
    code: Annotated[str | None, Query(max_length=2048)] = None,
    state: Annotated[str | None, Query(max_length=512)] = None,
    error: Annotated[str | None, Query(max_length=256)] = None,
    oauth_state: Annotated[str | None, Cookie()] = None,
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
        _user, _access_token, refresh_token = await handle_google_callback(db, code, settings.google_redirect_uri)
    except OAuthError as e:
        return _login_error_redirect(e.code)

    resp = RedirectResponse(f"{settings.frontend_url}/auth/callback", status_code=status.HTTP_302_FOUND)
    set_refresh_cookie(resp, refresh_token)
    clear_oauth_state_cookie(resp)
    return resp


@router.get("/google/userinfo", response_model=UserResponse)
async def google_userinfo(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get current user info (for frontend to check Google linkage)."""
    return current_user