"""An "auto" upload declares neither label: the footage decides both, or the upload fails.

Fail-closed on purpose: the classifier is an uncalibrated heuristic (tests/test_classification.py is synthetic only), so a
verdict below WARN_MIN_CONF must never choose which baseline a clip joins. See docs/DECISIONS.md 2026-10-09.
"""

import pytest
from sqlalchemy import select

from app.modules.biomechanics.classification import AUTO
from app.modules.pose import tasks
from app.modules.pose.processing import analyze_frames, identify_labels
from app.modules.pose.reprocess import reprocess_video
from app.modules.video.models import PoseFrame, Video, VideoProcessingStatus
from tests.conftest import auth_header
from tests.synth import run_frames, squat_frames
from tests.test_classification import _still, jump_frames, knee_frames
from tests.test_pose_tasks import counts, make_tracking, new_video, pipeline  # noqa: F401  (pipeline is a fixture)
from tests.test_video_api import _coach_with_athlete

FPS = 30.0


def _standing(seconds=6):
    return knee_frames(_still(seconds))


# ------------------------------------------------------------------ the upload request
async def _upload_url(client, token, athlete_id, movement, view):
    return await client.post("/api/v1/videos/upload-url", headers=auth_header(token), json={
        "athlete_id": athlete_id, "movement_type": movement, "camera_view": view, "original_filename": "clip.mp4"})


async def test_auto_must_be_declared_for_both_labels_or_neither(client):
    token, athlete_id = await _coach_with_athlete(client)
    assert (await _upload_url(client, token, athlete_id, AUTO, "sagittal")).status_code == 422
    assert (await _upload_url(client, token, athlete_id, "squatting", AUTO)).status_code == 422
    assert (await _upload_url(client, token, athlete_id, "skydiving", "sagittal")).status_code == 400  # still checked


async def test_auto_upload_is_accepted_and_waits_for_the_worker_to_label_it(client):
    token, athlete_id = await _coach_with_athlete(client)
    r = await _upload_url(client, token, athlete_id, AUTO, AUTO)
    assert r.status_code == 200, r.text
    video = (await client.get(f"/api/v1/videos/{r.json()['video_id']}", headers=auth_header(token))).json()
    assert (video["movement_type"], video["camera_view"]) == (AUTO, AUTO)


# ------------------------------------------------------------------ identify_labels
@pytest.mark.parametrize("name,frames,expected", [
    ("squat", squat_frames(), ("squatting", "sagittal")),
    ("run", run_frames(170, kmax=80, seconds=8), ("running", "sagittal")),
    ("sprint", run_frames(230, kmax=80, seconds=8), ("sprinting", "sagittal")),
    ("standing still", _standing(), None),                 # nothing to identify
    ("jump", jump_frames(), None),                         # jump vs landing is capped below the bar: pick it by hand
    ("no frames", [], None),
])
def test_identify_labels_answers_only_when_sure(name, frames, expected):
    assert identify_labels(frames, FPS) == expected


def test_auto_analysis_says_the_labels_were_identified_not_declared():
    frames = squat_frames()
    _, declared = analyze_frames(frames, "squatting", "sagittal", FPS)
    _, auto = analyze_frames(frames, "squatting", "sagittal", FPS, auto=True)
    assert declared["classification"]["declared"] == {"movement_type": "squatting", "camera_view": "sagittal"}
    c = auto["classification"]
    assert c["declared"] == {"movement_type": AUTO, "camera_view": AUTO}
    assert c["agrees"] == {"movement_type": None, "camera_view": None} and c["suggested"] == c["agrees"]
    assert (c["movement_type"], c["camera_view"]) == ("squatting", "sagittal")   # the verdict is still reported


# ------------------------------------------------------------------ the worker
async def _auto_video(db):
    video = await new_video(db)
    video.movement_type = video.camera_view = AUTO
    await db.commit()
    return video


async def test_worker_labels_an_auto_clip_from_its_footage_and_keeps_saying_so(db_session, pipeline):
    frames = squat_frames()
    pipeline["tracking"] = make_tracking(frames_n=len(frames), main_len=len(frames))
    pipeline["frames"], pipeline["rate"] = frames, 1.0
    video = await _auto_video(db_session)

    assert (await tasks.process_video({}, video.id))["status"] == "completed"
    await db_session.refresh(video)
    assert (video.movement_type, video.camera_view) == ("squatting", "sagittal")   # the labels are real from here on
    assert video.analysis["classification"]["declared"]["movement_type"] == AUTO
    assert video.analysis["movement"]["movement_type"] == "squatting" and video.analysis["movement"]["reps"]["n_reps"] >= 4
    assert (await counts(db_session, video.id))[1] > 0

    await reprocess_video(db_session, video)         # a later reprocess must not turn "identified" into "declared"
    await db_session.refresh(video)
    assert video.analysis["classification"]["declared"]["movement_type"] == AUTO


async def test_worker_fails_an_unidentifiable_auto_clip_before_storing_anything(db_session, pipeline):
    frames = _standing()
    pipeline["tracking"] = make_tracking(frames_n=len(frames), main_len=len(frames))
    pipeline["frames"], pipeline["rate"] = frames, 1.0
    video = await _auto_video(db_session)

    assert await tasks.process_video({}, video.id) == {"status": "failed", "reason": "movement_not_identified"}
    await db_session.refresh(video)
    assert video.processing_status == VideoProcessingStatus.failed and video.error_code == "movement_not_identified"
    assert "choose them yourself" in video.error_message
    assert (video.movement_type, video.camera_view) == (AUTO, AUTO)                 # nothing was guessed
    assert await counts(db_session, video.id) == (0, 0)
    assert not (await db_session.scalars(select(PoseFrame).where(PoseFrame.video_id == video.id))).all()


async def test_a_declared_label_is_never_replaced_by_the_classifier(db_session, pipeline):
    frames = run_frames(170, kmax=80, seconds=8)                 # a run, uploaded as a squat
    pipeline["tracking"] = make_tracking(frames_n=len(frames), main_len=len(frames))
    pipeline["frames"], pipeline["rate"] = frames, 1.0
    video = await new_video(db_session)                          # declared squatting / sagittal

    await tasks.process_video({}, video.id)
    await db_session.refresh(video)
    assert (video.movement_type, video.camera_view) == ("squatting", "sagittal")
    assert video.analysis["classification"]["declared"]["movement_type"] == "squatting"
    assert video.analysis["classification"]["agrees"]["movement_type"] is False        # T1: warn and suggest only
    assert isinstance(video, Video)
