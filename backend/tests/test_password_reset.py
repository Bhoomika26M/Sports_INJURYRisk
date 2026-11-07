"""Tests for Password Reset via Email OTP (U2).

Verifies:
- Enumeration parity (no user leakage)
- Verification & password reset
- Expiry handling
- One-time use (reuse prevention)
- Lockout on excessive failed attempts
- Active session/refresh-token revocation
"""

import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import hash_password, verify_password
from app.modules.users.models import User, UserRole, PasswordResetOtp, RefreshToken
from tests.conftest import auth_header, register_and_login
from tests.factories import make_user


@pytest.mark.asyncio
async def test_enumeration_parity(client: AsyncClient, db_session):
    """Proves: Existing vs non-existing emails return identical 202 response."""
    user = await make_user(db_session, "real_user@test.com", role=UserRole.athlete)
    await db_session.commit()

    # Existing user
    r_exist = await client.post("/api/v1/auth/password/forgot", json={"email": "real_user@test.com"})
    assert r_exist.status_code == 202

    # Non-existing user
    r_fake = await client.post("/api/v1/auth/password/forgot", json={"email": "nonexistent_ghost@test.com"})
    assert r_fake.status_code == 202

    # Bodies must be identical
    assert r_exist.json() == r_fake.json()


@pytest.mark.asyncio
async def test_password_reset_happy_path(client: AsyncClient, db_session):
    """Proves: Request OTP -> Verify code -> Reset password -> Login with new credentials."""
    user = await make_user(db_session, "reset_success@test.com", role=UserRole.coach)
    await db_session.commit()

    # Request reset
    r_forgot = await client.post("/api/v1/auth/password/forgot", json={"email": "reset_success@test.com"})
    assert r_forgot.status_code == 202

    # Retrieve generated OTP from DB
    otp_record = await db_session.scalar(
        select(PasswordResetOtp)
        .where(PasswordResetOtp.user_id == user.id)
        .order_by(PasswordResetOtp.created_at.desc())
    )
    assert otp_record is not None
    assert otp_record.used_at is None

    # Let's set a known code
    code = "123456"
    otp_record.code_hash = hash_password(code)
    await db_session.commit()

    # Reset password
    r_reset = await client.post(
        "/api/v1/auth/password/reset",
        json={
            "email": "reset_success@test.com",
            "code": "123456",
            "new_password": "NewSecretPassword123!",
        },
    )
    assert r_reset.status_code == 200

    # Old password fails
    r_old_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "reset_success@test.com", "password": "password123"},
    )
    assert r_old_login.status_code == 401

    # New password succeeds
    r_new_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "reset_success@test.com", "password": "NewSecretPassword123!"},
    )
    assert r_new_login.status_code == 200


@pytest.mark.asyncio
async def test_password_reset_expiry(client: AsyncClient, db_session):
    """Proves: Expired OTP is rejected."""
    user = await make_user(db_session, "expired_user@test.com", role=UserRole.athlete)
    otp = PasswordResetOtp(
        user_id=user.id,
        code_hash=hash_password("654321"),
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        attempts=0,
    )
    db_session.add(otp)
    await db_session.commit()

    r = await client.post(
        "/api/v1/auth/password/reset",
        json={"email": "expired_user@test.com", "code": "654321", "new_password": "NewPassword123!"},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error"]["code"] == "INVALID_CODE"


@pytest.mark.asyncio
async def test_password_reset_reuse(client: AsyncClient, db_session):
    """Proves: Already used OTP cannot be reused."""
    user = await make_user(db_session, "reuse_user@test.com", role=UserRole.athlete)
    otp = PasswordResetOtp(
        user_id=user.id,
        code_hash=hash_password("999888"),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        used_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        attempts=0,
    )
    db_session.add(otp)
    await db_session.commit()

    r = await client.post(
        "/api/v1/auth/password/reset",
        json={"email": "reuse_user@test.com", "code": "999888", "new_password": "NewPassword123!"},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error"]["code"] == "INVALID_CODE"


@pytest.mark.asyncio
async def test_password_reset_lockout(client: AsyncClient, db_session):
    """Proves: 5 wrong code attempts locks out with 429."""
    user = await make_user(db_session, "lockout_user@test.com", role=UserRole.coach)
    otp = PasswordResetOtp(
        user_id=user.id,
        code_hash=hash_password("111222"),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        attempts=5,
    )
    db_session.add(otp)
    await db_session.commit()

    r = await client.post(
        "/api/v1/auth/password/reset",
        json={"email": "lockout_user@test.com", "code": "111222", "new_password": "NewPassword123!"},
    )
    assert r.status_code == 429
    assert r.json()["detail"]["error"]["code"] == "TOO_MANY_ATTEMPTS"


@pytest.mark.asyncio
async def test_password_reset_revokes_refresh_tokens(client: AsyncClient, db_session):
    """Proves: Resetting password invalidates all existing refresh tokens."""
    token = await register_and_login(client, "revoke_tokens@test.com", "coach")
    user = await db_session.scalar(select(User).where(User.email == "revoke_tokens@test.com"))

    # Create active refresh token
    rt = RefreshToken(
        user_id=user.id,
        token_hash="fake_hash",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        revoked=False,
    )
    db_session.add(rt)
    await db_session.commit()

    # Create valid OTP
    otp = PasswordResetOtp(
        user_id=user.id,
        code_hash=hash_password("555444"),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        attempts=0,
    )
    db_session.add(otp)
    await db_session.commit()

    # Reset password
    r_reset = await client.post(
        "/api/v1/auth/password/reset",
        json={"email": "revoke_tokens@test.com", "code": "555444", "new_password": "BrandNewPassword123!"},
    )
    assert r_reset.status_code == 200

    # Verify refresh token in DB is marked revoked
    await db_session.refresh(rt)
    assert rt.revoked is True
