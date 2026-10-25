from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Body, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core import security
from app.core.config import settings
from app.schemas.user import UserCreate, UserResponse
from app.schemas.token import Token, OAuthLoginRequest, GoogleOAuthRequest
from app.services import user_service
from app.api.deps import get_current_active_user
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

router = APIRouter()

def set_auth_cookie(response: Response, access_token: str) -> None:
    """Sets a secure, HttpOnly cookie with the JWT access token for web session persistence."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False,  # Set to True when using HTTPS in production
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )

@router.post("/login", response_model=Token)
def login_access_token(
    response: Response,
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """OAuth2 compatible token login, get an access token for future requests."""
    user = user_service.authenticate_user(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.id, expires_delta=access_token_expires, role=user.role
    )
    set_auth_cookie(response, access_token)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/oauth/login", response_model=Token)
def oauth_login(
    *,
    response: Response,
    db: Session = Depends(get_db),
    oauth_in: OAuthLoginRequest
) -> Any:
    """OAuth2 / Social login (e.g., Google OAuth2). Authenticates or registers OAuth user."""
    user = user_service.authenticate_or_register_oauth(
        db,
        email=oauth_in.email,
        full_name=oauth_in.full_name,
        provider=oauth_in.provider,
        role=oauth_in.role
    )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.id, expires_delta=access_token_expires, role=user.role
    )
    set_auth_cookie(response, access_token)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/google", response_model=Token)
def google_authenticate(
    *,
    response: Response,
    db: Session = Depends(get_db),
    google_in: GoogleOAuthRequest
) -> Any:
    """
    Cryptographically verify real Google ID Token issued by Google Identity Services.
    Authenticates or provisions the user in PostgreSQL and returns an application JWT.
    """
    try:
        req = google_requests.Request()
        audience = settings.GOOGLE_CLIENT_ID if settings.GOOGLE_CLIENT_ID else None
        
        idinfo = id_token.verify_oauth2_token(
            google_in.credential,
            req,
            audience=audience
        )
        
        email = idinfo.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Google token does not contain an email address.")
            
        email_verified = idinfo.get("email_verified", False)
        if not email_verified:
            raise HTTPException(status_code=400, detail="Google account email is not verified.")
            
        google_id = idinfo.get("sub")
        if not google_id:
            raise HTTPException(status_code=400, detail="Google token does not contain a valid subject ID.")
            
        full_name = idinfo.get("name") or email.split("@")[0]
        
        user = user_service.authenticate_or_register_google(
            db=db,
            google_id=google_id,
            email=email,
            email_verified=email_verified,
            full_name=full_name,
            requested_role=google_in.role or "athlete",
            admin_code=getattr(google_in, "admin_code", None)
        )
    except HTTPException:
        raise
    except ValueError as e:
        error_msg = str(e)
        if "already associated" in error_msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error_msg)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Google token verification failed: {error_msg}")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google authentication error: {str(e)}"
        )
        
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user account.")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.id, expires_delta=access_token_expires, role=user.role
    )
    set_auth_cookie(response, access_token)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/register", response_model=UserResponse)
def register(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate,
) -> Any:
    """Register a new user with support for roles (Athlete, Coach, Physiotherapist, Sports Scientist, Administrator)."""
    user = user_service.get_user_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    user = user_service.create_user(db, user_in=user_in)
    return user

@router.get("/verify", response_model=UserResponse)
def verify_token(
    current_user: Any = Depends(get_current_active_user)
) -> Any:
    """Verify JWT token and return active user profile."""
    return current_user

@router.post("/logout")
def logout(response: Response) -> Any:
    """Logout (Server clears HttpOnly cookie, client clears state)."""
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        samesite="lax"
    )
    return {"message": "Successfully logged out"}
