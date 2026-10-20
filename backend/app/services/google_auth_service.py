"""Google Sign-In (OAuth 2.0 authorization-code flow).

Design
------
* The browser is redirected to Google's consent screen. We pass a short-lived,
  HMAC-signed ``state`` value so the callback can reject CSRF / code-injection
  attempts (the state is stateless, so no server-side session store is needed).
* The callback receives ``code`` + ``state``. We verify the state, exchange the
  code for tokens using the *client secret* (server-to-server, never in the
  browser), then fetch the OpenID ``userinfo``.
* We only trust a Google account whose email is marked ``email_verified``.
* Account resolution (per product decision):
    - existing user with oauth_provider/oauth_subject match -> sign in;
    - existing user with the same verified email -> link + sign in;
    - otherwise -> create a new **athlete** account.
* The user never supplies a role via Google; self-provisioned accounts are
  athletes, exactly like public registration.
* On success we mint our own JWT + server-side session, so Google users get the
  same revocation/session semantics as everyone else.

Nothing here logs tokens, codes, secrets, or raw Google profile payloads.
"""

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Optional, Tuple
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.audit import log_security_event
from app.core.config import settings
from app.core.security import get_password_hash
from app.models.athlete import Athlete
from app.models.user import User

PROVIDER = "google"

# A password hash that can never match a real password. Used for accounts that
# authenticate only through Google, so the (NOT NULL) column stays populated but
# password login is impossible.
_UNUSABLE_PASSWORD_HASH: Optional[str] = None


def google_configured() -> bool:
    """True when the Google client credentials are present."""
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def _require_configured() -> None:
    if not google_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Sign-In is not configured on this server.",
        )


def _unusable_hash() -> str:
    """Lazily build a bcrypt hash of random bytes (never matches a password)."""
    global _UNUSABLE_PASSWORD_HASH
    if _UNUSABLE_PASSWORD_HASH is None:
        _UNUSABLE_PASSWORD_HASH = get_password_hash(secrets.token_urlsafe(32))
    return _UNUSABLE_PASSWORD_HASH


# --------------------------------------------------------------------------- #
# Signed, stateless OAuth state (CSRF protection)
# --------------------------------------------------------------------------- #

def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _state_signature(payload_b64: str) -> str:
    mac = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    )
    return _b64url(mac.digest())


def create_oauth_state(next_url: Optional[str] = None) -> str:
    """Create a signed state token carrying a nonce and an optional return path."""
    payload = {
        "n": secrets.token_urlsafe(16),
        "t": int(time.time()),
        "next": next_url or "",
    }
    payload_b64 = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    return f"{payload_b64}.{_state_signature(payload_b64)}"


def verify_oauth_state(state: str) -> dict:
    """Validate a state token's signature and age; return its payload."""
    if not state or "." not in state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    payload_b64, signature = state.rsplit(".", 1)
    expected = _state_signature(payload_b64)
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    issued_at = int(payload.get("t", 0))
    if time.time() - issued_at > settings.GOOGLE_STATE_EXPIRE_SECONDS:
        raise HTTPException(status_code=400, detail="OAuth state has expired")
    return payload


# --------------------------------------------------------------------------- #
# Authorization URL + code exchange
# --------------------------------------------------------------------------- #

def build_authorization_url(next_url: Optional[str] = None) -> Tuple[str, str]:
    """Return (authorization_url, state) for the Google consent screen."""
    _require_configured()
    state = create_oauth_state(next_url)
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "include_granted_scopes": "true",
        "prompt": "select_account",
    }
    return f"{settings.GOOGLE_AUTH_URI}?{urlencode(params)}", state


