"""Auth router — register, login, refresh, logout, me, Google OAuth2."""

import logging
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import get_current_user
from app.core.errors import api_error
from app.database import get_db
from app.modules.auth.schemas import (
    GoogleLoginRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.modules.auth.service import (
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

    # Set refresh token as httpOnly cookie — never in the response body
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
        path="/api/v1/auth",
    )

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

    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
        path="/api/v1/auth",
    )

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

    response.delete_cookie(key="refresh_token", path="/api/v1/auth")
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get current authenticated user."""
    return current_user


@router.get("/google")
async def google_login():
    """Redirect to Google OAuth2 consent screen."""
    from urllib.parse import urlencode

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return {"url": url}


@router.post("/google/callback", response_model=TokenResponse)
async def google_callback(
    data: GoogleLoginRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Handle Google OAuth2 callback, create/get user, return tokens."""
    user, access_token, refresh_token = await handle_google_callback(db, data.code, data.redirect_uri)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
        path="/api/v1/auth",
    )

    return TokenResponse(access_token=access_token)


@router.get("/google/userinfo", response_model=UserResponse)
async def google_userinfo(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get current user info (for frontend to check Google linkage)."""
    return current_user