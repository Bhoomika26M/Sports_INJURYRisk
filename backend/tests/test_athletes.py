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
