"""Tests for the email-OTP password recovery and password change workflows.

These use the shared conftest fixtures (isolated test database + TestClient).
The email service is monkeypatched so tests never touch SMTP; the captured codes
let us drive the happy paths without weakening the security under test.
"""

import secrets
from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import sessionmaker

from app.core.otp import (
    PURPOSE_PASSWORD_CHANGE,
    PURPOSE_PASSWORD_RECOVERY,
)
from app.core.security import (
    create_access_token,
    create_user_session,
    get_password_hash,
    verify_password,
)
from app.models.password_otp import PasswordOTP
from app.models.user import User


# --------------------------------------------------------------------------- #
# Fixtures / helpers
# --------------------------------------------------------------------------- #

@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Keep the global in-memory rate limiter from leaking between tests."""
    from app.core.rate_limit import rate_limiter
    with rate_limiter.lock:
        rate_limiter.requests.clear()
    yield
    with rate_limiter.lock:
        rate_limiter.requests.clear()


@pytest.fixture
def sent_otps(monkeypatch):
    """Capture OTP emails instead of sending them. Returns the list of sends."""
    sent = []

    def fake_send(to_email, otp, purpose_label, expires_minutes):
        sent.append(
            {"to_email": to_email, "otp": otp, "purpose_label": purpose_label}
        )
        return True

    from app.core.email import email_service
    monkeypatch.setattr(email_service, "send_otp", fake_send)
    return sent


def _make_user(db, password="oldpassword123", role="athlete"):
    user = User(
        email=f"otp{secrets.token_hex(6)}@example.com",
        password_hash=get_password_hash(password),
        full_name="OTP User",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def user(db):
    return _make_user(db)


def _auth_headers(db, user, minutes=30):
    token_data = create_access_token(
        data={"sub": user.email}, expires_delta=timedelta(minutes=minutes)
    )
    create_user_session(db, user, token_data["jti"], token_data["expires_at"])
    return {"Authorization": f"Bearer {token_data['access_token']}"}


@pytest.fixture
def auth_headers(db, user):
    return _auth_headers(db, user)


def _rows(db, user, purpose):
    return (
        db.query(PasswordOTP)
        .filter(PasswordOTP.user_id == user.id, PasswordOTP.purpose == purpose)
        .order_by(PasswordOTP.id.asc())
        .all()
    )


def _latest(db, user, purpose):
    rows = _rows(db, user, purpose)
    return rows[-1] if rows else None


def _request_recovery(client, email):
    return client.post("/api/v1/auth/forgot-password", json={"email": email})


def _request_change_code(client, headers):
    return client.post("/api/v1/auth/change-password/request-otp", headers=headers)


# --------------------------------------------------------------------------- #
# Workflow A: password recovery
# --------------------------------------------------------------------------- #

def test_recovery_same_response_for_existing_and_unknown_email(client, sent_otps, db, user):
    known = _request_recovery(client, user.email)
    unknown = _request_recovery(client, "nobody-here@example.com")
    assert known.status_code == 200
    assert unknown.status_code == 200
    assert known.json() == unknown.json()
    # No enumeration hint in the message text.
    assert "sent" in known.json()["message"].lower()
    # Only the real account got an email.
    assert len(sent_otps) == 1
    assert sent_otps[0]["to_email"] == user.email


def test_recovery_valid_otp_resets_password(client, sent_otps, db, user):
    _request_recovery(client, user.email)
    code = sent_otps[-1]["otp"]

    resp = client.post(
        "/api/v1/auth/reset-password",
        json={"email": user.email, "otp": code, "new_password": "brandnewpass123"},
    )
    assert resp.status_code == 200

    db.expire_all()
    refreshed = db.query(User).filter(User.id == user.id).first()
    assert verify_password("brandnewpass123", refreshed.password_hash)
    assert not verify_password("oldpassword123", refreshed.password_hash)


def test_recovery_wrong_otp_rejected(client, sent_otps, db, user):
    _request_recovery(client, user.email)
    code = sent_otps[-1]["otp"]
    wrong = "000000" if code != "000000" else "111111"

    resp = client.post(
        "/api/v1/auth/reset-password",
        json={"email": user.email, "otp": wrong, "new_password": "brandnewpass123"},
    )
    assert resp.status_code == 400


def test_recovery_expired_otp_rejected(client, sent_otps, db, user):
    _request_recovery(client, user.email)
    code = sent_otps[-1]["otp"]

    row = _latest(db, user, PURPOSE_PASSWORD_RECOVERY)
    row.expires_at = datetime.utcnow() - timedelta(minutes=1)
    db.commit()

    resp = client.post(
        "/api/v1/auth/reset-password",
        json={"email": user.email, "otp": code, "new_password": "brandnewpass123"},
    )
    assert resp.status_code == 400


def test_recovery_otp_single_use(client, sent_otps, db, user):
    _request_recovery(client, user.email)
    code = sent_otps[-1]["otp"]

    first = client.post(
        "/api/v1/auth/reset-password",
        json={"email": user.email, "otp": code, "new_password": "brandnewpass123"},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/v1/auth/reset-password",
        json={"email": user.email, "otp": code, "new_password": "anotherpass1234"},
    )
    assert second.status_code == 400


def test_recovery_superseded_otp_rejected(client, sent_otps, db, user, monkeypatch):
    # Allow an immediate re-issue so we get two codes.
    monkeypatch.setattr(
        "app.services.otp_service.settings.OTP_RESEND_COOLDOWN_SECONDS", 0
    )
    _request_recovery(client, user.email)
    first_code = sent_otps[-1]["otp"]
    _request_recovery(client, user.email)
    second_code = sent_otps[-1]["otp"]
    assert first_code != second_code

    stale = client.post(
        "/api/v1/auth/reset-password",
        json={"email": user.email, "otp": first_code, "new_password": "brandnewpass123"},
    )
    assert stale.status_code == 400

    fresh = client.post(
        "/api/v1/auth/reset-password",
        json={"email": user.email, "otp": second_code, "new_password": "brandnewpass123"},
    )
    assert fresh.status_code == 200


def test_recovery_attempt_limit_enforced(client, sent_otps, db, user):
    _request_recovery(client, user.email)
    code = sent_otps[-1]["otp"]
    wrong = "000000" if code != "000000" else "111111"

    statuses = []
    for _ in range(6):
        r = client.post(
            "/api/v1/auth/reset-password",
            json={"email": user.email, "otp": wrong, "new_password": "brandnewpass123"},
        )
        statuses.append(r.status_code)

    # Five wrong tries are rejected as invalid; the sixth hits the attempt cap.
    assert statuses[:5] == [400] * 5
    assert statuses[5] == 429

    # Even the correct code is now unusable.
    blocked = client.post(
        "/api/v1/auth/reset-password",
        json={"email": user.email, "otp": code, "new_password": "brandnewpass123"},
    )
    assert blocked.status_code == 429


def test_recovery_code_cannot_reset_another_account(client, sent_otps, db, user):
    other = _make_user(db, password="otherpass12345")

    _request_recovery(client, user.email)
    code = sent_otps[-1]["otp"]

    resp = client.post(
        "/api/v1/auth/reset-password",
        json={"email": other.email, "otp": code, "new_password": "brandnewpass123"},
    )
    assert resp.status_code == 400

    db.expire_all()
    other_refreshed = db.query(User).filter(User.id == other.id).first()
    assert verify_password("otherpass12345", other_refreshed.password_hash)


def test_recovery_stores_hash_not_raw_code(client, sent_otps, db, user):
    _request_recovery(client, user.email)
    code = sent_otps[-1]["otp"]

    row = _latest(db, user, PURPOSE_PASSWORD_RECOVERY)
    assert row is not None
    assert row.otp_hash != code
    assert code not in row.otp_hash


def test_recovery_code_not_returned_by_api(client, sent_otps, db, user):
    resp = _request_recovery(client, user.email)
    body = resp.text
    assert sent_otps[-1]["otp"] not in body


def test_recovery_revokes_all_sessions(client, sent_otps, db, user):
    headers = _auth_headers(db, user)
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200

    _request_recovery(client, user.email)
    code = sent_otps[-1]["otp"]
    client.post(
        "/api/v1/auth/reset-password",
        json={"email": user.email, "otp": code, "new_password": "brandnewpass123"},
    )

    # Previously issued access token is now rejected.
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_recovery_email_failure_handled_safely(client, db, user, monkeypatch):
    def failing_send(to_email, otp, purpose_label, expires_minutes):
        return False

    from app.core.email import email_service
    monkeypatch.setattr(email_service, "send_otp", failing_send)

    resp = _request_recovery(client, user.email)
    # Still generic (no enumeration, no error oracle).
    assert resp.status_code == 200

    # No usable, undisclosed code is left behind.
    row = _latest(db, user, PURPOSE_PASSWORD_RECOVERY)
    assert row is not None
    assert row.invalidated_at is not None
    assert row.used_at is None

    for candidate in ("000000", "111111", "222222"):
        r = client.post(
            "/api/v1/auth/reset-password",
            json={"email": user.email, "otp": candidate, "new_password": "brandnewpass123"},
        )
        assert r.status_code == 400


def test_recovery_password_policy_intact(client, sent_otps, db, user):
    _request_recovery(client, user.email)
    code = sent_otps[-1]["otp"]

    resp = client.post(
        "/api/v1/auth/reset-password",
        json={"email": user.email, "otp": code, "new_password": "short"},
    )
    assert resp.status_code == 422


def test_recovery_endpoint_rate_limited(client, sent_otps, db, user):
    statuses = [_request_recovery(client, user.email).status_code for _ in range(4)]
    assert statuses[:3] == [200, 200, 200]
    assert statuses[3] == 429


def test_recovery_resend_cooldown_suppresses_resend(client, sent_otps, db, user):
    _request_recovery(client, user.email)
    assert len(sent_otps) == 1
    # Second request within the (default 60s) cooldown: generic response, no new email.
    second = _request_recovery(client, user.email)
    assert second.status_code == 200
    assert len(sent_otps) == 1


# --------------------------------------------------------------------------- #
# Workflow B: authenticated password change
# --------------------------------------------------------------------------- #

def test_change_requires_authentication(client, sent_otps, db, user):
    assert client.post("/api/v1/auth/change-password/request-otp").status_code == 401
    assert client.post(
        "/api/v1/auth/change-password",
        json={"otp": "123456", "current_password": "oldpassword123", "new_password": "brandnewpass123"},
    ).status_code == 401


def test_change_request_otp_sent_to_own_email(client, sent_otps, db, user, auth_headers):
    resp = _request_change_code(client, auth_headers)
    assert resp.status_code == 200
    assert len(sent_otps) == 1
    assert sent_otps[0]["to_email"] == user.email


def test_change_request_ignores_client_supplied_recipient(client, sent_otps, db, user, auth_headers):
    other = _make_user(db, password="otherpass12345")
    resp = client.post(
        "/api/v1/auth/change-password/request-otp",
        headers=auth_headers,
        json={"email": other.email, "user_id": other.id},
    )
    assert resp.status_code == 200
    # Code still goes to the authenticated account, never the supplied address.
    assert sent_otps[0]["to_email"] == user.email
    assert other.email not in [s["to_email"] for s in sent_otps]


def test_change_valid_otp_and_current_password(client, sent_otps, db, user, auth_headers):
    _request_change_code(client, auth_headers)
    code = sent_otps[-1]["otp"]

    resp = client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={"otp": code, "current_password": "oldpassword123", "new_password": "brandnewpass123"},
    )
    assert resp.status_code == 200

    db.expire_all()
    refreshed = db.query(User).filter(User.id == user.id).first()
    assert verify_password("brandnewpass123", refreshed.password_hash)


def test_change_wrong_current_password_rejected(client, sent_otps, db, user, auth_headers):
    _request_change_code(client, auth_headers)
    code = sent_otps[-1]["otp"]

    resp = client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={"otp": code, "current_password": "WRONG", "new_password": "brandnewpass123"},
    )
    assert resp.status_code == 400

    # A wrong current password must NOT consume the OTP (no self-lockout).
    still_ok = client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={"otp": code, "current_password": "oldpassword123", "new_password": "brandnewpass123"},
    )
    assert still_ok.status_code == 200


def test_change_wrong_otp_rejected(client, sent_otps, db, user, auth_headers):
    _request_change_code(client, auth_headers)
    code = sent_otps[-1]["otp"]
    wrong = "000000" if code != "000000" else "111111"

    resp = client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={"otp": wrong, "current_password": "oldpassword123", "new_password": "brandnewpass123"},
    )
    assert resp.status_code == 400


def test_change_expired_otp_rejected(client, sent_otps, db, user, auth_headers):
    _request_change_code(client, auth_headers)
    code = sent_otps[-1]["otp"]

    row = _latest(db, user, PURPOSE_PASSWORD_CHANGE)
    row.expires_at = datetime.utcnow() - timedelta(minutes=1)
    db.commit()

    resp = client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={"otp": code, "current_password": "oldpassword123", "new_password": "brandnewpass123"},
    )
    assert resp.status_code == 400


def test_change_otp_single_use(client, sent_otps, db, user, auth_headers):
    _request_change_code(client, auth_headers)
    code = sent_otps[-1]["otp"]

    first = client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={"otp": code, "current_password": "oldpassword123", "new_password": "brandnewpass123"},
    )
    assert first.status_code == 200

    headers2 = _auth_headers(db, user)
    second = client.post(
        "/api/v1/auth/change-password",
        headers=headers2,
        json={"otp": code, "current_password": "brandnewpass123", "new_password": "anotherpass1234"},
    )
    assert second.status_code == 400


def test_change_rejects_password_reuse(client, sent_otps, db, user, auth_headers):
    _request_change_code(client, auth_headers)
    code = sent_otps[-1]["otp"]

    resp = client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={"otp": code, "current_password": "oldpassword123", "new_password": "oldpassword123"},
    )
    assert resp.status_code == 400


def test_change_revokes_all_sessions_including_current(client, sent_otps, db, user, auth_headers):
    # A second, independent session for the same user.
    other_headers = _auth_headers(db, user)

    _request_change_code(client, auth_headers)
    code = sent_otps[-1]["otp"]
    resp = client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={"otp": code, "current_password": "oldpassword123", "new_password": "brandnewpass123"},
    )
    assert resp.status_code == 200

    # Both the current and the other session are revoked.
    assert client.get("/api/v1/auth/me", headers=auth_headers).status_code == 401
    assert client.get("/api/v1/auth/me", headers=other_headers).status_code == 401


def test_change_new_password_works_and_old_fails(client, sent_otps, db, user, auth_headers):
    _request_change_code(client, auth_headers)
    code = sent_otps[-1]["otp"]
    client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={"otp": code, "current_password": "oldpassword123", "new_password": "brandnewpass123"},
    )

    assert client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "brandnewpass123"}
    ).status_code == 200
    assert client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "oldpassword123"}
    ).status_code == 401


def test_change_request_resend_cooldown(client, sent_otps, db, user, auth_headers):
    assert _request_change_code(client, auth_headers).status_code == 200
    # Immediate second request is throttled by the cooldown.
    second = _request_change_code(client, auth_headers)
    assert second.status_code == 429
    assert len(sent_otps) == 1


# --------------------------------------------------------------------------- #
# Cross-purpose isolation
# --------------------------------------------------------------------------- #

def test_recovery_otp_cannot_authorize_password_change(client, sent_otps, db, user, auth_headers):
    _request_recovery(client, user.email)
    recovery_code = sent_otps[-1]["otp"]

    resp = client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={"otp": recovery_code, "current_password": "oldpassword123", "new_password": "brandnewpass123"},
    )
    assert resp.status_code == 400


def test_change_otp_cannot_authorize_password_recovery(client, sent_otps, db, user, auth_headers):
    _request_change_code(client, auth_headers)
    change_code = sent_otps[-1]["otp"]

    resp = client.post(
        "/api/v1/auth/reset-password",
        json={"email": user.email, "otp": change_code, "new_password": "brandnewpass123"},
    )
    assert resp.status_code == 400


# --------------------------------------------------------------------------- #
# Concurrency
# --------------------------------------------------------------------------- #

def test_concurrent_consume_only_one_wins(db, user, sent_otps, monkeypatch):
    """Two sessions that both read the live OTP race to consume it; one must lose."""
    monkeypatch.setattr(
        "app.services.otp_service.settings.OTP_RESEND_COOLDOWN_SECONDS", 0
    )

    from app.services.otp_service import issue_otp, _active_otp, _consume_otp

    otp = issue_otp(db, user, PURPOSE_PASSWORD_CHANGE)

    Other = sessionmaker(bind=db.get_bind())
    s1, s2 = Other(), Other()
    try:
        r1 = _active_otp(s1, user.id, PURPOSE_PASSWORD_CHANGE)
        r2 = _active_otp(s2, user.id, PURPOSE_PASSWORD_CHANGE)
        assert r1 is not None and r2 is not None

        outcomes = []
        for session, record in ((s1, r1), (s2, r2)):
            try:
                _consume_otp(session, record, PURPOSE_PASSWORD_CHANGE, otp)
                session.commit()
                outcomes.append("consumed")
            except Exception:
                session.rollback()
                outcomes.append("rejected")
        assert outcomes.count("consumed") == 1
        assert outcomes.count("rejected") == 1
    finally:
        s1.close()
        s2.close()
