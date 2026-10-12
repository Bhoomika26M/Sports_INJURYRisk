"""The sampled tracker, the playable annotated video, and the in-process job runner (replaced Redis + arq)."""

import asyncio
import json
import shutil
import subprocess

import cv2
import numpy as np
import pytest
from sqlalchemy import select, update

from app.modules.pose import jobs, pipeline as P
from app.modules.video.models import Video, VideoProcessingStatus
from tests.conftest import TestSessionLocal, auth_header
from tests.factories import make_athlete, make_user, make_video
from tests.test_tracking import _FakeTrackModel, _make_clip
from tests.test_video_api import _coach_with_athlete


# --- tracker sampling ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("fps,stride,expected", [(30, 1, 2), (24, 1, 2), (60, 1, 4), (240, 4, 4), (10, 1, 1)])
def test_detect_every_targets_about_15_hz(monkeypatch, fps, stride, expected):
    monkeypatch.setattr(P, "YOLO_TRACK_FPS", 15)
    assert P.detect_every(fps, stride) == expected


def test_detect_every_zero_means_every_frame(monkeypatch):
    monkeypatch.setattr(P, "YOLO_TRACK_FPS", 0)
    assert P.detect_every(240, 4) == 1


def test_boxes_are_interpolated_between_detections_and_never_across_a_miss():
    track = {0: (0.0, 0.0, 10.0, 20.0), 2: (2.0, 0.0, 12.0, 20.0), 4: (4.0, 0.0, 14.0, 20.0), 8: (8.0, 0.0, 18.0, 20.0)}
    out = P.subject_boxes_for(track, 10, step=2)
    assert out[1] == (1.0, 0.0, 11.0, 20.0)          # between two detections
    assert out[3] == (3.0, 0.0, 13.0, 20.0)
    assert out[5] is None and out[6] is None and out[7] is None   # sample 6 was missed: no invented person
    assert out[8] == track[8] and out[9] == track[8]  # held for the rest of its step
    assert all(out[i] is not None for i in range(0, 5))


def test_track_persons_only_runs_yolo_on_sampled_frames(tmp_path):
    clip = _make_clip(tmp_path / "c.mp4", n_frames=10)
    model = _FakeTrackModel([([[0, 0, 10, 20]], [1])])
    out = P.track_persons(clip, model, stride=1, every=3)
    assert model.calls == 4                       # frames 0, 3, 6, 9
    assert sorted(out["tracks"][1]) == [0, 3, 6, 9] and out["step"] == 3 and out["frames_processed"] == 10
    assert len(out["person_counts"]) == 4         # coverage is measured over the frames YOLO actually saw


def test_track_persons_reports_progress(tmp_path):
    clip = _make_clip(tmp_path / "p.mp4", n_frames=10)
    seen = []
    P.track_persons(clip, _FakeTrackModel([([], [])]), stride=1, progress_callback=seen.append)
    assert seen and seen == sorted(seen) and seen[-1] < 100


# --- annotated video -----------------------------------------------------------------------------------------------

@pytest.mark.skipif(shutil.which("ffprobe") is None or P.ffmpeg_bin() is None, reason="needs ffmpeg + ffprobe")
def test_annotated_video_is_h264_with_even_sides_and_capped_height(tmp_path):
    out = tmp_path / "a.mp4"
    w = P._open_annotated_writer(str(out), 30.0, (1281, 1441))   # odd, taller than the cap
    for _ in range(5):
        w.write(np.zeros((1441, 1281, 3), np.uint8))
    w.release()
    info = json.loads(subprocess.check_output(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name,width,height", "-of", "json", str(out)]))
    s = info["streams"][0]
    assert s["codec_name"] == "h264"              # mp4v (MPEG-4 Part 2) does not play in Chrome / Edge / Firefox
    assert s["height"] <= P.ANNOTATED_MAX_HEIGHT and s["width"] % 2 == 0 and s["height"] % 2 == 0


def test_no_encoder_means_no_annotated_video_not_a_failed_analysis(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "ffmpeg_bin", lambda: None)
    assert P._open_annotated_writer(str(tmp_path / "a.mp4"), 30.0, (96, 160)) is None


# --- job runner ---------------------------------------------------------------------------------------------------

@pytest.fixture
def runner(monkeypatch):
    monkeypatch.setattr(jobs, "async_session_factory", TestSessionLocal)
    monkeypatch.setattr(jobs, "_queue", asyncio.Queue())
    monkeypatch.setattr(jobs, "_ctx", {"yolo_model": object()})
    return jobs


async def test_start_requeues_videos_a_previous_run_left_processing(db_session, runner, monkeypatch):
    coach = await make_user(db_session, "j@t.com")
    athlete = await make_athlete(db_session, coach.id)
    stuck = await make_video(db_session, athlete.id, coach.id, status=VideoProcessingStatus.processing)
    await make_video(db_session, athlete.id, coach.id, status=VideoProcessingStatus.completed)
    ran = []

    async def fake_process(ctx, video_id):
        ran.append(video_id)

    monkeypatch.setattr(jobs, "process_video", fake_process)
    await jobs.start()
    await asyncio.wait_for(jobs._queue.join(), 5)
    await jobs.stop()
    assert ran == [str(stuck.id)]


async def test_missing_models_fail_the_video_at_once_with_a_code(db_session, runner, monkeypatch):
    coach = await make_user(db_session, "m@t.com")
    athlete = await make_athlete(db_session, coach.id)
    v = await make_video(db_session, athlete.id, coach.id, status=VideoProcessingStatus.processing)
    monkeypatch.setattr(jobs, "_ctx", {})

    async def no_models():
        raise OSError("offline")

    async def never(ctx, video_id):
        raise AssertionError("must not start a pass without models")

    monkeypatch.setattr(jobs, "_ensure_models", no_models)
    monkeypatch.setattr(jobs, "process_video", never)
    jobs.enqueue(v.id)
    await jobs.start()
    await asyncio.wait_for(jobs._queue.join(), 5)
    await jobs.stop()
    async with TestSessionLocal() as s:
        row = await s.scalar(select(Video).where(Video.id == v.id))
    assert row.processing_status == VideoProcessingStatus.failed and row.error_code == "models_unavailable"


async def test_a_crashing_job_does_not_stop_the_runner(db_session, runner, monkeypatch):
    coach = await make_user(db_session, "k@t.com")
    athlete = await make_athlete(db_session, coach.id)
    ran = []

    async def flaky(ctx, video_id):
        ran.append(video_id)
        if len(ran) == 1:
            raise RuntimeError("boom")

    monkeypatch.setattr(jobs, "process_video", flaky)
    await jobs.start()
    jobs.enqueue("a")
    jobs.enqueue("b")
    await asyncio.wait_for(jobs._queue.join(), 5)
    await jobs.stop()
    assert ran == ["a", "b"]


# --- confirm-upload ------------------------------------------------------------------------------------------------

async def test_confirming_twice_is_refused_so_a_clip_is_never_stored_twice(client, db_session):
    token, athlete_id = await _coach_with_athlete(client)
    H = auth_header(token)
    up = (await client.post("/api/v1/videos/upload-url", headers=H, json={
        "athlete_id": athlete_id, "movement_type": "squatting", "camera_view": "sagittal", "original_filename": "x.mp4"})).json()
    await db_session.execute(update(Video).where(Video.id == up["video_id"]).values(processing_status=VideoProcessingStatus.processing))
    await db_session.commit()
    again = await client.post(f"/api/v1/videos/{up['video_id']}/confirm-upload", headers=H)
    assert again.status_code == 409
