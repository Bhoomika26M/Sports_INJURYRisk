"""Tests for Google Sign-In (OAuth 2.0 authorization-code flow).

The Google HTTP calls (token exchange + userinfo) are monkeypatched, so these
tests never touch the network. They cover the state signing/verification, the
account-resolution rules (sign in / link by verified email / create athlete),
and the guard rails (inactive accounts, unverified email, subject conflicts,
misconfigured server).
"""

import secrets

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.athlete import Athlete
from app.models.user import User
from app.services import google_auth_service as google


# --------------------------------------------------------------------------- #
# Fixtures / helpers
# --------------------------------------------------------------------------- #

@pytest.fixture(autouse=True)
def reset_rate_limiter():
    from app.core.rate_limit import rate_limiter
    with rate_limiter.lock:
        rate_limiter.requests.clear()
    yield
    with rate_limiter.lock:
        rate_limiter.requests.clear()


@pytest.fixture
def google_configured(monkeypatch):
    """Pretend the server has Google credentials configured."""
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "test-client-secret")
    return settings


def _profile(sub="google-sub-1", email=None, verified=True, name="Test Google"):
    return {
        "sub": sub,
        "email": email or f"g{secrets.token_hex(6)}@example.com",
        "email_verified": verified,
        "name": name,
    }


