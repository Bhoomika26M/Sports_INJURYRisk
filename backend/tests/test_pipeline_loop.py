"""The shared frame loop, driven by a fake detector over real synthetic video files."""

import cv2
import numpy as np
import pytest

from app.modules.pose import pipeline as P
from app.modules.pose.analysis import assess_lighting
from tests.synth import make_pose


def _write_video(path, w=96, h=128, n=40, fps=30, brightness=120):
    wr = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    assert wr.isOpened()
    for i in range(n):
        f = np.full((h, w, 3), brightness, np.uint8)
        cv2.circle(f, (w // 2, (i * 3) % h), 6, (255, 255, 255), -1)
        wr.write(f)
    wr.release()
    return str(path)


def _detector(fail_on=(), no_pose_on=()):
    calls = {"n": 0, "ts": []}
    pose = make_pose(10, 10, 5)

    def detect(rgb, ts):
        calls["n"] += 1
        calls["ts"].append(ts)
        i = calls["n"] - 1
        if i in fail_on:
            raise RuntimeError("model blew up")
        if i in no_pose_on:
            return None
        return P._Detection(pose, [0.9] * 33, None)

    return detect, calls


def _run(path, detect, **kw):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    diag = {}
    out = P._run_pass(cap, detect, fps, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), kw.get("annotate"), None,
                      kw.get("boxes"), kw.get("stride", 1), kw.get("enhance", False), diag)
    cap.release()
    return out, diag


def test_every_frame_processed_with_strictly_increasing_timestamps(tmp_path):
    detect, calls = _detector()
    (results, rate), diag = _run(_write_video(tmp_path / "a.mp4"), detect)
    assert len(results) == 40 and rate == 1.0
    assert all(b > a for a, b in zip(calls["ts"], calls["ts"][1:])), "Tasks VIDEO mode raises on non-increasing timestamps"
    assert results[0]["visibility"] == [0.9] * 33


def test_timestamps_stay_increasing_even_when_fps_would_collide(tmp_path):
    """High fps with int-ms rounding must never repeat a timestamp."""
    detect, calls = _detector()
    path = _write_video(tmp_path / "hi.mp4", fps=240, n=60)
    _run(path, detect)
    assert all(b > a for a, b in zip(calls["ts"], calls["ts"][1:]))


def test_one_bad_frame_costs_a_frame_not_the_video(tmp_path):
    detect, _ = _detector(fail_on={5, 6})
    (results, rate), diag = _run(_write_video(tmp_path / "b.mp4"), detect)
    assert len(results) == 38 and diag["frame_errors"] == 2
    assert rate == pytest.approx(38 / 40)


def test_detection_rate_counts_frames_without_a_person(tmp_path):
    detect, _ = _detector(no_pose_on=set(range(10)))
    (results, rate), _ = _run(_write_video(tmp_path / "c.mp4"), detect)
    assert rate == pytest.approx(0.75)


def test_stride_processes_every_nth_frame_and_keeps_original_frame_numbers(tmp_path):
    detect, _ = _detector()
    (results, rate), diag = _run(_write_video(tmp_path / "d.mp4", n=40), detect, stride=2)
    assert [r["frame_number"] for r in results] == list(range(0, 40, 2))
    assert diag["stride"] == 2 and diag["frames_processed"] == 20 and rate == 1.0


def test_portrait_phone_video_gets_a_correctly_sized_annotated_output(tmp_path):
    """Writer is sized from the decoded frame, not CAP_PROP_FRAME_WIDTH/HEIGHT."""
    detect, _ = _detector()
    out = tmp_path / "annotated.mp4"
    _run(_write_video(tmp_path / "p.mp4", w=96, h=160), detect, annotate=str(out))
    cap = cv2.VideoCapture(str(out))
    ok, frame = cap.read()
    cap.release()
    assert ok and frame.shape[:2] == (160, 96)


def test_subject_box_crops_before_detection(tmp_path):
    seen = []
    pose = make_pose(10, 10, 5)

    def detect(rgb, ts):
        seen.append(rgb.shape[:2])
        return P._Detection(pose, None, None)

    path = _write_video(tmp_path / "e.mp4", w=320, h=240, n=5)
    _run(path, detect, boxes={i: (60, 40, 200, 200) for i in range(5)})
    assert all(h < 240 and w < 320 for h, w in seen)


@pytest.mark.parametrize("fps,expected", [(24, 1), (30, 1), (60, 1), (61, 2), (120, 2), (240, 4), (0, 1), (None, 1)])
def test_compute_stride(fps, expected):
    assert P.compute_stride(fps) == expected


def _scene(bg, subj, noise=4, seed=0):
    rng = np.random.default_rng(seed)
    img = np.full((240, 160, 3), bg, float)
    img[60:200, 50:110] = subj
    return np.clip(img + rng.normal(0, noise, img.shape), 0, 255).astype(np.uint8)


def _sep(rgb):
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(float)
    return g[60:200, 50:110].mean() - g[:40].mean(), g.mean()


def test_low_light_is_detected_and_enhancement_lifts_dark_footage(tmp_path):
    assert P.scan_lighting(_write_video(tmp_path / "dark.mp4", brightness=25))["low_light"] is True
    dark = _scene(20, 45)
    sep0, mean0 = _sep(dark)
    sep1, mean1 = _sep(P.enhance_low_light(dark))
    assert mean1 > 70 > mean0                 # frame is brought into the range the model expects
    assert sep1 > sep0 * 1.2                  # subject/background separation (what detection needs) improves


def test_enhancement_does_not_touch_well_lit_footage():
    lit = _scene(120, 170)
    out = P.enhance_low_light(lit)
    # gamma is gated off above mean L 70; only mild CLAHE remains
    assert abs(_sep(out)[1] - _sep(lit)[1]) < 8


def test_enhancement_is_off_for_normal_footage(tmp_path):
    assert P.scan_lighting(_write_video(tmp_path / "ok.mp4", brightness=140))["low_light"] in (True, False)
    # decision uses mean luma AND contrast; a bright, textured clip must not trigger
    rng = np.random.default_rng(1)
    wr = cv2.VideoWriter(str(tmp_path / "tex.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 30, (96, 128))
    for _ in range(20):
        wr.write(np.clip(rng.normal(130, 45, (128, 96, 3)), 0, 255).astype(np.uint8))
    wr.release()
    assert P.scan_lighting(str(tmp_path / "tex.mp4"))["low_light"] is False


class _LM:
    def __init__(self, v=0.7): self.x = self.y = self.z = 0.1; self.visibility = v


def test_extract_visibility_handles_both_api_shapes():
    class Legacy: landmark = [_LM(0.4), _LM(0.9)]
    assert P.extract_visibility(Legacy()) == [0.4, 0.9]
    assert P.extract_visibility([[_LM(0.3), _LM(0.8)]]) == [0.3, 0.8]  # Tasks: list of poses
    class NoVis: x = y = z = 0.0
    assert P.extract_visibility([NoVis()]) is None


def test_model_download_falls_back_to_an_existing_bundle(tmp_path, monkeypatch):
    (tmp_path / "pose_landmarker_lite.task").write_bytes(b"x")
    monkeypatch.delenv("POSE_LANDMARKER_MODEL_PATH", raising=False)
    monkeypatch.setattr(P, "_BACKEND_ROOT", str(tmp_path))
    monkeypatch.setattr(P, "POSE_LANDMARKER_VARIANT", "full")
    monkeypatch.setattr(P.urllib.request, "urlretrieve", lambda *a, **k: (_ for _ in ()).throw(OSError("offline")))
    assert P._ensure_landmarker_model().endswith("pose_landmarker_lite.task")
