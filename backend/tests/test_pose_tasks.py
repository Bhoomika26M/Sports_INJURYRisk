"""process_video end-to-end against real Postgres, with YOLO / MediaPipe replaced by deterministic fakes.

The fakes stand in for the two model passes only (the real clips and weights are not available in CI);
tracking summary -> coverage assessment -> persistence -> baseline eligibility all run for real.
"""

import numpy as np
import pytest
from sqlalchemy import func, select

from app.modules.pose import tasks
from app.modules.video.models import BiomechanicalMetric, PoseFrame, Video, VideoProcessingStatus
from tests.conftest import TestSessionLocal
from tests.factories import make_athlete, make_user, make_video
from app.modules.risk_scoring.features import fetch_baseline_set

H = 1080


def standing_pose(jitter: float) -> dict:
    """MediaPipe world landmarks: metres, Y-DOWN (head -0.65, hips 0, ankles +0.78)."""
    lm = {str(i): [0.0, 0.0, 0.0] for i in range(33)}
    lm["0"] = [0.0, -0.65, 0.0]
    for idx, (x, y) in {11: (0.2, -0.5), 12: (-0.2, -0.5), 23: (0.1, 0.0), 24: (-0.1, 0.0),
                        25: (0.1, 0.4 - jitter), 26: (-0.1, 0.4 - jitter), 27: (0.1, 0.78), 28: (-0.1, 0.78)}.items():
        lm[str(idx)] = [x, y, 0.0]
    return lm


def frames(n_detected: int, n_total: int) -> tuple[list[dict], float]:
    rng = np.random.default_rng(0)
    res = [{"frame_number": i, "timestamp_ms": i * 33, "world_landmarks": standing_pose(float(rng.normal(0, 0.01)))}
           for i in range(n_detected)]
    return res, n_detected / n_total


def box(h):
    return (100.0, 100.0, 100.0 + h * 0.4, 100.0 + h)


def make_tracking(*, frames_n=100, main_len=100, main_h=420.0, others=()):
    tracks = {1: {i: box(main_h) for i in range(main_len)}}
    for k, (n, h) in enumerate(others, start=2):
        tracks[k] = {i: box(h) for i in range(n)}
    persons = 1 + len(list(others))
    return {"person_counts": [persons] * frames_n, "tracks": tracks, "main_track_id": 1, "max_persons": persons,
            "frames_processed": frames_n, "tracked": True, "frame_height": H, "frame_width": 1920}


@pytest.fixture
def pipeline(monkeypatch):
    """Patch the two model passes + I/O; returns a recorder the test configures per scenario."""
    rec = {"tracking": None, "frames": None, "rate": None, "passed_kwargs": None}

    monkeypatch.setattr(tasks, "async_session_factory", TestSessionLocal)
    async def fake_download(key): return "/tmp/does-not-matter.mp4"
    monkeypatch.setattr(tasks, "download_from_storage", fake_download)
    monkeypatch.setattr(tasks, "cleanup_local_file", lambda p: None)
    monkeypatch.setattr(tasks, "extract_thumbnail", lambda src, dst: None)
    monkeypatch.setattr(tasks, "track_persons", lambda path, model, stride=1: rec["tracking"])

    def fake_pass(path, annotate_output_path=None, progress_callback=None, subject_boxes=None, diagnostics=None, stride=None,
                  full_frame_fallback=True):
        rec["passed_kwargs"] = {"subject_boxes": subject_boxes, "full_frame_fallback": full_frame_fallback}
        return rec["frames"], rec["rate"]

    monkeypatch.setattr(tasks, "run_mediapipe_full_pass", fake_pass)
    return rec


async def new_video(db) -> Video:
    coach = await make_user(db, "coach@pose.example.com")
    athlete = await make_athlete(db, coach.id)
    return await make_video(db, athlete.id, coach.id, status=VideoProcessingStatus.pending_upload)


async def counts(db, video_id):
    poses = await db.scalar(select(func.count()).select_from(PoseFrame).where(PoseFrame.video_id == video_id))
    mets = await db.scalar(select(func.count()).select_from(BiomechanicalMetric).where(BiomechanicalMetric.video_id == video_id))
    return poses, mets


