"""Google OAuth2 authorization-code flow (Defect 5).

Google is never contacted: `exchange_google_code` / `get_google_user_info` are replaced, and the
exchange function's own error mapping is tested against httpx.MockTransport.
"""

from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.config import settings
from app.modules.auth import service
from app.modules.auth.schemas import GoogleUserInfo
from app.modules.auth.service import OAuthError
from app.modules.users.models import NotificationPreference, RefreshToken, User

CALLBACK = "/api/v1/auth/google/callback"
STATE = "s" * 43   # shape of secrets.token_urlsafe(32)


@pytest.fixture(autouse=True)
def google_configured(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "test-client-id.apps.googleusercontent.com")
    monkeypatch.setattr(settings, "google_client_secret", "test-secret")
    monkeypatch.setattr(settings, "frontend_url", "http://localhost:3000")
    monkeypatch.setattr(settings, "cookie_secure", True)


def fake_google(monkeypatch, *, sub="g-sub-1", email="gina@example.com", verified=True, name="Gina Google"):
    calls = {"exchange": 0, "userinfo": 0}

    async def exchange(code, redirect_uri):
        calls["exchange"] += 1
        assert redirect_uri == settings.google_redirect_uri
        return "google-access-token"

    async def userinfo(access_token):
        calls["userinfo"] += 1
        return GoogleUserInfo(sub=sub, email=email, name=name, picture="http://x/p.png", email_verified=verified)

    monkeypatch.setattr(service, "exchange_google_code", exchange)
    monkeypatch.setattr(service, "get_google_user_info", userinfo)
    return calls


async def callback(client: AsyncClient, **overrides):
    params = {"code": "auth-code", "state": STATE}
    cookies = {"oauth_state": STATE}
    for k, v in overrides.items():
        if k == "cookie_state":
            cookies = {} if v is None else {"oauth_state": v}
        elif v is None:
            params.pop(k, None)
        else:
            params[k] = v
    return await client.get(CALLBACK, params=params, cookies=cookies)


def set_cookie_headers(resp) -> list[str]:
    return resp.headers.get_list("set-cookie")


def refresh_cookie(resp) -> str | None:
    for h in set_cookie_headers(resp):
        if h.startswith("refresh_token=") and "Max-Age=0" not in h:
            return h
    return None


async def user_count(db, email) -> int:
    return await db.scalar(select(func.count()).select_from(User).where(User.email == email))


def assert_rejected(resp, code):
    assert resp.status_code == 302
    loc = urlparse(resp.headers["location"])
    assert f"{loc.scheme}://{loc.netloc}{loc.path}" == "http://localhost:3000/login"
    assert parse_qs(loc.query) == {"error": [code]}
    assert refresh_cookie(resp) is None, "a rejected sign-in must never issue a session"


# ---- start of the flow --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_start_is_a_real_redirect_to_google_with_state(client: AsyncClient):
    resp = await client.get("/api/v1/auth/google")
    assert resp.status_code == 302                                   # was a 200 JSON body {"url": ...}
    url = urlparse(resp.headers["location"])
    assert f"{url.scheme}://{url.netloc}{url.path}" == "https://accounts.google.com/o/oauth2/v2/auth"
    q = parse_qs(url.query)
    assert q["client_id"] == ["test-client-id.apps.googleusercontent.com"]
    assert q["response_type"] == ["code"] and q["scope"] == ["openid email profile"]
    assert q["redirect_uri"] == [settings.google_redirect_uri]
    assert "access_type" not in q                                    # we never use Google refresh tokens
    state = q["state"][0]
    assert len(state) >= 32

    cookie = next(h for h in set_cookie_headers(resp) if h.startswith("oauth_state="))
    assert cookie.startswith(f"oauth_state={state};")
    assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=lax" in cookie


@pytest.mark.asyncio
async def test_each_start_gets_a_fresh_state(client: AsyncClient):
    states = {parse_qs(urlparse((await client.get("/api/v1/auth/google")).headers["location"]).query)["state"][0] for _ in range(5)}
    assert len(states) == 5


