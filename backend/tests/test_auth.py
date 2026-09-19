"""Auth endpoint tests — register, login, refresh, logout, /me."""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, create_test_user, login_test_user


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """Register a new user — should return 201 with user data."""
    response = await create_test_user(client)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test User"
    assert data["role"] == "coach"
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Registering the same email twice — should return 409, not 500."""
    await create_test_user(client)
    response = await create_test_user(client)
    assert response.status_code == 409
    data = response.json()
    assert data["detail"]["error"]["code"] == "DUPLICATE_EMAIL"


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    """Invalid email format — should return 422."""
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "testpass123", "full_name": "Test", "role": "coach"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    """Password too short — should return 422."""
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "short", "full_name": "Test", "role": "coach"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Login with correct credentials — should return access token."""
    await create_test_user(client)
    response = await login_test_user(client)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    # Refresh token should be in a cookie, not the body
    assert "refresh_token" not in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Login with wrong password — should return 401, never a token."""
    await create_test_user(client)
    response = await login_test_user(client, password="wrongpassword")
    assert response.status_code == 401
    data = response.json()
    assert data["detail"]["error"]["code"] == "INVALID_CREDENTIALS"
    assert "access_token" not in data


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Login with non-existent email — should return 401."""
    response = await login_test_user(client, email="nonexistent@example.com")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_token(client: AsyncClient):
    """/me with valid token — should return 200 with user data."""
    await create_test_user(client)
    login_resp = await login_test_user(client)
    token = login_resp.json()["access_token"]

    response = await client.get("/api/v1/auth/me", headers=auth_header(token))
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["role"] == "coach"


@pytest.mark.asyncio
async def test_me_without_token(client: AsyncClient):
    """/me without token — should return 401."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_invalid_token(client: AsyncClient):
    """/me with garbage token — should return 401."""
    response = await client.get("/api/v1/auth/me", headers=auth_header("garbage.token.here"))
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    """Refresh — should return new access token."""
    await create_test_user(client)
    login_resp = await login_test_user(client)

    # Extract refresh token from cookie
    refresh_cookie = login_resp.cookies.get("refresh_token")
    assert refresh_cookie is not None

    # Use refresh token
    response = await client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": refresh_cookie},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_refresh_token_rotation(client: AsyncClient):
    """After refresh, the old refresh token should be rejected (rotation)."""
    await create_test_user(client)
    login_resp = await login_test_user(client)
    old_refresh = login_resp.cookies.get("refresh_token")

    # Use refresh token once
    await client.post("/api/v1/auth/refresh", cookies={"refresh_token": old_refresh})

    # Try to use the same refresh token again — should fail
    response = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": old_refresh})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_then_reuse_refresh(client: AsyncClient):
    """After logout, the refresh token should be rejected."""
    await create_test_user(client)
    login_resp = await login_test_user(client)
    refresh_cookie = login_resp.cookies.get("refresh_token")

    # Logout
    await client.post("/api/v1/auth/logout", cookies={"refresh_token": refresh_cookie})

    # Try to use the revoked refresh token
    response = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": refresh_cookie})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_register_all_roles(client: AsyncClient):
    """Can register users with all 5 roles."""
    roles = ["athlete", "coach", "physiotherapist", "sports_scientist", "admin"]
    for i, role in enumerate(roles):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"user{i}@example.com",
                "password": "testpassword123",
                "full_name": f"User {role}",
                "role": role,
            },
        )
        assert response.status_code == 201, f"Failed to register role: {role}"
        assert response.json()["role"] == role
