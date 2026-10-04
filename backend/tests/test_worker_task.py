"""process_video wiring against a real database, with only the two heavy model calls stubbed."""

import pytest
from sqlalchemy import select

from app.modules.pose import tasks
from app.modules.users.models import User
from app.modules.video.models import BiomechanicalMetric, PoseFrame, Video, VideoProcessingStatus
from tests.conftest import TestSessionLocal, register_and_login
from tests.synth import squat_frames
from tests.test_risk_assessment_api import _athlete, _user


async def _pending_video(db, view):
    await register_and_login_once(db)
    coach = await _user(db, "w@t.com")
    ath = await _athlete(db, coach.id)
    v = Video(athlete_id=ath.id, uploaded_by=coach.id, movement_type="squatting", storage_key="clip.mp4",
              original_filename="clip.mp4", camera_view=view, fps=30, processing_status=VideoProcessingStatus.uploaded)
    db.add(v)
    await db.commit()
    await db.refresh(v)
    return v


async def register_and_login_once(db):
    from app.core.security import hash_password
    from app.modules.users.models import UserRole
    if not await _user(db, "w@t.com"):
        db.add(User(email="w@t.com", password_hash=hash_password("x" * 12), full_name="W", role=UserRole.coach))
        await db.commit()


@pytest.fixture
def stubbed_models(monkeypatch):
    seen = {}

    async def fake_download(key):
        return "/tmp/fake.mp4"

    def fake_track(path, model, stride=1):
        seen["track_stride"] = stride
        return {"person_counts": [1] * 10, "tracks": {1: {i: (100, 100, 300, 600) for i in range(10)}},   # a 500 px tall athlete
                "main_track_id": 1, "max_persons": 1, "frames_processed": 10, "tracked": True,
                "frame_width": 1080, "frame_height": 1920}

    def fake_pass(path, annotate_output_path=None, progress_callback=None, subject_boxes=None, diagnostics=None, stride=None,
                  full_frame_fallback=True):
        seen["pass_stride"] = stride
        diagnostics.update({"frames_processed": 270, "stride": stride, "model": "stub",
                            "lighting": {"mean_luma": 120.0, "luma_range": 120.0, "low_light": False},
                            "contrast_enhanced": False})
        return squat_frames(n_reps=4), 1.0

    monkeypatch.setattr(tasks, "download_from_storage", fake_download)
    monkeypatch.setattr(tasks, "track_persons", fake_track)
    monkeypatch.setattr(tasks, "run_mediapipe_full_pass", fake_pass)
    monkeypatch.setattr(tasks, "extract_thumbnail", lambda *a, **k: None)
    monkeypatch.setattr(tasks, "async_session_factory", TestSessionLocal)
    return seen


@pytest.mark.asyncio
async def test_worker_persists_raw_landmarks_with_visibility_metrics_and_analysis(db_session, stubbed_models):
    v = await _pending_video(db_session, "sagittal")
    out = await tasks.process_video({}, v.id)
    assert out["status"] == "completed"

    async with TestSessionLocal() as s:
        video = await s.scalar(select(Video).where(Video.id == v.id))
        assert video.processing_status == VideoProcessingStatus.completed
        a = video.analysis
        assert a["quality"]["grade"] == "good" and a["movement"]["reps"]["n_reps"] == 4
        frames = (await s.scalars(select(PoseFrame).where(PoseFrame.video_id == v.id))).all()
        assert frames and "_vis" in frames[0].keypoints and len(frames[0].keypoints["_vis"]) == 33
        assert "0" in frames[0].keypoints            # landmarks still addressable exactly as before
        n_metrics = len((await s.scalars(select(BiomechanicalMetric).where(BiomechanicalMetric.video_id == v.id))).all())
        assert n_metrics > 500
    assert stubbed_models["track_stride"] == stubbed_models["pass_stride"] == 1


@pytest.mark.asyncio
async def test_worker_handles_other_camera_view_with_qualitative_valgus(db_session, stubbed_models):
    """REGRESSION: 'qualitative' (11 chars) overflowed VARCHAR(10) -> every frontal/'other'-view video
    died at the metrics INSERT with an internal_error."""
    v = await _pending_video(db_session, "other")
    out = await tasks.process_video({}, v.id)
    assert out["status"] == "completed", out
    async with TestSessionLocal() as s:
        confs = {m.confidence for m in (await s.scalars(select(BiomechanicalMetric).where(BiomechanicalMetric.video_id == v.id))).all()}
    assert confs == {"validated", "qualitative"}


@pytest.mark.asyncio
async def test_worker_fails_cleanly_below_the_detection_floor(db_session, stubbed_models, monkeypatch):
    monkeypatch.setattr(tasks, "run_mediapipe_full_pass",
                        lambda *a, diagnostics=None, **k: (squat_frames(n_reps=1)[:5], 0.3))  # clearly below the 40% partial-coverage floor
    v = await _pending_video(db_session, "sagittal")
    out = await tasks.process_video({}, v.id)
    assert out == {"status": "failed", "reason": "low_detection_quality"}


@pytest.mark.asyncio
async def test_slow_motion_stride_is_used_for_both_tracking_and_pose(db_session, stubbed_models, monkeypatch):
    v = await _pending_video(db_session, "sagittal")
    v.fps = 240
    await db_session.commit()
    await tasks.process_video({}, v.id)
    assert stubbed_models["track_stride"] == stubbed_models["pass_stride"] == 4


@pytest.mark.asyncio
async def test_reprocess_upgrades_an_old_video_from_stored_landmarks(db_session):
    """An old video (stored before visibility existed, with a stale metric row) is re-derived in place."""
    from sqlalchemy import insert
    from app.modules.pose.reprocess import reprocess_all

    v = await _pending_video(db_session, "sagittal")
    v.processing_status = VideoProcessingStatus.completed
    await db_session.commit()
    frames = squat_frames(n_reps=4)
    await db_session.execute(insert(PoseFrame), [
        {"video_id": v.id, "frame_number": f["frame_number"], "timestamp_ms": f["timestamp_ms"],
         "keypoints": f["world_landmarks"], "model_used": "mediapipe"} for f in frames])        # no "_vis"
    await db_session.execute(insert(BiomechanicalMetric), [
        {"video_id": v.id, "frame_number": 0, "metric_name": "hip_flexion_angle_left",
         "metric_value": 171.0, "plane": "sagittal", "confidence": "validated"}])               # old inverted convention
    await db_session.commit()

    assert (await reprocess_all(db_session, v.id, dry_run=True))[0]["status"] == "dry-run"
    res = (await reprocess_all(db_session, v.id))[0]
    assert res["status"] == "reprocessed" and res["metrics"] > 500

    await db_session.refresh(v)
    hips = (await db_session.scalars(select(BiomechanicalMetric).where(
        BiomechanicalMetric.video_id == v.id, BiomechanicalMetric.metric_name == "hip_flexion_angle_left"))).all()
    assert hips and min(float(h.metric_value) for h in hips) < 30     # standing hip flexion ~0-ish, not ~171
    assert {w["code"] for w in v.analysis["quality"]["warnings"]} >= {"visibility_unavailable"}
