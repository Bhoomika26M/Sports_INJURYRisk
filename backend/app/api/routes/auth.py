from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.auth import (
    UserRegister, UserLogin, Token, 
    PasswordResetRequest, PasswordReset, PasswordChange
)
from app.schemas.user import UserResponse
from app.services.auth_service import register_user, authenticate_user, create_user_token
from app.services.password_reset_service import (
    request_password_reset, 
    reset_password, 
    change_password
)
from app.core.security import get_current_active_user, revoke_session
from app.core.rate_limit import RateLimitDependency
from app.core.audit import log_logout
from app.models.user import User
from jose import jwt
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserRegister, 
    db: Session = Depends(get_db),
    request: Request = None,
    _: None = Depends(RateLimitDependency(max_requests=5, window_seconds=300))
):
    """
    Register a new user.
    
    - **email**: User's email address (must be unique)
    - **password**: User's password
    - **full_name**: User's full name
    - **role**: User's role (public registration only allows 'athlete')
    """
    user = register_user(db, user_data, request)
    return user


@router.post("/login", response_model=Token)
def login(
    user_data: UserLogin, 
    db: Session = Depends(get_db),
    request: Request = None,
    _: None = Depends(RateLimitDependency(max_requests=10, window_seconds=60))
):
    """
    Login with email and password to get access token.
    
    - **email**: User's email address
    - **password**: User's password
    
    Returns a JWT access token that should be used in the Authorization header for subsequent requests.
    """
    user = authenticate_user(db, user_data, request)
    access_token = create_user_token(user, db)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
def logout(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Logout current user and invalidate session.
    
    Requires a valid JWT token. The session will be revoked server-side.
    """
    # Extract token from Authorization header
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            jti = payload.get("jti")
            if jti:
                revoke_session(db, jti)
        except:
            pass  # If token parsing fails, just proceed
    
    # Log logout
    ip_address = request.client.host if request else None
    log_logout(current_user, ip_address)
    
    return {"message": "Successfully logged out"}


@router.post("/forgot-password")
def forgot_password(
    request_data: PasswordResetRequest,
    db: Session = Depends(get_db),
    _: None = Depends(RateLimitDependency(max_requests=3, window_seconds=300))
):
    """
    Request a password reset.
    
    - **email**: User's email address
    
    For security reasons, this endpoint always returns the same response
    regardless of whether the email exists in the system.
    """
    return request_password_reset(db, request_data.email)


@router.post("/reset-password")
def reset_password_endpoint(
    reset_data: PasswordReset,
    db: Session = Depends(get_db),
    _: None = Depends(RateLimitDependency(max_requests=5, window_seconds=300))
):
    """
    Reset password using a valid reset token.
    
    - **token**: Password reset token (received via email)
    - **new_password**: New password
    - **confirm_password**: Confirm new password
    """
    return reset_password(db, reset_data.token, reset_data.new_password)


@router.post("/change-password")
def change_password_endpoint(
    change_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Change password for authenticated user.
    
    - **current_password**: Current password
    - **new_password**: New password
    - **confirm_password**: Confirm new password
    
    After successful password change, all existing sessions will be invalidated.
    """
    return change_password(db, current_user, change_data.current_password, change_data.new_password)


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    Get current user information.
    
    Requires a valid JWT token in the Authorization header.
    """
    return current_user
