"""Tests for Phase 1 Security, Integrity, and Scientific Honesty (F01-F11)."""

import pytest
from httpx import AsyncClient

from app.modules.users.models import UserRole
from tests.conftest import auth_header, register_and_login
from tests.factories import make_athlete, make_user, make_video


@pytest.mark.asyncio
async def test_compare_forbidden_for_other_users_videos(client: AsyncClient, db_session):
    """F01: POST /api/v1/videos/compare must return 403 when caller cannot access both videos."""
    coach_owner = await make_user(db_session, "owner_coach@test.com", role=UserRole.coach)
    athlete = await make_athlete(db_session, coach_id=coach_owner.id)
    video_a = await make_video(db_session, athlete.id, coach_owner.id, movement_type="squatting")
    video_b = await make_video(db_session, athlete.id, coach_owner.id, movement_type="squatting")
    await db_session.commit()

    attacker_token = await register_and_login(client, "attacker_coach@test.com", "coach")
    headers = auth_header(attacker_token)

    payload = {
        "video_a_id": video_a.id,
        "video_b_id": video_b.id,
    }
    resp = await client.post("/api/v1/videos/compare", json=payload, headers=headers)
    assert resp.status_code == 403, f"Expected 403 IDOR rejection, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_vector_posture_forbidden_and_uuid_validated(client: AsyncClient, db_session):
    """F03: GET /{id}/vector-posture requires UuidPath and 403 access check."""
    coach = await make_user(db_session, "vec_coach@test.com", role=UserRole.coach)
    athlete = await make_athlete(db_session, coach_id=coach.id)
    video = await make_video(db_session, athlete.id, coach.id, movement_type="squatting")
    await db_session.commit()

    attacker_token = await register_and_login(client, "vec_attacker@test.com", "coach")
    resp_idor = await client.get(f"/api/v1/videos/{video.id}/vector-posture", headers=auth_header(attacker_token))
    assert resp_idor.status_code == 403, f"Expected 403, got {resp_idor.status_code}"

    # String identifiers such as non_uuid_preset_slug must be rejected with 422
    resp_invalid_uuid = await client.get("/api/v1/videos/non_uuid_preset_slug/vector-posture", headers=auth_header(attacker_token))
    assert resp_invalid_uuid.status_code == 422, f"Expected 422 for non-UUID, got {resp_invalid_uuid.status_code}"


@pytest.mark.asyncio
async def test_claim_does_not_attach_arbitrary_coach(client: AsyncClient, db_session):
    """F08: POST /api/v1/athletes/claim must create unlinked profile (coach_id=None)."""
    coach = await make_user(db_session, "first_coach@test.com", role=UserRole.coach)
    await db_session.commit()

    ath_token = await register_and_login(client, "new_athlete@test.com", "athlete")
    headers = auth_header(ath_token)

    payload = {
        "sport_type": "basketball",
        "date_of_birth": "2002-05-14",
        "position": "Guard",
    }
    resp = await client.post("/api/v1/athletes/claim", json=payload, headers=headers)
    assert resp.status_code in (200, 201), resp.text
    data = resp.json()
    assert data["coach_id"] is None, f"Expected coach_id=None, but got {data.get('coach_id')}"
    assert data["sport_type"] == "basketball"
    assert data["date_of_birth"] == "2002-05-14"


@pytest.mark.asyncio
async def test_claim_requires_dob(client: AsyncClient, db_session):
    """F08: Claim request without date_of_birth must be rejected with 422."""
    ath_token = await register_and_login(client, "claim_nodob@test.com", "athlete")
    headers = auth_header(ath_token)
    payload = {
        "sport_type": "soccer",
    }
    resp = await client.post("/api/v1/athletes/claim", json=payload, headers=headers)
    assert resp.status_code == 422, f"Expected 422 for missing date_of_birth, got {resp.status_code}"


@pytest.mark.asyncio
async def test_upload_requires_athlete_id(client: AsyncClient, db_session):
    """F09: POST /videos/upload-url must require athlete_id."""
    coach_token = await register_and_login(client, "upload_coach@test.com", "coach")
    headers = auth_header(coach_token)
    payload = {
        "movement_type": "squatting",
        "camera_view": "sagittal",
        "original_filename": "squat.mp4",
    }
    resp = await client.post("/api/v1/videos/upload-url", json=payload, headers=headers)
    assert resp.status_code == 422, f"Expected 422 when athlete_id is omitted, got {resp.status_code}"