def _make_user(db: Session, email=None, role="athlete", active=True, **kw):
    user = User(
        email=email or f"local{secrets.token_hex(6)}@example.com",
        password_hash=google._unusable_hash(),
        full_name="Local User",
        role=role,
        is_active=active,
        **kw,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _patch_userinfo(monkeypatch, profile):
    """Patch the network step to return the supplied Google profile."""
    monkeypatch.setattr(google, "exchange_code_for_userinfo", lambda code: profile)


# --------------------------------------------------------------------------- #
# State signing (CSRF protection)
# --------------------------------------------------------------------------- #

def test_state_round_trips():
    state = google.create_oauth_state(next_url="/videos/upload")
    payload = google.verify_oauth_state(state)
    assert payload["next"] == "/videos/upload"
    assert payload["n"]


def test_state_rejects_tampering():
    state = google.create_oauth_state()
    payload_b64, signature = state.rsplit(".", 1)
    tampered = f"{payload_b64}.{'A' * len(signature)}"
    with pytest.raises(HTTPException) as exc:
        google.verify_oauth_state(tampered)
    assert exc.value.status_code == 400


def test_state_rejects_expired(monkeypatch):
    state = google.create_oauth_state()
    monkeypatch.setattr(settings, "GOOGLE_STATE_EXPIRE_SECONDS", 0)
    with pytest.raises(HTTPException) as exc:
        google.verify_oauth_state(state)
    assert exc.value.status_code == 400


def test_state_rejects_garbage():
    for bad in ("", "no-dot", "a.b.c.d"):
        with pytest.raises(HTTPException):
            google.verify_oauth_state(bad)


# --------------------------------------------------------------------------- #
# Configuration gating
# --------------------------------------------------------------------------- #

def test_authorize_url_requires_configuration(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "")
    with pytest.raises(HTTPException) as exc:
        google.build_authorization_url()
    assert exc.value.status_code == 503


def test_authorize_url_contains_expected_params(google_configured):
    url, state = google.build_authorization_url(next_url="/dashboard")
    assert url.startswith(settings.GOOGLE_AUTH_URI)
    assert "client_id=test-client-id" in url
    assert "response_type=code" in url
    assert "scope=openid+email+profile" in url or "scope=openid%20email%20profile" in url
    assert state in url


# --------------------------------------------------------------------------- #
# Account resolution
# --------------------------------------------------------------------------- #

def test_new_google_user_creates_athlete(db, google_configured, monkeypatch):
    profile = _profile(email="newbie@example.com")
    _patch_userinfo(monkeypatch, profile)

    user, outcome = google.authenticate_with_google(db, "auth-code")

    assert outcome == "created"
    assert user.email == "newbie@example.com"
    assert user.role == "athlete"
    assert user.oauth_provider == "google"
    assert user.oauth_subject == profile["sub"]
    # Google-only accounts must not be password-loggable.
    assert user.password_hash.startswith("$2")
    profile_row = db.query(Athlete).filter(Athlete.user_id == user.id).first()
    assert profile_row is not None


def test_existing_linked_user_signs_in(db, google_configured, monkeypatch):
    existing = _make_user(
        db, email="linked@example.com", oauth_provider="google", oauth_subject="sub-42"
    )
    _patch_userinfo(monkeypatch, _profile(sub="sub-42", email="linked@example.com"))

    user, outcome = google.authenticate_with_google(db, "auth-code")

    assert outcome == "signed_in"
    assert user.id == existing.id


def test_existing_email_gets_linked(db, google_configured, monkeypatch):
    existing = _make_user(db, email="known@example.com")
    _patch_userinfo(monkeypatch, _profile(sub="sub-99", email="known@example.com"))

    user, outcome = google.authenticate_with_google(db, "auth-code")

    assert outcome == "linked"
    assert user.id == existing.id
    assert user.oauth_provider == "google"
    assert user.oauth_subject == "sub-99"


def test_linking_is_case_insensitive_on_email(db, google_configured, monkeypatch):
    existing = _make_user(db, email="Mixed@Example.com")
    _patch_userinfo(monkeypatch, _profile(sub="sub-c", email="mixed@example.com"))

    user, outcome = google.authenticate_with_google(db, "auth-code")
    assert outcome == "linked"
    assert user.id == existing.id


def test_unverified_email_is_refused(db, google_configured, monkeypatch):
    _patch_userinfo(monkeypatch, _profile(email="unverified@example.com", verified=False))
    with pytest.raises(HTTPException) as exc:
        google.authenticate_with_google(db, "auth-code")
    assert exc.value.status_code == 403
    assert db.query(User).filter(User.email == "unverified@example.com").first() is None


def test_inactive_account_is_refused(db, google_configured, monkeypatch):
    _make_user(
        db,
        email="off@example.com",
        active=False,
        oauth_provider="google",
        oauth_subject="sub-off",
    )
    _patch_userinfo(monkeypatch, _profile(sub="sub-off", email="off@example.com"))
    with pytest.raises(HTTPException) as exc:
        google.authenticate_with_google(db, "auth-code")
    assert exc.value.status_code == 403


def test_subject_conflict_is_refused(db, google_configured, monkeypatch):
    """An email already bound to a different Google subject must not be stolen."""
    _make_user(
        db,
        email="taken@example.com",
        oauth_provider="google",
        oauth_subject="original-sub",
    )
    _patch_userinfo(monkeypatch, _profile(sub="attacker-sub", email="taken@example.com"))
    with pytest.raises(HTTPException) as exc:
        google.authenticate_with_google(db, "auth-code")
    assert exc.value.status_code == 409


# --------------------------------------------------------------------------- #
# HTTP endpoints
# --------------------------------------------------------------------------- #

def test_authorize_url_endpoint(client, google_configured):
    resp = client.get("/api/v1/auth/google/authorize-url", params={"next": "/profile"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["authorization_url"].startswith(settings.GOOGLE_AUTH_URI)
    assert body["state"]


def test_authorize_url_endpoint_503_when_unconfigured(client, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "")
    resp = client.get("/api/v1/auth/google/authorize-url")
    assert resp.status_code == 503


def test_exchange_endpoint_issues_token(client, db, google_configured, monkeypatch):
    profile = _profile(email="viabrowser@example.com")
    _patch_userinfo(monkeypatch, profile)
    state = google.create_oauth_state()

    resp = client.post(
        "/api/v1/auth/google/exchange", json={"code": "auth-code", "state": state}
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    assert token

    # The issued token must be a normal, working application session.
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "viabrowser@example.com"


def test_exchange_endpoint_rejects_bad_state(client, google_configured):
    resp = client.post(
        "/api/v1/auth/google/exchange", json={"code": "x", "state": "not-a-state"}
    )
    assert resp.status_code == 400
