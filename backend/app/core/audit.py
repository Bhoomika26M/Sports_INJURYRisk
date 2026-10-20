import logging
from datetime import datetime
from typing import Optional
from app.models.user import User

# Configure audit logger
audit_logger = logging.getLogger("security_audit")
audit_logger.setLevel(logging.INFO)

# Console handler for development
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
audit_logger.addHandler(handler)


def log_security_event(
    event_type: str,
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[dict] = None,
    success: bool = True
):
    """
    Log security events for audit purposes.
    
    IMPORTANT: Never log passwords, tokens, or sensitive data.
    """
    log_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "user_id": user_id,
        "user_email": user_email,
        "ip_address": ip_address,
        "success": success,
        "details": details or {}
    }
    
    if success:
        audit_logger.info(f"SECURITY_EVENT: {log_data}")
    else:
        audit_logger.warning(f"SECURITY_EVENT: {log_data}")


def log_login(user: User, ip_address: Optional[str] = None, success: bool = True):
    """Log login attempt."""
    log_security_event(
        event_type="LOGIN",
        user_id=user.id,
        user_email=user.email,
        ip_address=ip_address,
        success=success
    )


def log_logout(user: User, ip_address: Optional[str] = None):
    """Log logout."""
    log_security_event(
        event_type="LOGOUT",
        user_id=user.id,
        user_email=user.email,
        ip_address=ip_address,
        success=True
    )


def log_password_reset_request(email: str, ip_address: Optional[str] = None):
    """Log password reset request (without revealing if email exists)."""
    log_security_event(
        event_type="PASSWORD_RESET_REQUEST",
        user_email=email,  # May not exist
        ip_address=ip_address,
        success=True
    )


def log_password_reset(user: User, ip_address: Optional[str] = None):
    """Log successful password reset."""
    log_security_event(
        event_type="PASSWORD_RESET",
        user_id=user.id,
        user_email=user.email,
        ip_address=ip_address,
        success=True
    )


def log_password_change(user: User, ip_address: Optional[str] = None):
    """Log password change."""
    log_security_event(
        event_type="PASSWORD_CHANGE",
        user_id=user.id,
        user_email=user.email,
        ip_address=ip_address,
        success=True
    )


def log_failed_login(email: str, ip_address: Optional[str] = None):
    """Log failed login attempt."""
    log_security_event(
        event_type="LOGIN_FAILED",
        user_email=email,
        ip_address=ip_address,
        success=False
    )


def log_authorization_failure(user_id: Optional[int], email: Optional[str], resource: str, ip_address: Optional[str] = None):
    """Log authorization failure."""
    log_security_event(
        event_type="AUTHORIZATION_FAILURE",
        user_id=user_id,
        user_email=email,
        ip_address=ip_address,
        details={"resource": resource},
        success=False
    )


def log_registration(user: User, ip_address: Optional[str] = None):
    """Log user registration."""
    log_security_event(
        event_type="USER_REGISTRATION",
        user_id=user.id,
        user_email=user.email,
        ip_address=ip_address,
        details={"role": user.role},
        success=True
    )


def log_admin_user_created(
    new_user: User,
    admin_user: User,
    ip_address: Optional[str] = None,
):
    """Log an administrator creating a user with a privileged role."""
    log_security_event(
        event_type="ADMIN_USER_CREATED",
        user_id=admin_user.id,
        user_email=admin_user.email,
        ip_address=ip_address,
        details={
            "created_user_id": new_user.id,
            "created_user_email": new_user.email,
            "created_role": new_user.role,
        },
        success=True,
    )


def log_otp_requested(
    purpose: str,
    user_email: Optional[str] = None,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
):
    """Log that an email OTP was issued. Never includes the code itself."""
    log_security_event(
        event_type="OTP_REQUESTED",
        user_id=user_id,
        user_email=user_email,
        ip_address=ip_address,
        details={"purpose": purpose},
        success=True
    )


def log_otp_verification_failed(
    purpose: str,
    email: Optional[str] = None,
    ip_address: Optional[str] = None,
    reason: Optional[str] = None,
):
    """Log a failed/rejected OTP verification. Never includes the code."""
    log_security_event(
        event_type="OTP_VERIFICATION_FAILED",
        user_email=email,
        ip_address=ip_address,
        details={"purpose": purpose, "reason": reason},
        success=False
    )