def exchange_code_for_userinfo(code: str) -> dict:
    """Exchange an authorization code for tokens, then fetch the userinfo."""
    _require_configured()
    try:
        token_resp = httpx.post(
            settings.GOOGLE_TOKEN_URI,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            timeout=10.0,
        )
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach Google to verify the sign-in.",
        )

    if token_resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google rejected the authorization code.",
        )
    access_token = token_resp.json().get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google did not return an access token.",
        )

    try:
        info_resp = httpx.get(
            settings.GOOGLE_USERINFO_URI,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10.0,
        )
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach Google to read your profile.",
        )
    if info_resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google did not return your profile.",
        )
    return info_resp.json()


# --------------------------------------------------------------------------- #
# Account resolution
# --------------------------------------------------------------------------- #

class GoogleAccountError(HTTPException):
    """Raised when the Google profile cannot be turned into a local account."""


def _normalized_email(email: str) -> str:
    return (email or "").strip().lower()


def _link_or_create_user(db: Session, profile: dict) -> Tuple[User, str]:
    """Resolve a Google profile to a local user. Returns (user, outcome)."""
    subject = str(profile.get("sub") or "").strip()
    email = _normalized_email(profile.get("email", ""))
    email_verified = bool(profile.get("email_verified"))
    full_name = (profile.get("name") or "").strip() or (email.split("@")[0] if email else "Google User")

    if not subject:
        raise GoogleAccountError(status_code=401, detail="Google profile is missing an account id.")
    if not email:
        raise GoogleAccountError(status_code=401, detail="Google did not provide an email address.")
    if not email_verified:
        # We only link/create by verified email; otherwise anyone could claim an
        # address. Google normally sets this for Gmail/Workspace accounts.
        raise GoogleAccountError(
            status_code=403,
            detail="Your Google email address is not verified.",
        )

    # 1. Exact federated identity match.
    existing = (
        db.query(User)
        .filter(User.oauth_provider == PROVIDER, User.oauth_subject == subject)
        .first()
    )
    if existing is not None:
        if not existing.is_active:
            raise GoogleAccountError(status_code=403, detail="This account is inactive.")
        return existing, "signed_in"

    # 2. Same verified email -> link the Google identity to the local account.
    by_email = (
        db.query(User).filter(func.lower(User.email) == email).first()
    )
    if by_email is not None:
        if not by_email.is_active:
            raise GoogleAccountError(status_code=403, detail="This account is inactive.")
        # If the account is already linked to a *different* Google subject, do
        # not silently steal it.
        if by_email.oauth_subject and by_email.oauth_subject != subject:
            raise GoogleAccountError(
                status_code=409,
                detail="This email is already linked to a different Google account.",
            )
        by_email.oauth_provider = PROVIDER
        by_email.oauth_subject = subject
        db.commit()
        db.refresh(by_email)
        return by_email, "linked"

    # 3. Brand-new account: Google self-provisioning is athlete-only.
    user = User(
        email=email,
        password_hash=_unusable_hash(),
        full_name=full_name,
        role="athlete",
        is_active=True,
        oauth_provider=PROVIDER,
        oauth_subject=subject,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    athlete = Athlete(
        athlete_id=f"ATH{user.id:06d}",
        user_id=user.id,
        sport_type="General",
        age=18,
        height=170.0,
        weight=70.0,
    )
    db.add(athlete)
    db.commit()
    return user, "created"


def authenticate_with_google(db: Session, code: str, ip_address: Optional[str] = None) -> Tuple[User, str]:
    """Full flow: exchange code, resolve account, audit. Returns (user, outcome)."""
    _require_configured()
    profile = exchange_code_for_userinfo(code)
    try:
        user, outcome = _link_or_create_user(db, profile)
    except GoogleAccountError as exc:
        log_security_event(
            event_type="GOOGLE_SIGNIN_FAILED",
            user_email=_normalized_email(profile.get("email", "")),
            ip_address=ip_address,
            details={"reason": exc.detail},
            success=False,
        )
        raise

    log_security_event(
        event_type="GOOGLE_SIGNIN",
        user_id=user.id,
        user_email=user.email,
        ip_address=ip_address,
        details={"outcome": outcome},
        success=True,
    )
    return user, outcome
