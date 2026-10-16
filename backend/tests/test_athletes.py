"""Athlete endpoint tests — CRUD, RBAC, injuries, training load, ACWR."""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, register_and_login


async def _coach(client: AsyncClient) -> str:
    return await register_and_login(client, "coach@test.com", "coach")


async def _make_athlete(client: AsyncClient, token: str, **kw) -> dict:
    data = {"sport_type": "basketball", "date_of_birth": "2000-01-15",
            "height_cm": 185.5, "weight_kg": 82.0, "dominant_side": "right"}
    data.update(kw)
    resp = await client.post("/api/v1/athletes", json=data, headers=auth_header(token))
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_create_and_get_athlete(client: AsyncClient):
    token = await _coach(client)
    athlete = await _make_athlete(client, token)
    resp = await client.get(f"/api/v1/athletes/{athlete['id']}", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["sport_type"] == "basketball"


@pytest.mark.asyncio
async def test_athlete_role_cannot_create(client: AsyncClient):
    token = await register_and_login(client, "a@test.com", "athlete")
    resp = await client.post("/api/v1/athletes", json={"sport_type": "soccer", "date_of_birth": "2001-05-05"},
                             headers=auth_header(token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_unrelated_athlete_cannot_read(client: AsyncClient):
    coach_token = await _coach(client)
    athlete = await _make_athlete(client, coach_token)
    other = await register_and_login(client, "other@test.com", "athlete")
    resp = await client.get(f"/api/v1/athletes/{athlete['id']}", headers=auth_header(other))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_injury_crud(client: AsyncClient):
    token = await _coach(client)
    athlete = await _make_athlete(client, token)
    resp = await client.post(f"/api/v1/athletes/{athlete['id']}/injuries", json={
        "injury_type": "ACL tear", "body_part": "left knee",
        "injury_date": "2025-06-15", "severity": "severe",
    }, headers=auth_header(token))
    assert resp.status_code == 201
    injury_id = resp.json()["id"]
    listed = await client.get(f"/api/v1/athletes/{athlete['id']}/injuries", headers=auth_header(token))
    assert listed.json()["total"] == 1
    await client.delete(f"/api/v1/athletes/{athlete['id']}/injuries/{injury_id}", headers=auth_header(token))
    listed = await client.get(f"/api/v1/athletes/{athlete['id']}/injuries", headers=auth_header(token))
    assert listed.json()["total"] == 0


@pytest.mark.asyncio
async def test_training_load_and_acwr(client: AsyncClient):
    token = await _coach(client)
    athlete = await _make_athlete(client, token)
    resp = await client.post(f"/api/v1/athletes/{athlete['id']}/training-load", json={
        "entry_date": "2025-07-01", "session_type": "strength",
        "duration_minutes": 90, "rpe": 15,
    }, headers=auth_header(token))
    assert resp.status_code == 422  # RPE out of range
    resp = await client.post(f"/api/v1/athletes/{athlete['id']}/training-load", json={
        "entry_date": "2025-07-01", "session_type": "strength",
        "duration_minutes": 90, "rpe": 7,
    }, headers=auth_header(token))
    assert resp.status_code == 201
    assert resp.json()["session_load"] == 630.0
    acwr = await client.get(f"/api/v1/athletes/{athlete['id']}/acwr", headers=auth_header(token))
    assert acwr.status_code == 200
    assert "acwr" in acwr.json()


@pytest.mark.asyncio
async def test_create_and_update_athlete_name_and_email(client: AsyncClient):
    token = await _coach(client)
    # 1. Create with name and email
    resp = await client.post("/api/v1/athletes", json={
        "full_name": "Marcus Rashford",
        "email": "marcus@england.com",
        "sport_type": "soccer",
        "date_of_birth": "1997-10-31",
    }, headers=auth_header(token))
    assert resp.status_code == 201
    data = resp.json()
    assert data["full_name"] == "Marcus Rashford"
    assert data["email"] == "marcus@england.com"
    athlete_id = data["id"]

    # 2. Update name and email
    update_resp = await client.put(f"/api/v1/athletes/{athlete_id}", json={
        "full_name": "Marcus Rashford MBE",
        "email": "rashford@manutd.com",
    }, headers=auth_header(token))
    assert update_resp.status_code == 200
    up_data = update_resp.json()
    assert up_data["full_name"] == "Marcus Rashford MBE"
    assert up_data["email"] == "rashford@manutd.com"

    # 3. Get athlete profile confirms updated properties
    get_resp = await client.get(f"/api/v1/athletes/{athlete_id}", headers=auth_header(token))
    assert get_resp.status_code == 200
    assert get_resp.json()["full_name"] == "Marcus Rashford MBE"
    assert get_resp.json()["email"] == "rashford@manutd.com"


@pytest.mark.asyncio
async def test_link_existing_user_athlete(client: AsyncClient):
    # Athlete signs up first
    athlete_token = await register_and_login(client, "pro.runner@track.com", "athlete")
    coach_token = await _coach(client)

    # Coach adds athlete with that email
    resp = await client.post("/api/v1/athletes", json={
        "full_name": "Pro Runner",
        "email": "pro.runner@track.com",
        "sport_type": "track",
        "date_of_birth": "1999-04-12",
    }, headers=auth_header(coach_token))
    assert resp.status_code == 201
    athlete_id = resp.json()["id"]

    # The athlete can now see their linked profile
    my_profile = await client.get(f"/api/v1/athletes/{athlete_id}", headers=auth_header(athlete_token))
    assert my_profile.status_code == 200
    assert my_profile.json()["email"] == "pro.runner@track.com"

