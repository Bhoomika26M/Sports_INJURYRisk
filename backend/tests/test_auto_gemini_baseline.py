"""Tests for automatic Gemini baseline fallback when peer baseline videos are insufficient."""

from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient
import numpy as np

from app.config import settings
from app.modules.video.ai_service import check_baseline_sufficiency
from tests.conftest import auth_header, register_and_login
from tests.factories import make_athlete, make_population, make_user, make_video, normal_frames

METRICS = ("knee_flexion_angle_left", "knee_flexion_angle_right")


@pytest.mark.asyncio
async def test_check_baseline_sufficiency_detects_insufficient_and_sufficient(db_session):
    """Test check_baseline_sufficiency logic with zero baseline vs full baseline."""
    # When 0 videos exist in DB for running
    is_suff, have_v, need_v, have_a, need_a = await check_baseline_sufficiency(db_session, "running")
    assert not is_suff
    assert have_v == 0
    assert need_v == settings.min_baseline_videos

    # When sufficient population exists for squatting
    await make_population(db_session, videos=settings.min_baseline_videos + 2, athletes=settings.min_baseline_athletes + 1, movement_type="squatting", seed=10)
    is_suff, have_v, need_v, have_a, need_a = await check_baseline_sufficiency(db_session, "squatting")
    assert is_suff
    assert have_v >= settings.min_baseline_videos
    assert have_a >= settings.min_baseline_athletes


@pytest.mark.asyncio
async def test_insufficient_baseline_with_mocked_gemini_produces_score(client: AsyncClient, db_session):
    """When baseline videos < threshold, automatic Gemini observation computes a valid score."""
    token = await register_and_login(client, "admin@auto-gemini.example.com", "admin")
    coach = await make_user(db_session, "coach@auto-gemini.example.com")
    athlete = await make_athlete(db_session, coach.id)
    rng = np.random.default_rng(42)

    video = await make_video(
        db_session,
        athlete.id,
        coach.id,
        movement_type="sprinting",
        metrics={m: normal_frames(rng, 120) for m in METRICS},
    )

    mock_observation = {
        "overall": {
            "quality": "good",
            "knee_valgus": "mild",
            "trunk_lean": "none",
            "asymmetry": "none",
        },
        "flags": ["mild knee valgus observed during stance phase"],
        "recommendations": ["Focus on hip abductor strengthening"],
    }

    # Mock run_gemini_observation_for_video so it returns mock_observation
    with patch(
        "app.modules.video.ai_service.run_gemini_observation_for_video",
        new=AsyncMock(return_value=mock_observation),
    ):
        resp = await client.get(
            f"/api/v1/videos/{video.id}/risk-score",
            headers=auth_header(token),
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "overall_score" in body
        assert body["overall_score"] is not None
        assert 0 <= body["overall_score"] <= 100
        assert body["score_breakdown"] is not None
        assert "biomechanical_deviations" in body["score_breakdown"]
        assert body["baseline"]["method"] == "Multimodal AI video observation + kinematic analysis"


@pytest.mark.asyncio
async def test_sufficient_baseline_does_not_trigger_gemini(client: AsyncClient, db_session):
    """When baseline videos >= threshold, standard Isolation Forest baseline is used."""
    token = await register_and_login(client, "admin@suff-gemini.example.com", "admin")
    coach, athletes, videos = await make_population(
        db_session,
        videos=settings.min_baseline_videos + 2,
        athletes=settings.min_baseline_athletes + 1,
        movement_type="squatting",
        seed=20,
    )

    target_video = videos[0]

    with patch(
        "app.modules.video.ai_service.run_gemini_observation_for_video",
        new=AsyncMock(),
    ) as mock_gemini:
        resp = await client.get(
            f"/api/v1/videos/{target_video.id}/risk-score",
            headers=auth_header(token),
        )

        # Baseline was sufficient, so run_gemini_observation_for_video should NOT be called
        mock_gemini.assert_not_called()
        assert resp.status_code == 200
        body = resp.json()
        assert "overall_score" in body
        assert "Multimodal AI" not in (body.get("baseline", {}).get("method") or "")

