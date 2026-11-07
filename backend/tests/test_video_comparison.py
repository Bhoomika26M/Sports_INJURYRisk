"""Unit and Integration Tests for Dual-Video Form Benchmark & Comparison Studio (Phase 2 Spec)."""

import pytest
from httpx import AsyncClient

from app.modules.users.models import UserRole
from app.modules.video.comparison_service import compare_two_videos
from app.modules.video.models import PoseFrame, VideoProcessingStatus
from app.modules.video.vector_service import (
    extract_inflection_vector_for_video,
    normalize_landmarks_to_svg,
)
from tests.conftest import auth_header, register_and_login
from tests.factories import make_athlete, make_user, make_video


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


@pytest.mark.asyncio
async def test_no_pose_frames_returns_no_snapshot_not_textbook(db_session):
    """F07: Videos without pose frames return None (UI renders 'no pose data'), never textbook figures."""
    coach = await make_user(db_session, "nopose_coach@test.com", role=UserRole.coach)
    athlete = await make_athlete(db_session, coach_id=coach.id)
    video = await make_video(db_session, athlete.id, coach.id, movement_type="squatting")
    await db_session.commit()

    vec = await extract_inflection_vector_for_video(db_session, video.id)
    assert vec is None, f"Expected None for video without pose frames, got {vec}"


@pytest.mark.asyncio
async def test_compare_uses_real_analysis_shape(db_session):
    """F05: Compare reads from video.analysis['movement']['metrics'] without hardcoded defaults."""
    coach = await make_user(db_session, "real_coach@test.com", role=UserRole.coach)
    athlete = await make_athlete(db_session, coach_id=coach.id)

    video_a = await make_video(db_session, athlete.id, coach.id, movement_type="squatting")
    video_a.processing_status = VideoProcessingStatus.completed
    video_a.camera_view = "sagittal"
    video_a.analysis = {
        "version": "2.3",
        "quality": {"grade": "good", "warnings": []},
        "movement": {
            "metrics": {
                "max_knee_flexion": 105.0,
                "max_trunk_lean": 22.0,
                "knee_valgus_flag": "none",
            },
            "reps": {"n_reps": 3, "rep_peaks": [103.0, 105.0, 104.0]},
        },
    }

    video_b = await make_video(db_session, athlete.id, coach.id, movement_type="squatting")
    video_b.processing_status = VideoProcessingStatus.completed
    video_b.camera_view = "sagittal"
    video_b.analysis = {
        "version": "2.3",
        "quality": {"grade": "fair", "warnings": []},
        "movement": {
            "metrics": {
                "max_knee_flexion": 85.0,
                "max_trunk_lean": 36.0,
                "knee_valgus_flag": "mild",
            },
            "reps": {"n_reps": 3, "rep_peaks": [82.0, 85.0, 84.0]},
        },
    }
    await db_session.commit()

    res = await compare_two_videos(db_session, video_a, video_b)
    assert res.movement_type == "squatting"
    assert res.video_a_info.id == video_a.id
    assert res.video_b_info.id == video_b.id

    deltas_by_key = {d.metric: d for d in res.deltas}
    assert "knee_flexion_depth" in deltas_by_key
    assert deltas_by_key["knee_flexion_depth"].video_a == 105
    assert deltas_by_key["knee_flexion_depth"].video_b == 85
    assert deltas_by_key["knee_flexion_depth"].delta == -20
    assert deltas_by_key["knee_flexion_depth"].verdict == "lower"

    assert "trunk_lean" in deltas_by_key
    assert deltas_by_key["trunk_lean"].video_a == 22
    assert deltas_by_key["trunk_lean"].video_b == 36
    assert deltas_by_key["trunk_lean"].delta == 14
    assert deltas_by_key["trunk_lean"].verdict == "higher"

    # Knee valgus is qualitative
    assert "knee_valgus" in deltas_by_key
    assert deltas_by_key["knee_valgus"].unit == "qualitative"
    assert deltas_by_key["knee_valgus"].video_a == "none"
    assert deltas_by_key["knee_valgus"].video_b == "mild"


@pytest.mark.asyncio
async def test_compare_missing_metric_is_none_not_default(db_session):
    """F05: Missing metrics return None and 'not_comparable', never hardcoded defaults (98/75/18/38)."""
    coach = await make_user(db_session, "missing_coach@test.com", role=UserRole.coach)
    athlete = await make_athlete(db_session, coach_id=coach.id)

    video_a = await make_video(db_session, athlete.id, coach.id, movement_type="squatting")
    video_a.processing_status = VideoProcessingStatus.completed
    video_a.camera_view = "sagittal"
    video_a.analysis = {
        "quality": {"grade": "good"},
        "movement": {"metrics": {}},
    }

    video_b = await make_video(db_session, athlete.id, coach.id, movement_type="squatting")
    video_b.processing_status = VideoProcessingStatus.completed
    video_b.camera_view = "sagittal"
    video_b.analysis = {
        "quality": {"grade": "good"},
        "movement": {"metrics": {}},
    }
    await db_session.commit()

    res = await compare_two_videos(db_session, video_a, video_b)
    deltas_by_key = {d.metric: d for d in res.deltas}

    # Must be None, not 98.0 / 75.0
    assert deltas_by_key["knee_flexion_depth"].video_a is None
    assert deltas_by_key["knee_flexion_depth"].video_b is None
    assert deltas_by_key["knee_flexion_depth"].delta is None
    assert deltas_by_key["knee_flexion_depth"].verdict == "not_comparable"