@pytest.mark.asyncio
async def test_start_returns_503_when_google_is_not_configured(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", None)
    resp = await client.get("/api/v1/auth/google")
    assert resp.status_code == 503
    assert resp.json()["detail"]["error"]["code"] == "OAUTH_NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_old_post_callback_is_gone(client: AsyncClient):
    """The POST-with-JSON callback could never be reached by Google and had no state check."""
    resp = await client.post(CALLBACK, json={"code": "x", "redirect_uri": "http://x"})
    assert resp.status_code == 405


# ---- happy path ---------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_callback_happy_path_sets_httponly_refresh_cookie_and_redirects_to_frontend(client, db_session, monkeypatch):
    calls = fake_google(monkeypatch)
    resp = await callback(client)

    assert resp.status_code == 302
    assert resp.headers["location"] == "http://localhost:3000/auth/callback"   # no code, no token in the URL
    cookie = refresh_cookie(resp)
    assert cookie and "HttpOnly" in cookie and "Secure" in cookie and "SameSite=lax" in cookie
    assert "Path=/api/v1/auth" in cookie
    assert any(h.startswith("oauth_state=") and "Max-Age=0" in h for h in set_cookie_headers(resp))  # state is single-use
    assert calls == {"exchange": 1, "userinfo": 1}

    user = await db_session.scalar(select(User).where(User.email == "gina@example.com"))
    assert user.google_id == "g-sub-1" and user.role.value == "athlete"
    token_value = cookie.split(";")[0].split("=", 1)[1]
    stored = await db_session.scalar(select(RefreshToken).where(RefreshToken.user_id == user.id))
    assert stored.token_hash != token_value and stored.token_hash.startswith("$argon2")   # hash only, never the token


@pytest.mark.asyncio
async def test_session_is_established_via_the_cookie_the_frontend_callback_page_uses(client, monkeypatch):
    fake_google(monkeypatch)
    token_value = refresh_cookie(await callback(client)).split(";")[0].split("=", 1)[1]

    refreshed = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": token_value})
    assert refreshed.status_code == 200
    access = refreshed.json()["access_token"]
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 200 and me.json()["email"] == "gina@example.com"


# ---- CSRF: state --------------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("overrides", [
    {"state": "x" * 43},          # query state differs from cookie
    {"cookie_state": None},       # no state cookie (attacker-initiated flow)
    {"cookie_state": "y" * 43},   # cookie differs from query
    {"state": None},              # no state in the query
], ids=["mismatch", "no_cookie", "cookie_differs", "no_query_state"])
async def test_state_mismatch_is_rejected_before_anything_else(client, db_session, monkeypatch, overrides):
    calls = fake_google(monkeypatch)
    resp = await callback(client, **overrides)
    assert_rejected(resp, "oauth_state_mismatch")
    assert calls == {"exchange": 0, "userinfo": 0}, "the code must not be exchanged when state fails"
    assert await user_count(db_session, "gina@example.com") == 0


@pytest.mark.asyncio
async def test_consent_denied_is_reported_without_exchanging_anything(client, monkeypatch):
    calls = fake_google(monkeypatch)
    assert_rejected(await callback(client, code=None, error="access_denied"), "oauth_denied")
    assert calls["exchange"] == 0


@pytest.mark.asyncio
async def test_error_param_with_bad_state_still_reports_state_failure(client, monkeypatch):
    fake_google(monkeypatch)
    assert_rejected(await callback(client, code=None, error="access_denied", state="z" * 43), "oauth_state_mismatch")


@pytest.mark.asyncio
async def test_missing_code_with_valid_state_is_rejected(client, monkeypatch):
    calls = fake_google(monkeypatch)
    assert_rejected(await callback(client, code=None), "oauth_missing_code")
    assert calls["exchange"] == 0


# ---- invalid / expired code ---------------------------------------------------------------------

@pytest.mark.asyncio
async def test_invalid_or_expired_code_is_rejected(client, db_session, monkeypatch):
    async def exchange(code, redirect_uri):
        raise OAuthError("oauth_code_invalid", "The Google sign-in code was rejected or has expired")

    monkeypatch.setattr(service, "exchange_google_code", exchange)
    assert_rejected(await callback(client, code="expired-or-forged"), "oauth_code_invalid")
    assert await db_session.scalar(select(func.count()).select_from(User)) == 0


