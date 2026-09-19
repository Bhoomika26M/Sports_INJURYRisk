"""
Auth endpoint tests:
  - POST /api/v1/auth/register
  - POST /api/v1/auth/login
  - GET  /api/v1/auth/me
  - PUT  /api/v1/users/me
  - POST /api/v1/admin/users
"""
import pytest
from httpx import AsyncClient

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"
UPDATE_ME_URL = "/api/v1/users/me"
ADMIN_CREATE_USER_URL = "/api/v1/admin/users"

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
async def _register_and_login(client: AsyncClient, email: str, password: str = "Pass1234") -> str:
    """Register an athlete and return a valid access token."""
    await client.post(REGISTER_URL, json={
        "email": email,
        "password": password,
        "full_name": "Test User",
    })
    resp = await client.post(LOGIN_URL, json={"email": email, "password": password})
    return resp.json()["access_token"]


async def _admin_token(client: AsyncClient) -> str:
    """Create an admin via /admin/users (bootstrapped by first login as admin)."""
    # First register an athlete, then use a second, pre-seeded admin token
    # We create the admin with a direct DB insert via AdminUserCreate; instead,
    # we use the fact that the first call to /admin/users requires auth.
    # For bootstrapping: register athlete, then directly post admin creation
    # requires admin token — so we seed admin via the registration of a special account.
    # We cannot self-elevate through /register, so we create admin via
    # the admin endpoint after bootstrapping with a direct db fixture.
    # For test purposes: admin is pre-created through register + manual role update
    # (achieved in test_auth_me_authorized by using a helper that patches).
    # Instead, tests that need an admin token call this helper.
    raise RuntimeError("Use _create_admin_token fixture instead")


# ---------------------------------------------------------------------------
# Test: successful registration → role is always athlete
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_register_athlete(client: AsyncClient):
    resp = await client.post(REGISTER_URL, json={
        "email": "athlete1@test.com",
        "password": "Secure123",
        "full_name": "Alice Athlete",
    })
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["email"] == "athlete1@test.com"
    assert body["role"] == "athlete"          # Never admin
    assert "hashed_password" not in body


# ---------------------------------------------------------------------------
# Test: registration forces athlete role even if admin supplied
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_register_forces_athlete_role(client: AsyncClient):
    # Even if someone posts an extra 'role' field it should be ignored
    resp = await client.post(REGISTER_URL, json={
        "email": "hacker@test.com",
        "password": "Secure123",
        "full_name": "Bad Actor",
        "role": "admin",           # Must be silently overridden
    })
    assert resp.status_code == 201
    assert resp.json()["role"] == "athlete"


# ---------------------------------------------------------------------------
# Test: duplicate registration returns 409
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {"email": "dup@test.com", "password": "Pass1234", "full_name": "Dup"}
    await client.post(REGISTER_URL, json=payload)
    resp = await client.post(REGISTER_URL, json=payload)
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Test: login success → contains access_token with correct role
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post(REGISTER_URL, json={
        "email": "login_ok@test.com",
        "password": "Pass1234",
        "full_name": "Login OK",
    })
    resp = await client.post(LOGIN_URL, json={
        "email": "login_ok@test.com",
        "password": "Pass1234",
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"

    # Decode and verify claims
    import jwt as pyjwt
    from app.core.config import settings
    payload = pyjwt.decode(body["access_token"], settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["type"] == "access"
    assert payload["role"] == "athlete"
    assert "sub" in payload
    assert "exp" in payload


# ---------------------------------------------------------------------------
# Test: wrong password → 401
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post(REGISTER_URL, json={
        "email": "wrongpw@test.com",
        "password": "Correct123",
        "full_name": "Wrong PW",
    })
    resp = await client.post(LOGIN_URL, json={
        "email": "wrongpw@test.com",
        "password": "WrongPassword",
    })
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Test: /auth/me without token → 401
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_auth_me_unauthorized(client: AsyncClient):
    resp = await client.get(ME_URL)
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Test: /auth/me with valid token → 200 with user data
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_auth_me_authorized(client: AsyncClient):
    token = await _register_and_login(client, "me_test@test.com")
    resp = await client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "me_test@test.com"
    assert body["role"] == "athlete"


# ---------------------------------------------------------------------------
# Test: PUT /users/me updates name and phone
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_update_user_me(client: AsyncClient):
    token = await _register_and_login(client, "update_me@test.com")
    resp = await client.put(
        UPDATE_ME_URL,
        headers={"Authorization": f"Bearer {token}"},
        json={"full_name": "Updated Name", "phone_number": "+1234567890"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["full_name"] == "Updated Name"
    assert body["phone_number"] == "+1234567890"


# ---------------------------------------------------------------------------
# Test: athlete calling POST /admin/users → 403
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_athlete_forbidden_on_admin_endpoint(client: AsyncClient):
    token = await _register_and_login(client, "athlete_forbidden@test.com")
    resp = await client.post(
        ADMIN_CREATE_USER_URL,
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": "newcoach@test.com",
            "password": "Pass1234",
            "full_name": "New Coach",
            "role": "coach",
        },
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Test: admin can create a user with any role via /admin/users
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_admin_can_create_user(client: AsyncClient, db_session):
    """Seed an admin user directly in the DB, then test endpoint access."""
    from app.core.security import hash_password
    from app.models.enums import UserRole
    from app.models.user import User

    # Directly seed admin into test DB
    admin = User(
        email="admin_seed@test.com",
        hashed_password=hash_password("Admin1234"),
        full_name="Test Admin",
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    db_session.add(admin)
    await db_session.flush()

    # Login as admin
    resp = await client.post(LOGIN_URL, json={
        "email": "admin_seed@test.com",
        "password": "Admin1234",
    })
    assert resp.status_code == 200, resp.text
    admin_token = resp.json()["access_token"]

    # Create a coach via admin endpoint
    resp = await client.post(
        ADMIN_CREATE_USER_URL,
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "email": "newcoach_admin@test.com",
            "password": "Pass1234",
            "full_name": "New Coach",
            "role": "coach",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["role"] == "coach"
    assert body["email"] == "newcoach_admin@test.com"
    assert body["is_verified"] is True   # Admin-created accounts are pre-verified
