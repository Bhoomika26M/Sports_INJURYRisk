"""Deprecated: the token-link password reset flow.

This module implemented the original emailed reset *link* flow. It has been
replaced by the email OTP workflows in ``app/services/otp_service.py`` (see
``POST /api/v1/auth/forgot-password`` and ``/reset-password``). It is retained,
unused, so the historical ``password_resets`` table and its data stay valid;
new code should use the OTP service. Do not wire these functions into routes.
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.password_reset import PasswordReset
from app.core.security import get_password_hash, verify_password, revoke_all_user_sessions
from app.core.email import email_service


def generate_reset_token() -> str:
    """Generate a cryptographically secure random reset token."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hash a reset token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def request_password_reset(db: Session, email: str) -> dict:
    """
    Request a password reset.
    
    Always returns the same generic response to prevent account enumeration.
    """
    # Find user by email
    user = db.query(User).filter(User.email == email).first()
    
    if user:
        # Generate secure reset token
        token = generate_reset_token()
        token_hash = hash_token(token)
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        # Create password reset record
        password_reset = PasswordReset(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at
        )
        db.add(password_reset)
        db.commit()
        
        # Generate reset link
        reset_link = f"http://localhost:5173/reset-password?token={token}"
        
        # Send email
        email_service.send_password_reset(user.email, reset_link, user.full_name)
    
    # Always return the same generic response
    return {
        "message": "If an account exists for this email, password reset instructions have been sent."
    }


def reset_password(db: Session, token: str, new_password: str) -> dict:
    """
    Reset password using a valid reset token.
    """
    # Hash the token to match stored hash
    token_hash = hash_token(token)
    
    # Find valid, unused reset token
    password_resets = db.query(PasswordReset).filter(
        PasswordReset.token_hash == token_hash
    ).all()
    
    password_reset = None
    for pr in password_resets:
        if pr.used_at is None and pr.expires_at > datetime.utcnow():
            password_reset = pr
            break
    
    if not password_reset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Get user
    user = db.query(User).filter(User.id == password_reset.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Hash new password
    hashed_password = get_password_hash(new_password)
    
    # Update user password
    user.password_hash = hashed_password
    db.commit()
    
    # Mark token as used
    password_reset.used_at = datetime.utcnow()
    db.commit()
    
    # Revoke all existing sessions
    revoke_all_user_sessions(db, user.id)
    
    # Send confirmation email
    email_service.send_password_changed(user.email, user.full_name)
    
    return {"message": "Password has been reset successfully"}


def change_password(db: Session, user: User, current_password: str, new_password: str) -> dict:
    """
    Change password for authenticated user.
    """
    # Verify current password
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Check if new password is different
    if verify_password(new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )
    
    # Hash new password
    hashed_password = get_password_hash(new_password)
    
    # Update user password
    user.password_hash = hashed_password
    db.commit()
    
    # Revoke all existing sessions except current
    # For simplicity, we revoke all sessions and user must re-login
    revoke_all_user_sessions(db, user.id)
    
    # Send confirmation email
    email_service.send_password_changed(user.email, user.full_name)
    
    return {"message": "Password has been changed successfully"}
