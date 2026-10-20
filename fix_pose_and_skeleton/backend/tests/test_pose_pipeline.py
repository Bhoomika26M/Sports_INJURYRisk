"""End-to-end: upload -> real run_analysis job -> results, video file and skeleton endpoints.

The MediaPipe model itself is replaced by a fake backend that reports a synthetic squat,
so these tests need no model download. They check everything around the model.
"""

import cv2
import numpy as np

from app.services import pose_estimation
from app.services.analysis_pipeline import run_analysis
from tests.synthetic import make_sequence
from tests.test_api import _setup_athlete, make_video

FRAMES = 120


class FakeBackend:
    """Stands in for MediaPipe: returns 33 landmarks taken from a synthetic squat."""

    def __init__(self, hide=()):
        self.seq = make_sequence(frames=FRAMES)
        self.i = 0
        self.hide = set(hide)

    def detect(self, rgb, timestamp_ms):
        pos = self.seq[min(self.i, FRAMES - 1)]
        self.i += 1
        lms = [(0.5, 0.5, 0.0)] * 33
        lms = list(lms)
        for name, mp_index in pose_estimation._MEDIAPIPE_LANDMARKS.items():
            x, y = pos[pose_estimation.JOINT_INDEX[name]]
            vis = 0.0 if name in self.hide else 0.99
            lms[mp_index] = (float(x), float(y), vis)
        return lms

    def close(self):
        pass


def _upload(client, tmp_path, monkeypatch, backend):
    monkeypatch.setattr("app.services.analysis_pipeline.SessionLocal", client.app.state.testing_session)
    monkeypatch.setattr(pose_estimation.PoseEstimator, "_make_backend", lambda self: backend)
    h, a = _setup_athlete(client)
    path = tmp_path / "squat.mp4"
    make_video(path, frames=FRAMES, size=(640, 480))
    with path.open("rb") as f:
        r = client.post("/api/v1/videos/upload", headers=h, data={"athlete_id": a["id"], "activity": "squatting"},
                        files={"file": ("squat.mp4", f, "video/mp4")})
    assert r.status_code == 201, r.text
    return h, r.json()["id"]


def test_full_job_produces_results_and_skeleton(client, tmp_path, monkeypatch):
    h, vid = _upload(client, tmp_path, monkeypatch, FakeBackend())
    run_analysis(vid)

    video = client.get(f"/api/v1/videos/{vid}", headers=h).json()
    assert video["status"] == "completed", video["error"]

    analyses = client.get("/api/v1/analyses", headers=h).json()
    assert len(analyses) == 1 and analyses[0]["video_id"] == vid
    detail = client.get(f"/api/v1/analyses/{analyses[0]['id']}", headers=h).json()
    assert detail["injury_risks"] and detail["recommendations"]

    pose = client.get(f"/api/v1/videos/{vid}/pose", headers=h).json()
    assert len(pose["frames"]) == FRAMES and len(pose["frames"][0]) == len(pose["joint_names"])
    assert pose["frames"][0][0][0] is not None  # joints were actually located

    f = client.get(f"/api/v1/videos/{vid}/file", headers=h)
    assert f.status_code == 200 and f.headers["content-type"].startswith("video/") and len(f.content) > 1000


def test_missing_legs_gives_a_readable_failure(client, tmp_path, monkeypatch):
    hidden = ("left_knee", "right_knee", "left_ankle", "right_ankle", "left_foot", "right_foot")
    h, vid = _upload(client, tmp_path, monkeypatch, FakeBackend(hide=hidden))
    run_analysis(vid)
    video = client.get(f"/api/v1/videos/{vid}", headers=h).json()
    assert video["status"] == "failed"
    assert "left knee" in video["error"] and "head to feet" in video["error"]


def test_video_file_is_access_controlled(client, tmp_path, monkeypatch):
    from tests.conftest import login, register

    h, vid = _upload(client, tmp_path, monkeypatch, FakeBackend())
    register(client, "other@example.com")
    other = login(client, "other@example.com")
    assert client.get(f"/api/v1/videos/{vid}/file", headers=other).status_code == 404
    assert client.get(f"/api/v1/videos/{vid}/file").status_code == 401


def test_tasks_backend_glue(monkeypatch):
    """The current-MediaPipe backend: timestamps strictly increase and landmarks are converted."""
    from types import SimpleNamespace

    import mediapipe as mp
    from mediapipe.tasks.python import vision

    seen = []

    class FakeLandmarker:
        def detect_for_video(self, image, ts):
            seen.append(ts)
            lm = SimpleNamespace(x=0.25, y=0.75, visibility=0.9)
            return SimpleNamespace(pose_landmarks=[[lm] * 33])

        def close(self):
            pass

    monkeypatch.setattr(pose_estimation, "ensure_pose_model", lambda: "model.task")
    monkeypatch.setattr(vision.PoseLandmarker, "create_from_options", staticmethod(lambda options: FakeLandmarker()))
    backend = pose_estimation._TasksBackend(mp)
    frame = np.zeros((48, 64, 3), dtype=np.uint8)
    out = backend.detect(frame, 100)
    backend.detect(frame, 100)  # same timestamp twice must still be accepted
    backend.detect(frame, 50)
    assert out[0] == (0.25, 0.75, 0.9) and len(out) == 33
    assert seen == sorted(set(seen)) and len(seen) == 3
