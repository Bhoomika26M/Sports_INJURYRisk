"""Video API tests — movement registry, upload-url validation and gating."""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, register_and_login


async def _coach_with_athlete(client: AsyncClient):
    token = await register_and_login(client, "coach@test.com", "coach")
    resp = await client.post("/api/v1/athletes", json={
        "sport_type": "basketball", "date_of_birth": "2000-01-15",
    }, headers=auth_header(token))
    assert resp.status_code == 201, resp.text
    return token, resp.json()["id"]


@pytest.mark.asyncio
async def test_movement_types_registry(client: AsyncClient):
    token = await register_and_login(client, "c@test.com", "coach")
    resp = await client.get("/api/v1/videos/movement-types", headers=auth_header(token))
    assert resp.status_code == 200
    codes = {m["code"] for m in resp.json()}
    assert {"squatting", "landing", "running", "sprinting", "jumping", "throwing", "cutting"} <= codes
    squat = next(m for m in resp.json() if m["code"] == "squatting")
    assert len(squat["metrics"]) >= 5


@pytest.mark.asyncio
async def test_upload_url_rejects_bad_movement_and_view(client: AsyncClient):
    token, athlete_id = await _coach_with_athlete(client)
    resp = await client.post("/api/v1/videos/upload-url", json={
        "athlete_id": athlete_id, "movement_type": "skydiving",
        "camera_view": "sagittal", "original_filename": "a.mp4",
    }, headers=auth_header(token))
    assert resp.status_code == 400
    resp = await client.post("/api/v1/videos/upload-url", json={
        "athlete_id": athlete_id, "movement_type": "squatting",
        "camera_view": "sagittal", "original_filename": "evil.exe",
    }, headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["storage_key"].endswith("upload.mp4")


@pytest.mark.asyncio
async def test_athlete_cannot_upload_for_others(client: AsyncClient):
    coach_token, athlete_id = await _coach_with_athlete(client)
    other = await register_and_login(client, "other@test.com", "athlete")
    resp = await client.post("/api/v1/videos/upload-url", json={
        "athlete_id": athlete_id, "movement_type": "squatting",
        "camera_view": "sagittal", "original_filename": "a.mp4",
    }, headers=auth_header(other))
    assert resp.status_code == 403
    _ = coach_token
