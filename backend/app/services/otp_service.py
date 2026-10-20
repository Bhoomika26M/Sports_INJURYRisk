"""Email OTP workflows for password recovery and authenticated password change.

Design notes
------------
* OTPs are generated with `secrets` and stored only as keyed HMAC digests
  (`app/core/otp.py`). The raw code is returned to the caller solely so it can
  be emailed, and is never persisted or logged.
* Every issued code is bound to a *purpose* ("password_recovery" or
  "password_change") and to a single user account.
* Issuing a new code invalidates any outstanding code for the same account and
  purpose.
* Verification consumes the code with a single conditional UPDATE; because the
  UPDATE only matches a still-unused, unexpired, under-limit row, two
  concurrent requests cannot both consume the same code, and repeated bad
  submissions cannot exceed the attempt limit.
* Recovery requests always return a generic response so the endpoint cannot be
  used to enumerate accounts.
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.audit import (
    log_otp_requested,
    log_otp_verification_failed,
    log_password_change,
    log_password_reset,
    log_password_reset_request,
    log_security_event,
)
from app.core.config import settings
from app.core.email import email_service
from app.core.otp import (
    PURPOSE_PASSWORD_CHANGE,
    PURPOSE_PASSWORD_RECOVERY,
    generate_otp,
    hash_otp,
    verify_otp,
)
from app.core.security import (
    get_password_hash,
    revoke_all_user_sessions,
    verify_password,
)
from app.models.password_otp import PasswordOTP
from app.models.user import User


# Kept deliberately generic (no account-existence hint) while remaining
# wording-compatible with the message the previous token-link flow returned.
GENERIC_RECOVERY_MESSAGE = (
    "If an account exists for this email, password reset instructions have been sent."
)


def _invalid_otp_exception() -> HTTPException:
    """A single generic error for every OTP failure mode (no oracle)."""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired verification code",
    )


def _too_many_attempts_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many verification attempts. Please request a new code.",
    )


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _find_user_by_email(db: Session, email: str) -> Optional[User]:
    return (
        db.query(User)
        .filter(func.lower(User.email) == _normalize_email(email))
        .first()
    )


def _active_otp(db: Session, user_id: int, purpose: str) -> Optional[PasswordOTP]:
    """Most recent still-usable OTP for an account/purpose."""
    return (
        db.query(PasswordOTP)
        .filter(
            PasswordOTP.user_id == user_id,
            PasswordOTP.purpose == purpose,
            PasswordOTP.used_at.is_(None),
            PasswordOTP.invalidated_at.is_(None),
        )
        .order_by(PasswordOTP.created_at.desc(), PasswordOTP.id.desc())
        .first()
    )


def _recently_issued(db: Session, user_id: int, purpose: str) -> bool:
    """True if a code was issued for this account/purpose within the cooldown."""
    cutoff = datetime.utcnow() - timedelta(seconds=settings.OTP_RESEND_COOLDOWN_SECONDS)
    row = (
        db.query(PasswordOTP.id)
        .filter(
            PasswordOTP.user_id == user_id,
            PasswordOTP.purpose == purpose,
            PasswordOTP.created_at >= cutoff,
        )
        .first()
    )
    return row is not None


def _invalidate_outstanding(db: Session, user_id: int, purpose: str) -> int:
    """Invalidate every outstanding code for an account/purpose. Returns count."""
    now = datetime.utcnow()
    return (
        db.query(PasswordOTP)
        .filter(
            PasswordOTP.user_id == user_id,
            PasswordOTP.purpose == purpose,
            PasswordOTP.used_at.is_(None),
            PasswordOTP.invalidated_at.is_(None),
        )
        .update({PasswordOTP.invalidated_at: now}, synchronize_session=False)
    )


def issue_otp(db: Session, user: User, purpose: str) -> str:
    """Create a fresh OTP for a user/purpose, invalidating any outstanding code.

    Returns the raw code (never stored) so the caller can email it.
    """
    _invalidate_outstanding(db, user.id, purpose)

    otp = generate_otp()
    record = PasswordOTP(
        user_id=user.id,
        purpose=purpose,
        otp_hash=hash_otp(otp, purpose),
        expires_at=datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
        attempt_count=0,
        max_attempts=settings.OTP_MAX_ATTEMPTS,
    )
    db.add(record)
    db.commit()
    return otp


def _consume_otp(db: Session, record: PasswordOTP, purpose: str, otp: str) -> None:
    """Validate and atomically mark an OTP used.

    Raises on any failure. On success the row is marked used *within the current
    transaction* and NOT committed here - the caller commits together with the
    password update so consumption and the password change are atomic.
    """
    if record.expires_at <= datetime.utcnow():
        record.invalidated_at = datetime.utcnow()
        db.commit()
        raise _invalid_otp_exception()

    if record.attempt_count >= record.max_attempts:
        raise _too_many_attempts_exception()

    if not verify_otp(otp, purpose, record.otp_hash):
        # Count the failed attempt with a conditional UPDATE so the limit holds
        # even under concurrency.
        updated = (
            db.query(PasswordOTP)
            .filter(
                PasswordOTP.id == record.id,
                PasswordOTP.used_at.is_(None),
                PasswordOTP.attempt_count < PasswordOTP.max_attempts,
            )
            .update(
                {PasswordOTP.attempt_count: PasswordOTP.attempt_count + 1},
                synchronize_session=False,
            )
        )
        db.commit()
        if updated != 1:
            raise _too_many_attempts_exception()
        raise _invalid_otp_exception()

    # Correct code: consume atomically.
    now = datetime.utcnow()
    consumed = (
        db.query(PasswordOTP)
        .filter(
            PasswordOTP.id == record.id,
            PasswordOTP.used_at.is_(None),
            PasswordOTP.invalidated_at.is_(None),
            PasswordOTP.expires_at > now,
            PasswordOTP.attempt_count < PasswordOTP.max_attempts,
        )
        .update({PasswordOTP.used_at: now}, synchronize_session=False)
    )
    if consumed != 1:
        db.rollback()
        raise _invalid_otp_exception()


def _load_usable_otp_or_raise(
    db: Session, user_id: int, purpose: str, otp: str, email_for_audit: Optional[str]
) -> PasswordOTP:
    record = _active_otp(db, user_id, purpose)
    if record is None:
        log_otp_verification_failed(purpose, email_for_audit, reason="no_active_code")
        raise _invalid_otp_exception()
    try:
        _consume_otp(db, record, purpose, otp)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_400_BAD_REQUEST:
            log_otp_verification_failed(purpose, email_for_audit, reason="mismatch_or_expired")
        elif exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            log_otp_verification_failed(purpose, email_for_audit, reason="attempt_limit")
        raise
    return record


# --------------------------------------------------------------------------- #
# Workflow A: password recovery (unauthenticated)
# --------------------------------------------------------------------------- #

def request_password_recovery_otp(db: Session, email: str, ip_address: Optional[str] = None) -> dict:
    """Issue a recovery OTP to a registered account (generic response always)."""
    normalized = _normalize_email(email)

    # Always record that a request was received (without confirming existence).
    log_password_reset_request(normalized, ip_address)

    user = _find_user_by_email(db, normalized) if normalized else None
    if user is not None and user.is_active:
        # Per-account resend cooldown: silently skip re-sending inside the
        # window (the client cannot tell the difference, so no enumeration).
        if not _recently_issued(db, user.id, PURPOSE_PASSWORD_RECOVERY):
            otp = issue_otp(db, user, PURPOSE_PASSWORD_RECOVERY)
            delivered = email_service.send_otp(
                user.email, otp, "password recovery", settings.OTP_EXPIRE_MINUTES
            )
            if delivered:
                log_otp_requested(
                    PURPOSE_PASSWORD_RECOVERY, user_email=user.email, user_id=user.id, ip_address=ip_address
                )
            else:
                # Delivery failed: invalidate so an undisclosed, unusable code
                # cannot linger, and log the failure.
                _invalidate_outstanding(db, user.id, PURPOSE_PASSWORD_RECOVERY)
                db.commit()
                log_security_event(
                    event_type="OTP_DELIVERY_FAILED",
                    user_id=user.id,
                    user_email=user.email,
                    ip_address=ip_address,
                    details={"purpose": PURPOSE_PASSWORD_RECOVERY},
                    success=False,
                )

    return {"message": GENERIC_RECOVERY_MESSAGE}


def verify_recovery_and_reset_password(
    db: Session, email: str, otp: str, new_password: str, ip_address: Optional[str] = None
) -> dict:
    """Verify a recovery OTP and set a new password; revokes all sessions."""
    normalized = _normalize_email(email)
    user = _find_user_by_email(db, normalized) if normalized else None
    if user is None or not user.is_active:
        # Do not reveal whether the account exists.
        raise _invalid_otp_exception()

    _load_usable_otp_or_raise(db, user.id, PURPOSE_PASSWORD_RECOVERY, otp, user.email)

    # OTP marked used in this transaction; commit together with the password.
    user.password_hash = get_password_hash(new_password)
    db.commit()

    revoked = revoke_all_user_sessions(db, user.id)
    log_password_reset(user, ip_address)
    log_security_event(
        event_type="SESSION_REVOCATION",
        user_id=user.id,
        user_email=user.email,
        ip_address=ip_address,
        details={"reason": "password_reset", "sessions_revoked": revoked},
    )

    email_service.send_password_changed(user.email, user.full_name)
    return {"message": "Password has been reset successfully. Please sign in again."}


# --------------------------------------------------------------------------- #
# Workflow B: authenticated password change
# --------------------------------------------------------------------------- #

def request_password_change_otp(db: Session, user: User, ip_address: Optional[str] = None) -> dict:
    """Issue a password-change OTP to the *authenticated* account's email."""
    if not user.email or "@" not in user.email:
        # Documented safe failure: the account has no usable email address.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This account has no verified email address to receive a code.",
        )

    if _recently_issued(db, user.id, PURPOSE_PASSWORD_CHANGE):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "A verification code was just sent. "
                f"Please wait {settings.OTP_RESEND_COOLDOWN_SECONDS} seconds before requesting another."
            ),
        )

    otp = issue_otp(db, user, PURPOSE_PASSWORD_CHANGE)
    delivered = email_service.send_otp(
        user.email, otp, "password change", settings.OTP_EXPIRE_MINUTES
    )
    if not delivered:
        _invalidate_outstanding(db, user.id, PURPOSE_PASSWORD_CHANGE)
        db.commit()
        log_security_event(
            event_type="OTP_DELIVERY_FAILED",
            user_id=user.id,
            user_email=user.email,
            ip_address=ip_address,
            details={"purpose": PURPOSE_PASSWORD_CHANGE},
            success=False,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not send the verification code. Please try again later.",
        )

    log_otp_requested(
        PURPOSE_PASSWORD_CHANGE, user_email=user.email, user_id=user.id, ip_address=ip_address
    )
    # Never reveal the code; the recipient is always the account's own email.
    return {"message": "If the account is eligible, a verification code has been sent."}


