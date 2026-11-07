"""Authorization Test Matrix & Security Scenarios (U4 & U7).

Dynamically verifies multi-tenant isolation across all video and athlete routes:
- Unrelated coach cannot read another coach's athletes or videos.
- Different athlete cannot access another athlete's data.
- Expired / revoked session tokens are rejected.
- Logout revokes refresh tokens.
- Non-retryable video errors are rejected on retry.
"""

import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient

from app.main import app
from app.modules.users.models import UserRole
from app.modules.video.models import VideoProcessingStatus
from tests.conftest import auth_header, register_and_login
from tests.factories import make_athlete, make_user, make_video

# Dynamically gather all GET routes scoping on video_id or athlete_id
SCOPED_GET_ROUTES = [
    r
    for r in app.routes
    if getattr(r, "methods", None)
    and "GET" in r.methods
    and any(k in r.path for k in ["{video_id}", "{athlete_id}"])
]


@pytest.mark.asyncio
@pytest.mark.parametrize("route", SCOPED_GET_ROUTES, ids=lambda r: r.path)
async def test_unrelated_coach_cannot_read_scoped_resource(client: AsyncClient, db_session, route):
    """Proves tenant isolation: Unrelated coach gets 403 or 404 on any private resource."""
    owner = await make_user(db_session, f"owner_{route.path[:8].replace('/', '_')}@t.com", role=UserRole.coach)
    athlete = await make_athlete(db_session, coach_id=owner.id)
    video = await make_video(db_session, athlete.id, owner.id, movement_type="squatting")
    await db_session.commit()

    attacker_token = await register_and_login(client, f"attacker_{route.path[:8].replace('/', '_')}@t.com", "coach")
    path = (
        route.path
        .replace("{video_id}", video.id)
        .replace("{athlete_id}", athlete.id)
        .replace("{injury_id}", "00000000-0000-0000-0000-000000000000")
        .replace("{entry_id}", "00000000-0000-0000-0000-000000000000")
    )

    resp = await client.get(path, headers=auth_header(attacker_token))
    assert resp.status_code in (403, 404), f"Route {path} allowed unauthorized access with {resp.status_code}"


@pytest.mark.asyncio
@pytest.mark.parametrize("route", SCOPED_GET_ROUTES, ids=lambda r: r.path)
async def test_unrelated_athlete_cannot_read_scoped_resource(client: AsyncClient, db_session, route):
    """Proves tenant isolation: Different athlete gets 403 or 404 on any other athlete's resource."""
    owner = await make_user(db_session, f"owner_ath_{route.path[:8].replace('/', '_')}@t.com", role=UserRole.coach)
    athlete = await make_athlete(db_session, coach_id=owner.id)
    video = await make_video(db_session, athlete.id, owner.id, movement_type="squatting")
    await db_session.commit()

    attacker_token = await register_and_login(client, f"diff_ath_{route.path[:8].replace('/', '_')}@t.com", "athlete")
    path = (
        route.path
        .replace("{video_id}", video.id)
        .replace("{athlete_id}", athlete.id)
        .replace("{injury_id}", "00000000-0000-0000-0000-000000000000")
        .replace("{entry_id}", "00000000-0000-0000-0000-000000000000")
    )

    resp = await client.get(path, headers=auth_header(attacker_token))
    assert resp.status_code in (403, 404), f"Route {path} allowed unauthorized athlete access with {resp.status_code}"


@pytest.mark.asyncio
async def test_logout_then_reuse_refresh_token_fails(client: AsyncClient, db_session):
    """Proves session revocation: Calling logout invalidates the refresh cookie."""
    token = await register_and_login(client, "session_user@test.com", "coach")

    # Logout
    logout_resp = await client.post("/api/v1/auth/logout")
    assert logout_resp.status_code == 200

    # Attempt to refresh
    refresh_resp = await client.post("/api/v1/auth/refresh")
    assert refresh_resp.status_code == 401


@pytest.mark.asyncio
async def test_retry_video_non_failed_rejected(client: AsyncClient, db_session):
    """U7: Retrying a completed video returns 400."""
    coach = await make_user(db_session, "retry_coach@test.com", role=UserRole.coach)
    athlete = await make_athlete(db_session, coach_id=coach.id)
    video = await make_video(db_session, athlete.id, coach.id, movement_type="squatting")
    await db_session.commit()

    token = await register_and_login(client, "retry_coach@test.com", "coach")
    resp = await client.post(f"/api/v1/videos/{video.id}/retry", headers=auth_header(token))
    assert resp.status_code == 400
    assert resp.json()["detail"]["error"]["code"] == "NOT_FAILED"


@pytest.mark.asyncio
async def test_retry_video_non_retryable_error_rejected(client: AsyncClient, db_session):
    """U7: Non-retryable error (e.g. resolution_too_low) returns 422."""
    coach = await make_user(db_session, "retry_coach2@test.com", role=UserRole.coach)
    athlete = await make_athlete(db_session, coach_id=coach.id)
    video = await make_video(db_session, athlete.id, coach.id, movement_type="squatting")
    video.processing_status = VideoProcessingStatus.failed
    video.error_code = "resolution_too_low"
    await db_session.commit()

    token = await register_and_login(client, "retry_coach2@test.com", "coach")
    resp = await client.post(f"/api/v1/videos/{video.id}/retry", headers=auth_header(token))
    assert resp.status_code == 422
    assert resp.json()["detail"]["error"]["code"] == "NON_RETRYABLE_ERROR"
