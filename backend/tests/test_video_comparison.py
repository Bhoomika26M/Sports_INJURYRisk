"""Unit and Integration Tests for Dual-Video Form Benchmark & Comparison Studio."""

import pytest
from httpx import AsyncClient

from app.modules.risk_scoring.models import RiskScore
from app.modules.users.models import UserRole
from app.modules.video.clinical_catalog import get_corrective_protocol_for_faults
from app.modules.video.comparison_service import compare_two_videos
from app.modules.video.vector_service import (
    get_textbook_ideal_landmarks,
    normalize_landmarks_to_svg,
)
from tests.conftest import auth_header, register_and_login
from tests.factories import make_athlete, make_user, make_video


def test_textbook_ideal_landmarks_structure():
    """Verify textbook ideal standards return valid geometry for key movements."""
    for mv in ("squatting", "jumping", "sprinting"):
        data = get_textbook_ideal_landmarks(mv)
        assert data["is_textbook_benchmark"] is True
        assert "landmarks" in data
        assert "mid_shoulder" in data["landmarks"]
        assert "mid_hip" in data["landmarks"]
        assert "angles" in data
        assert "knee_flexion_left" in data["angles"]
        assert data["ground_y"] > 300.0


def test_normalize_landmarks_to_svg_detects_valgus_and_lean():
    """Test 2D SVG normalization and fault detection for trunk lean and valgus."""
    raw = {
        "0": [0.5, 0.1, 0.0],
        "11": [0.4, 0.3, 0.0],
        "12": [0.6, 0.3, 0.0],
        "23": [0.45, 0.55, 0.0],
        "24": [0.55, 0.55, 0.0],
        "25": [0.52, 0.75, 0.0],  # Left knee pushed medially toward center (valgus)
        "26": [0.58, 0.75, 0.0],
        "27": [0.42, 0.95, 0.0],
        "28": [0.65, 0.95, 0.0],
    }
    svg_data = normalize_landmarks_to_svg(raw, target_width=300, target_height=400)
    assert "landmarks" in svg_data
    assert "angles" in svg_data
    assert "trunk_lean" in svg_data["angles"]
    assert "knee_valgus" in svg_data["faults"]


def test_clinical_catalog_returns_prioritized_protocols():
    """Verify that corrective exercise protocol catalog returns clinical drills."""
    protocols = get_corrective_protocol_for_faults(["knee_valgus", "excessive_trunk_lean"])
    assert len(protocols) >= 2
    names = [p["title"] for p in protocols]
    assert any("Valgus" in n for n in names)
    assert any("Trunk" in n for n in names)


@pytest.mark.asyncio
async def test_compare_identical_videos(db_session):
    """Test comparing identical videos produces 100% match and identical advisory."""
    coach = await make_user(db_session, "comp_coach1@test.com", role=UserRole.coach)
    athlete = await make_athlete(db_session, coach_id=coach.id)
    video = await make_video(db_session, athlete.id, coach.id, movement_type="squatting")

    res = await compare_two_videos(db_session, video.id, video.id, run_gemini=False)
    assert res.is_identical is True
    assert res.form_match_score == 100.0
    assert "Self-Comparison Mode" in res.advisory
    assert res.suggest_swap is False
    assert len(res.deltas) >= 4


@pytest.mark.asyncio
async def test_compare_swapped_videos(db_session):
    """Test that if student has cleaner form than trainer, role swap is suggested."""
    coach = await make_user(db_session, "comp_coach2@test.com", role=UserRole.coach)
    athlete = await make_athlete(db_session, coach_id=coach.id)

    # Video A: Trainer (bad mechanics, high risk)
    video_a = await make_video(db_session, athlete.id, coach.id, movement_type="squatting")
    video_a.analysis = {
        "metrics": {"max_knee_flexion": 60.0, "max_trunk_lean": 45.0, "knee_valgus_flag": "mild"}
    }
    risk_a = RiskScore(
        video_id=video_a.id,
        athlete_id=athlete.id,
        overall_score=75.0,
        risk_category="high",
        score_breakdown={},
        assessment={"drivers": []},
    )
    db_session.add(risk_a)

    # Video B: Trainee (clean mechanics, low risk)
    video_b = await make_video(db_session, athlete.id, coach.id, movement_type="squatting")
    video_b.analysis = {
        "metrics": {"max_knee_flexion": 98.0, "max_trunk_lean": 15.0, "knee_valgus_flag": "none"}
    }
    risk_b = RiskScore(
        video_id=video_b.id,
        athlete_id=athlete.id,
        overall_score=20.0,
        risk_category="low",
        score_breakdown={},
        assessment={"drivers": []},
    )
    db_session.add(risk_b)
    await db_session.commit()

    res = await compare_two_videos(db_session, video_a.id, video_b.id, run_gemini=False)
    assert res.suggest_swap is True
    assert "Role Inversion Advisory" in res.advisory
    assert res.is_identical is False


@pytest.mark.asyncio
async def test_compare_api_endpoint(client: AsyncClient, db_session):
    """Test POST /api/v1/videos/compare endpoint via HTTP client."""
    token = await register_and_login(client, "api_coach@test.com", "coach")
    headers = auth_header(token)

    coach = await make_user(db_session, "comp_coach3@test.com", role=UserRole.coach)
    athlete = await make_athlete(db_session, coach_id=coach.id)
    video_a = await make_video(db_session, athlete.id, coach.id, movement_type="squatting")
    video_b = await make_video(db_session, athlete.id, coach.id, movement_type="squatting")
    await db_session.commit()

    payload = {
        "video_a_id": video_a.id,
        "video_b_id": video_b.id,
        "run_gemini": False,
    }
    resp = await client.post("/api/v1/videos/compare", json=payload, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "form_match_score" in body
    assert "deltas" in body
    assert "vector_posture_a" in body
    assert "vector_posture_b" in body
    assert "gemini_coaching" in body


@pytest.mark.asyncio
async def test_get_vector_posture_endpoint(client: AsyncClient, db_session):
    """Test GET /api/v1/videos/{video_id}/vector-posture."""
    token = await register_and_login(client, "admin_vec@test.com", "admin")
    headers = auth_header(token)

    coach = await make_user(db_session, "comp_coach4@test.com", role=UserRole.coach)
    athlete = await make_athlete(db_session, coach_id=coach.id)
    video = await make_video(db_session, athlete.id, coach.id, movement_type="squatting")
    await db_session.commit()

    # 1. For a real video
    resp = await client.get(f"/api/v1/videos/{video.id}/vector-posture", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "landmarks" in body
    assert "angles" in body

    # 2. For a textbook standard
    resp_textbook = await client.get("/api/v1/videos/textbook_squatting/vector-posture", headers=headers)
    assert resp_textbook.status_code == 200
    body_tb = resp_textbook.json()
    assert body_tb["is_textbook_benchmark"] is True


@pytest.mark.asyncio
async def test_benchmark_presets_endpoint(client: AsyncClient, db_session):
    """Test GET /api/v1/videos/benchmark-presets."""
    token = await register_and_login(client, "preset_coach_login@test.com", "coach")
    headers = auth_header(token)
    resp = await client.get("/api/v1/videos/benchmark-presets", headers=headers)
    assert resp.status_code == 200
    presets = resp.json()["presets"]
    assert len(presets) >= 1
    assert any(p["movement_type"] == "squatting" for p in presets)
