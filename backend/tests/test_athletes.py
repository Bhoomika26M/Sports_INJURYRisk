"""Athlete endpoint tests — CRUD, RBAC, injury history, training load."""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, create_test_user, login_test_user


async def _register_and_login(client: AsyncClient, email: str, role: str) -> str:
    """Register a user, login, return access token."""
    await create_test_user(client, email=email, role=role, full_name=f"Test {role}")
    resp = await login_test_user(client, email=email)
    return resp.json()["access_token"]


async def _create_athlete(client: AsyncClient, token: str, **overrides) -> dict:
    """Create an athlete and return the response data."""
    data = {
        "sport_type": "basketball",
        "date_of_birth": "2000-01-15",
        "height_cm": 185.5,
        "weight_kg": 82.0,
        "dominant_side": "right",
    }
    data.update(overrides)
    resp = await client.post(
        "/api/v1/athletes",
        json=data,
        headers=auth_header(token),
    )
    return resp


# --- Athlete CRUD ---

@pytest.mark.asyncio
async def test_create_athlete_as_coach(client: AsyncClient):
    """Coach can create an athlete — 201."""
    token = await _register_and_login(client, "coach@test.com", "coach")
    resp = await _create_athlete(client, token)
    assert resp.status_code == 201
    data = resp.json()
    assert data["sport_type"] == "basketball"
    assert data["dominant_side"] == "right"


@pytest.mark.asyncio
async def test_create_athlete_as_athlete_denied(client: AsyncClient):
    """Athlete role cannot create athlete profiles — 403."""
    token = await _register_and_login(client, "athlete@test.com", "athlete")
    resp = await _create_athlete(client, token)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_athlete_as_admin(client: AsyncClient):
    """Admin can create athlete profiles — 201."""
    token = await _register_and_login(client, "admin@test.com", "admin")
    resp = await _create_athlete(client, token)
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_list_athletes(client: AsyncClient):
    """List athletes — 200 with paginated response."""
    token = await _register_and_login(client, "coach@test.com", "coach")
    await _create_athlete(client, token)
    await _create_athlete(client, token, sport_type="soccer")

    resp = await client.get("/api/v1/athletes", headers=auth_header(token))
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data


