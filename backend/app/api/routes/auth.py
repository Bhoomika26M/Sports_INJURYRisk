from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.auth import (
    UserRegister, UserLogin, Token, 
    PasswordResetRequest, ResetPasswordOTP, ChangePasswordOTP,
    GoogleAuthorizeUrlResponse, GoogleCallbackRequest
)
from app.schemas.user import UserResponse
from app.services.auth_service import register_user, authenticate_user, create_user_token
from app.services.otp_service import (
    request_password_recovery_otp,
    verify_recovery_and_reset_password,
    request_password_change_otp,
    verify_change_password,
)
from app.services import google_auth_service as google_auth
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


@router.get("/google/authorize-url", response_model=GoogleAuthorizeUrlResponse)
def google_authorize_url(
    next: str = None,
    _: None = Depends(RateLimitDependency(max_requests=30, window_seconds=60)),
):
    """
    Get the Google consent-screen URL to redirect the browser to.

    - **next**: optional same-app path to return to after sign-in.

    Returns 503 until the server has Google credentials configured.
    """
    url, state = google_auth.build_authorization_url(next_url=next)
    return {"authorization_url": url, "state": state}


@router.post("/google/exchange", response_model=Token)
def google_exchange(
    payload: GoogleCallbackRequest,
    request: Request = None,
    db: Session = Depends(get_db),
    _: None = Depends(RateLimitDependency(max_requests=10, window_seconds=60)),
):
    """
    Exchange the Google authorization code for an application token.

    The browser obtains ``code`` + ``state`` at the configured redirect URI and
    posts them here. The server verifies the state, exchanges the code with
    Google (using the client secret), then returns the same JWT used by
    password login.
    """
    google_auth.verify_oauth_state(payload.state)
    ip_address = request.client.host if request else None
    user, _outcome = google_auth.authenticate_with_google(db, payload.code, ip_address)
    access_token = create_user_token(user, db)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/google/callback")
def google_callback(
    code: str,
    state: str,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    Server-side redirect callback (optional alternative to /google/exchange).

    Google can be pointed directly at this endpoint; it exchanges the code and
    then 302-redirects the browser to the configured frontend URL with the token
    in the fragment. Failures redirect to the frontend failure URL with an error
    code. Prefer /google/exchange with a frontend callback page if you would
    rather not put tokens in a URL.
    """
    from fastapi.responses import RedirectResponse
    from urllib.parse import urlencode

    ip_address = request.client.host if request else None
    try:
        google_auth.verify_oauth_state(state)
        user, _outcome = google_auth.authenticate_with_google(db, code, ip_address)
        token = create_user_token(user, db)
        fragment = urlencode({"access_token": token, "token_type": "bearer"})
        return RedirectResponse(f"{settings.GOOGLE_FRONTEND_SUCCESS_REDIRECT}#{fragment}")
    except HTTPException as exc:
        fragment = urlencode({"error": str(exc.detail)})
        return RedirectResponse(f"{settings.GOOGLE_FRONTEND_FAILURE_REDIRECT}#{fragment}")


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
    request: Request = None,
    db: Session = Depends(get_db),
    _: None = Depends(RateLimitDependency(max_requests=3, window_seconds=300))
):
    """
    Request a password-recovery OTP.

    - **email**: The account email address.

    Always returns the same generic response, whether or not an account exists,
    so the endpoint cannot be used to enumerate accounts. If an eligible account
    exists, a 6-digit code is emailed to it.
    """
    ip_address = request.client.host if request else None
    return request_password_recovery_otp(db, request_data.email, ip_address)


@router.post("/reset-password")
def reset_password_endpoint(
    reset_data: ResetPasswordOTP,
    request: Request = None,
    db: Session = Depends(get_db),
    _: None = Depends(RateLimitDependency(max_requests=5, window_seconds=300))
):
    """
    Reset a forgotten password using an emailed OTP.

    - **email**: The account email address.
    - **otp**: The 6-digit code from the email (a string; leading zeros count).
    - **new_password**: The new password.

    On success the OTP is consumed and all of the account's sessions are revoked.
    """
    ip_address = request.client.host if request else None
    return verify_recovery_and_reset_password(
        db, reset_data.email, reset_data.otp, reset_data.new_password, ip_address
    )


@router.post("/change-password/request-otp")
def change_password_request_otp(
    request: Request = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: None = Depends(RateLimitDependency(max_requests=5, window_seconds=300))
):
    """
    Request a password-change OTP for the authenticated user.

    The recipient is always the email on the authenticated account; the client
    cannot choose a different recipient. Subject to a resend cooldown.
    """
    ip_address = request.client.host if request else None
    return request_password_change_otp(db, current_user, ip_address)


@router.post("/change-password")
def change_password_endpoint(
    change_data: ChangePasswordOTP,
    request: Request = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: None = Depends(RateLimitDependency(max_requests=10, window_seconds=300))
):
    """
    Change the authenticated user's password.

    - **otp**: The 6-digit code emailed to the account.
    - **current_password**: The current password (required, in addition to the OTP).
    - **new_password**: The new password.

    The account is taken from the authenticated session. On success the OTP is
    consumed and all sessions (including the current one) are revoked, so the
    user must sign in again.
    """
    ip_address = request.client.host if request else None
    return verify_change_password(
        db,
        current_user,
        change_data.otp,
        change_data.current_password,
        change_data.new_password,
        ip_address,
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    Get current user information.
    
    Requires a valid JWT token in the Authorization header.
    """
    return current_user