def verify_change_password(
    db: Session,
    user: User,
    otp: str,
    current_password: str,
    new_password: str,
    ip_address: Optional[str] = None,
) -> dict:
    """Verify OTP + current password, then change the password.

    The identity comes from the authenticated session - never from the client.
    The current password is required as an additional safeguard (OTP alone is
    not sufficient). Any wrong current password is rejected *without* consuming
    the OTP attempt, so a user cannot lock themselves out by mistyping it; the
    route-level rate limit guards against guessing.
    """
    # 1. Current password must be correct. Checked before the OTP so that a
    #    failed password check does not burn an OTP attempt.
    if not verify_password(current_password, user.password_hash):
        log_otp_verification_failed(
            PURPOSE_PASSWORD_CHANGE, user.email, reason="bad_current_password"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # 2. New password must satisfy existing policy, including the reuse rule.
    if verify_password(new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password",
        )

    # 3. Verify + atomically consume the OTP.
    _load_usable_otp_or_raise(db, user.id, PURPOSE_PASSWORD_CHANGE, otp, user.email)

    # 4. Commit password change together with OTP consumption.
    user.password_hash = get_password_hash(new_password)
    db.commit()

    revoked = revoke_all_user_sessions(db, user.id)
    log_password_change(user, ip_address)
    log_security_event(
        event_type="SESSION_REVOCATION",
        user_id=user.id,
        user_email=user.email,
        ip_address=ip_address,
        details={"reason": "password_change", "sessions_revoked": revoked},
    )

    email_service.send_password_changed(user.email, user.full_name)
    return {
        "message": "Password changed successfully. All sessions have been signed out; please sign in again."
    }