@pytest.mark.asyncio
async def test_exchange_maps_google_400_invalid_grant_to_oauth_code_invalid(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "oauth2.googleapis.com"
        return httpx.Response(400, json={"error": "invalid_grant", "error_description": "Bad Request"})

    real = httpx.AsyncClient
    monkeypatch.setattr(service.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    with pytest.raises(OAuthError) as exc:
        await service.exchange_google_code("expired", settings.google_redirect_uri)
    assert exc.value.code == "oauth_code_invalid"


@pytest.mark.asyncio
async def test_exchange_maps_network_failure_to_provider_unavailable(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    real = httpx.AsyncClient
    monkeypatch.setattr(service.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    with pytest.raises(OAuthError) as exc:
        await service.exchange_google_code("c", settings.google_redirect_uri)
    assert exc.value.code == "oauth_provider_unavailable"


# ---- account linking ----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_already_linked_account_logs_in_instead_of_duplicating(client, db_session, monkeypatch):
    fake_google(monkeypatch)
    await callback(client)
    first = await db_session.scalar(select(User).where(User.email == "gina@example.com"))
    second_resp = await callback(client)

    assert second_resp.status_code == 302 and second_resp.headers["location"].endswith("/auth/callback")
    assert refresh_cookie(second_resp) is not None
    assert await user_count(db_session, "gina@example.com") == 1
    assert await db_session.scalar(select(func.count()).select_from(User).where(User.google_id == "g-sub-1")) == 1
    prefs = await db_session.scalar(select(func.count()).select_from(NotificationPreference).where(NotificationPreference.user_id == first.id))
    assert prefs == 5, "notification defaults must not be created twice"


@pytest.mark.asyncio
async def test_existing_password_account_is_linked_not_duplicated(client, db_session, monkeypatch):
    reg = await client.post("/api/v1/auth/register", json={
        "email": "gina@example.com", "password": "testpassword123", "full_name": "Gina P", "role": "coach"})
    assert reg.status_code == 201
    fake_google(monkeypatch)
    assert (await callback(client)).headers["location"].endswith("/auth/callback")

    users = (await db_session.scalars(select(User).where(User.email == "gina@example.com"))).all()
    assert len(users) == 1 and users[0].google_id == "g-sub-1" and users[0].role.value == "coach"
    login = await client.post("/api/v1/auth/login", json={"email": "gina@example.com", "password": "testpassword123"})
    assert login.status_code == 200, "linking must not break the password login"


# ---- auth failures ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unverified_google_email_cannot_take_over_an_existing_account(client, db_session, monkeypatch):
    await client.post("/api/v1/auth/register", json={
        "email": "victim@example.com", "password": "testpassword123", "full_name": "Victim", "role": "coach"})
    fake_google(monkeypatch, sub="attacker-sub", email="victim@example.com", verified=False)
    assert_rejected(await callback(client), "oauth_email_unverified")
    victim = await db_session.scalar(select(User).where(User.email == "victim@example.com"))
    assert victim.google_id is None


@pytest.mark.asyncio
async def test_account_linked_to_a_different_google_subject_is_not_reused(client, db_session, monkeypatch):
    fake_google(monkeypatch, sub="original-sub")
    await callback(client)
    fake_google(monkeypatch, sub="someone-else-sub")
    assert_rejected(await callback(client), "oauth_account_conflict")


@pytest.mark.asyncio
async def test_deactivated_account_cannot_sign_in_with_google(client, db_session, monkeypatch):
    fake_google(monkeypatch)
    await callback(client)
    user = await db_session.scalar(select(User).where(User.email == "gina@example.com"))
    user.is_active = False
    await db_session.commit()
    assert_rejected(await callback(client), "oauth_account_disabled")


@pytest.mark.asyncio
async def test_refresh_with_an_unknown_cookie_is_401(client):
    resp = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": "not-a-real-token"})
    assert resp.status_code == 401


# ---- validation (422) ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("param", ["state", "code", "error"])
async def test_oversized_callback_parameters_are_422(client, monkeypatch, param):
    fake_google(monkeypatch)
    resp = await client.get(CALLBACK, params={param: "a" * 5000}, cookies={"oauth_state": STATE})
    assert resp.status_code == 422


# ---- cookie attributes on the existing password flow (same non-negotiable rule) -----------------

@pytest.mark.asyncio
async def test_password_login_refresh_cookie_is_httponly_secure_samesite_lax(client):
    await client.post("/api/v1/auth/register", json={
        "email": "pw@example.com", "password": "testpassword123", "full_name": "Pw", "role": "coach"})
    resp = await client.post("/api/v1/auth/login", json={"email": "pw@example.com", "password": "testpassword123"})
    cookie = refresh_cookie(resp)
    assert cookie and "HttpOnly" in cookie and "Secure" in cookie and "SameSite=lax" in cookie
    assert "refresh_token" not in resp.text