@pytest.mark.asyncio
async def test_wide_group_clip_at_49pct_fails_honestly_with_diagnostics_and_stores_nothing(db_session, pipeline):
    pipeline["tracking"] = make_tracking(main_len=95, main_h=120.0, others=[(90, 110), (80, 115), (70, 100)])
    pipeline["frames"], pipeline["rate"] = frames(49, 100)
    video = await new_video(db_session)

    result = await tasks.process_video({}, video.id)
    await db_session.refresh(video)

    assert result == {"status": "failed", "reason": "subject_too_small"}
    assert video.processing_status == VideoProcessingStatus.failed
    assert video.error_code == "subject_too_small"
    assert "4 people were tracked" in video.error_message and "track 1" in video.error_message
    assert video.person_count_detected == 4 and float(video.detection_rate) == pytest.approx(0.49)  # persisted on failure
    assert await counts(db_session, video.id) == (0, 0), "no score-able data may be stored for unmeasurable footage"


@pytest.mark.asyncio
async def test_unstable_selection_fails_with_its_own_code(db_session, pipeline):
    pipeline["tracking"] = make_tracking(main_len=50, main_h=420.0, others=[(95, 410), (60, 400)])
    pipeline["frames"], pipeline["rate"] = frames(45, 100)
    video = await new_video(db_session)
    assert (await tasks.process_video({}, video.id))["reason"] == "multiple_people_subject_unstable"
    await db_session.refresh(video)
    assert video.error_code == "multiple_people_subject_unstable" and video.person_count_detected == 3


@pytest.mark.asyncio
async def test_multi_person_clip_is_analysed_without_full_frame_fallback_and_carries_a_note(db_session, pipeline):
    pipeline["tracking"] = make_tracking(main_len=95, main_h=420.0, others=[(90, 400)])
    pipeline["frames"], pipeline["rate"] = frames(92, 100)
    video = await new_video(db_session)

    assert (await tasks.process_video({}, video.id))["status"] == "completed"
    await db_session.refresh(video)
    assert pipeline["passed_kwargs"]["full_frame_fallback"] is False       # never measure someone else
    assert video.processing_status == VideoProcessingStatus.completed
    assert "track 1" in video.coverage_caveat and "Multiple people" in video.coverage_caveat
    assert video.person_count_detected == 2
    assert (await counts(db_session, video.id))[1] > 0


@pytest.mark.asyncio
async def test_single_person_clip_keeps_full_frame_fallback_and_has_no_caveat(db_session, pipeline):
    pipeline["tracking"] = make_tracking()
    pipeline["frames"], pipeline["rate"] = frames(95, 100)
    video = await new_video(db_session)
    await tasks.process_video({}, video.id)
    await db_session.refresh(video)
    assert pipeline["passed_kwargs"]["full_frame_fallback"] is True
    assert video.coverage_caveat is None and video.processing_status == VideoProcessingStatus.completed


@pytest.mark.asyncio
async def test_partial_coverage_completes_with_an_explicit_caveat(db_session, pipeline):
    pipeline["tracking"] = make_tracking(main_h=420.0)
    pipeline["frames"], pipeline["rate"] = frames(55, 100)
    video = await new_video(db_session)
    assert (await tasks.process_video({}, video.id))["coverage"] == "partial"
    await db_session.refresh(video)
    assert video.processing_status == VideoProcessingStatus.completed
    assert "55%" in video.coverage_caveat and "lower confidence" in video.coverage_caveat
    assert float(video.detection_rate) == pytest.approx(0.55)


@pytest.mark.asyncio
async def test_no_person_failure_records_zero_people(db_session, pipeline):
    pipeline["tracking"] = {"person_counts": [0] * 50, "tracks": {}, "main_track_id": None, "max_persons": 0,
                            "frames_processed": 50, "tracked": False, "frame_height": H, "frame_width": 1920}
    video = await new_video(db_session)
    assert (await tasks.process_video({}, video.id))["reason"] == "no_person_detected"
    await db_session.refresh(video)
    assert video.person_count_detected == 0 and float(video.detection_rate) == 0.0


@pytest.mark.asyncio
async def test_caveated_videos_never_feed_the_population_baseline(db_session):
    coach = await make_user(db_session, "coach@base.example.com")
    athlete = await make_athlete(db_session, coach.id)
    rng = np.random.default_rng(1)
    clean = await make_video(db_session, athlete.id, coach.id, metrics={"knee_flexion_angle_left": list(rng.normal(90, 8, 50))})
    caveated = await make_video(db_session, athlete.id, coach.id, metrics={"knee_flexion_angle_left": list(rng.normal(90, 8, 50))})
    caveated.coverage_caveat = "Partial coverage: ..."
    await db_session.commit()

    required = ["knee_flexion_angle_left.p95"]
    baseline = await fetch_baseline_set(db_session, "squatting", "00000000-0000-0000-0000-000000000000", required)
    assert baseline.videos == 1 and baseline.athletes == 1   # only the clean video is in the population
    assert clean.id != caveated.id