@pytest.mark.asyncio
async def test_compare_refuses_movement_view_quality_mismatch(client: AsyncClient, db_session):
    """F15: Compare endpoint refuses movement mismatch, view mismatch, and poor quality with 422."""
    token = await register_and_login(client, "mismatch_coach@test.com", "coach")
    headers = auth_header(token)

    from sqlalchemy import select
    from app.modules.users.models import User
    coach = await db_session.scalar(select(User).where(User.email == "mismatch_coach@test.com"))
    athlete = await make_athlete(db_session, coach_id=coach.id)

    # 1. Movement mismatch
    v_squat = await make_video(db_session, athlete.id, coach.id, movement_type="squatting")
    v_squat.processing_status = VideoProcessingStatus.completed
    v_squat.camera_view = "sagittal"

    v_jump = await make_video(db_session, athlete.id, coach.id, movement_type="jumping")
    v_jump.processing_status = VideoProcessingStatus.completed
    v_jump.camera_view = "sagittal"
    await db_session.commit()

    r1 = await client.post("/api/v1/videos/compare", json={"video_a_id": v_squat.id, "video_b_id": v_jump.id}, headers=headers)
    assert r1.status_code == 422
    assert "movement" in r1.text.lower()

    # 2. View mismatch
    v_frontal = await make_video(db_session, athlete.id, coach.id, movement_type="squatting")
    v_frontal.processing_status = VideoProcessingStatus.completed
    v_frontal.camera_view = "frontal"
    await db_session.commit()

    r2 = await client.post("/api/v1/videos/compare", json={"video_a_id": v_squat.id, "video_b_id": v_frontal.id}, headers=headers)
    assert r2.status_code == 422
    assert "view" in r2.text.lower()

    # 3. Poor quality
    v_poor = await make_video(db_session, athlete.id, coach.id, movement_type="squatting")
    v_poor.processing_status = VideoProcessingStatus.completed
    v_poor.camera_view = "sagittal"
    v_poor.analysis = {"quality": {"grade": "poor"}}
    await db_session.commit()

    r3 = await client.post("/api/v1/videos/compare", json={"video_a_id": v_squat.id, "video_b_id": v_poor.id}, headers=headers)
    assert r3.status_code == 422
    assert "quality" in r3.text.lower()


@pytest.mark.asyncio
async def test_compare_authorized_coach_succeeds(client: AsyncClient, db_session):
    """Test POST /api/v1/videos/compare returns typed CompareVideosResponse for authorized caller."""
    token = await register_and_login(client, "auth_coach_compare@test.com", "coach")
    headers = auth_header(token)

    from sqlalchemy import select
    from app.modules.users.models import User
    coach = await db_session.scalar(select(User).where(User.email == "auth_coach_compare@test.com"))
    athlete = await make_athlete(db_session, coach_id=coach.id)

    video_a = await make_video(db_session, athlete.id, coach.id, movement_type="squatting")
    video_a.processing_status = VideoProcessingStatus.completed
    video_a.camera_view = "sagittal"
    video_a.analysis = {
        "quality": {"grade": "good"},
        "movement": {"metrics": {"max_knee_flexion": 95.0, "max_trunk_lean": 20.0}},
    }

    video_b = await make_video(db_session, athlete.id, coach.id, movement_type="squatting")
    video_b.processing_status = VideoProcessingStatus.completed
    video_b.camera_view = "sagittal"
    video_b.analysis = {
        "quality": {"grade": "good"},
        "movement": {"metrics": {"max_knee_flexion": 98.0, "max_trunk_lean": 21.0}},
    }
    await db_session.commit()

    resp = await client.post(
        "/api/v1/videos/compare",
        json={"video_a_id": video_a.id, "video_b_id": video_b.id},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["movement_type"] == "squatting"
    assert "video_a_info" in body
    assert "video_b_info" in body
    assert "deltas" in body
    assert "summary" in body
    assert "differences under about 7°" in body["summary"].lower() or "within standard monocular pose-tracking error" in body["summary"].lower()
    # 98 - 95 = 3 deg, which is within the 6.5 deg noise floor
    knee_delta = next(d for d in body["deltas"] if d["metric"] == "knee_flexion_depth")
    assert knee_delta["verdict"] == "within_noise"
