"""Regression tests for bugs found by driving the real UI against the real API (2026-10-01).

None of these were caught by the existing suite because they only appear on paths the
tests never exercised: the athlete-role athlete list, GET /biomechanics with real rows,
and persisting frontal-plane ('qualitative') metrics.
"""
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.athletes.models import Athlete
from app.modules.video.models import BiomechanicalMetric, Video, VideoProcessingStatus
from tests.conftest import auth_header, register_and_login


async def _me(client: AsyncClient, token: str) -> dict:
    resp = await client.get("/api/v1/auth/me", headers=auth_header(token))
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_athlete_role_can_list_own_profile(client: AsyncClient, db_session: AsyncSession):
    """GET /athletes used `select` without importing it, so every athlete-role call was a 500."""
    token = await register_and_login(client, "ath@test.com", "athlete")

    resp = await client.get("/api/v1/athletes", headers=auth_header(token))
    assert resp.status_code == 200, resp.text  # no profile yet -> empty list, not a crash
    assert resp.json()["total"] == 0

    me = await _me(client, token)
    db_session.add(Athlete(user_id=me["id"], sport_type="basketball", date_of_birth=date(2000, 1, 15)))
    await db_session.commit()

    resp = await client.get("/api/v1/athletes", headers=auth_header(token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["sport_type"] == "basketball"


@pytest.mark.asyncio
async def test_biomechanics_endpoint_serializes_stored_frames(client: AsyncClient, db_session: AsyncSession):
    """BiomechanicsResponse was handed raw ORM rows (no from_attributes) -> 500 for any video with frames.

    Also stores confidence='qualitative' (11 chars): the column was VARCHAR(10), which made the worker's
    commit fail for any clip that produced frontal-plane (knee valgus) metrics.
    """
    token = await register_and_login(client, "coach2@test.com", "coach")
    me = await _me(client, token)
    created = await client.post(
        "/api/v1/athletes",
        json={"sport_type": "soccer", "date_of_birth": "1999-05-01"},
        headers=auth_header(token),
    )
    assert created.status_code == 201, created.text

    video = Video(
        athlete_id=created.json()["id"], uploaded_by=me["id"], movement_type="squatting",
        storage_key="tests/x.mp4", camera_view="sagittal", processing_status=VideoProcessingStatus.completed,
    )
    db_session.add(video)
    await db_session.flush()
    db_session.add_all([
        BiomechanicalMetric(video_id=video.id, frame_number=0, metric_name="knee_flexion_angle_left",
                            metric_value=95.5, plane="sagittal", confidence="validated"),
        BiomechanicalMetric(video_id=video.id, frame_number=0, metric_name="knee_valgus_deviation_left",
                            metric_value=7.8, plane="frontal", confidence="qualitative"),
    ])
    await db_session.commit()

    resp = await client.get(f"/api/v1/videos/{video.id}/biomechanics", headers=auth_header(token))
    assert resp.status_code == 200, resp.text
    frames = resp.json()["frames"]
    assert {f["confidence"] for f in frames} == {"validated", "qualitative"}
    assert isinstance(frames[0]["metric_value"], float)