@pytest.mark.asyncio
async def test_get_athlete_as_admin(client: AsyncClient):
    """Admin can get any athlete — 200."""
    coach_token = await _register_and_login(client, "coach@test.com", "coach")
    create_resp = await _create_athlete(client, coach_token)
    athlete_id = create_resp.json()["id"]

    admin_token = await _register_and_login(client, "admin@test.com", "admin")
    resp = await client.get(f"/api/v1/athletes/{athlete_id}", headers=auth_header(admin_token))
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_athlete_as_unrelated_athlete_denied(client: AsyncClient):
    """An athlete user who isn't linked to this athlete record — 403."""
    coach_token = await _register_and_login(client, "coach@test.com", "coach")
    create_resp = await _create_athlete(client, coach_token)
    athlete_id = create_resp.json()["id"]

    athlete_token = await _register_and_login(client, "athlete@test.com", "athlete")
    resp = await client.get(f"/api/v1/athletes/{athlete_id}", headers=auth_header(athlete_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_nonexistent_athlete(client: AsyncClient):
    """Get a non-existent athlete — 404."""
    token = await _register_and_login(client, "admin@test.com", "admin")
    resp = await client.get(
        "/api/v1/athletes/00000000-0000-0000-0000-000000000000",
        headers=auth_header(token),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_athlete_as_admin(client: AsyncClient):
    """Admin can update any athlete — 200."""
    coach_token = await _register_and_login(client, "coach@test.com", "coach")
    create_resp = await _create_athlete(client, coach_token)
    athlete_id = create_resp.json()["id"]

    admin_token = await _register_and_login(client, "admin@test.com", "admin")
    resp = await client.put(
        f"/api/v1/athletes/{athlete_id}",
        json={"sport_type": "tennis"},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["sport_type"] == "tennis"


@pytest.mark.asyncio
async def test_delete_athlete_as_admin(client: AsyncClient):
    """Admin can delete an athlete — 204."""
    coach_token = await _register_and_login(client, "coach@test.com", "coach")
    create_resp = await _create_athlete(client, coach_token)
    athlete_id = create_resp.json()["id"]

    admin_token = await _register_and_login(client, "admin@test.com", "admin")
    resp = await client.delete(f"/api/v1/athletes/{athlete_id}", headers=auth_header(admin_token))
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_athlete_as_coach_denied(client: AsyncClient):
    """Coach cannot delete athletes — 403."""
    coach_token = await _register_and_login(client, "coach@test.com", "coach")
    create_resp = await _create_athlete(client, coach_token)
    athlete_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/athletes/{athlete_id}", headers=auth_header(coach_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_access(client: AsyncClient):
    """No token — 401 on all endpoints."""
    resp = await client.get("/api/v1/athletes")
    assert resp.status_code == 401
    resp = await client.post("/api/v1/athletes", json={})
    assert resp.status_code == 401


# --- Injury History ---

@pytest.mark.asyncio
async def test_create_and_list_injuries(client: AsyncClient):
    """Coach can create and list injuries for their athlete."""
    token = await _register_and_login(client, "coach@test.com", "coach")
    create_resp = await _create_athlete(client, token)
    athlete_id = create_resp.json()["id"]

    # Create injury
    resp = await client.post(
        f"/api/v1/athletes/{athlete_id}/injuries",
        json={
            "injury_type": "ACL tear",
            "body_part": "left knee",
            "injury_date": "2025-06-15",
            "severity": "severe",
            "notes": "Non-contact injury during game",
        },
        headers=auth_header(token),
    )
    assert resp.status_code == 201
    assert resp.json()["injury_type"] == "ACL tear"

    # List injuries
    resp = await client.get(
        f"/api/v1/athletes/{athlete_id}/injuries",
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1


@pytest.mark.asyncio
async def test_delete_injury(client: AsyncClient):
    """Delete an injury record — 204."""
    token = await _register_and_login(client, "admin@test.com", "admin")
    create_resp = await _create_athlete(client, token)
    athlete_id = create_resp.json()["id"]

    injury_resp = await client.post(
        f"/api/v1/athletes/{athlete_id}/injuries",
        json={
            "injury_type": "Sprain",
            "body_part": "ankle",
            "injury_date": "2025-03-01",
            "severity": "minor",
        },
        headers=auth_header(token),
    )
    injury_id = injury_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/athletes/{athlete_id}/injuries/{injury_id}",
        headers=auth_header(token),
    )
    assert resp.status_code == 204


# --- Training Load ---

@pytest.mark.asyncio
async def test_create_and_list_training_load(client: AsyncClient):
    """Create and list training load entries."""
    token = await _register_and_login(client, "coach@test.com", "coach")
    create_resp = await _create_athlete(client, token)
    athlete_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/athletes/{athlete_id}/training-load",
        json={
            "entry_date": "2025-07-01",
            "session_type": "strength",
            "duration_minutes": 90,
            "rpe": 7,
            "notes": "Heavy squat session",
        },
        headers=auth_header(token),
    )
    assert resp.status_code == 201
    assert resp.json()["rpe"] == 7

    resp = await client.get(
        f"/api/v1/athletes/{athlete_id}/training-load",
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


@pytest.mark.asyncio
async def test_training_load_invalid_rpe(client: AsyncClient):
    """RPE outside 1-10 — 422."""
    token = await _register_and_login(client, "coach@test.com", "coach")
    create_resp = await _create_athlete(client, token)
    athlete_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/athletes/{athlete_id}/training-load",
        json={
            "entry_date": "2025-07-01",
            "rpe": 15,
        },
        headers=auth_header(token),
    )
    assert resp.status_code == 422
