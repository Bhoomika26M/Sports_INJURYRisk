"""Auth endpoint tests — register, login, refresh rotation, /me, RBAC."""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, register_and_login


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "new@test.com", "password": "testpassword123",
        "full_name": "New User", "role": "coach",
    })
    assert resp.status_code == 201, resp.text
    assert resp.json()["email"] == "new@test.com"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    await register_and_login(client, "dup@test.com", "coach")
    resp = await client.post("/api/v1/auth/register", json={
        "email": "dup@test.com", "password": "testpassword123",
        "full_name": "Dup", "role": "coach",
    })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_invalid_email_and_short_password(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "not-an-email", "password": "testpassword123",
        "full_name": "X", "role": "coach",
    })
    assert resp.status_code == 422
    resp = await client.post("/api/v1/auth/register", json={
        "email": "ok@test.com", "password": "short",
        "full_name": "X", "role": "coach",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await register_and_login(client, "coach@test.com", "coach")
    resp = await client.post("/api/v1/auth/login", json={"email": "coach@test.com", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_with_and_without_token(client: AsyncClient):
    token = await register_and_login(client, "me@test.com", "coach")
    resp = await client.get("/api/v1/auth/me", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["role"] == "coach"
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rotation(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "r@test.com", "password": "testpassword123",
        "full_name": "R", "role": "coach",
    })
    login = await client.post("/api/v1/auth/login", json={"email": "r@test.com", "password": "testpassword123"})
    old_refresh = login.cookies.get("refresh_token")
    assert old_refresh is not None
    first = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": old_refresh})
    assert first.status_code == 200
    second = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": old_refresh})
    assert second.status_code == 401


@pytest.mark.asyncio
async def test_google_login_redirects_to_google_when_configured(client: AsyncClient, monkeypatch):
    # Was: 200 + JSON {"url": ...}, which a browser navigation renders as raw JSON. Full coverage of the
    # flow (state, callback, linking, failures) lives in tests/test_google_oauth.py.
    from app.config import settings
    monkeypatch.setattr(settings, "google_client_id", "cid")
    monkeypatch.setattr(settings, "google_client_secret", "secret")
    resp = await client.get("/api/v1/auth/google")
    assert resp.status_code == 302
    assert resp.headers["location"].startswith("https://accounts.google.com/")
