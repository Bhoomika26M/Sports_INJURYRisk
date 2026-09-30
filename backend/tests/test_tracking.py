"""Multi-person tracking tests — main-subject selection, cropping, box helpers.

Pure unit tests: no YOLO weights, no MediaPipe model, no database.
Video IO uses tiny synthetic clips written to tmp_path.
"""

import numpy as np
import pytest

from app.modules.pose.pipeline import (
    _extract_boxes_and_ids,
    crop_to_box,
    map_crop_norm_to_full,
    select_main_track,
    track_persons,
)


# --- select_main_track ---

def test_select_main_track_prefers_most_frames():
    tracks = {
        1: {0: (0, 0, 10, 10), 1: (0, 0, 10, 10)},
        2: {0: (0, 0, 100, 100), 1: (0, 0, 100, 100), 2: (0, 0, 100, 100)},
    }
    assert select_main_track(tracks) == 2


def test_select_main_track_tiebreak_largest_median_area():
    tracks = {
        1: {0: (0, 0, 10, 10), 1: (0, 0, 10, 10)},
        2: {0: (0, 0, 50, 50), 1: (0, 0, 50, 50)},
    }
    assert select_main_track(tracks) == 2


def test_select_main_track_empty_and_single():
    assert select_main_track({}) is None
    assert select_main_track({7: {3: (0, 0, 5, 5)}}) == 7


# --- crop_to_box ---

def test_crop_to_box_pads_and_clamps():
    frame = np.zeros((200, 300, 3), dtype=np.uint8)
    crop, ox, oy = crop_to_box(frame, (100, 50, 200, 150), pad_ratio=0.1)
    # 100x100 box + 10px pad each side
    assert (ox, oy) == (90, 40)
    assert crop.shape == (120, 120, 3)


def test_crop_to_box_clamps_at_borders():
    frame = np.zeros((200, 300, 3), dtype=np.uint8)
    crop, ox, oy = crop_to_box(frame, (0, 0, 50, 50), pad_ratio=0.5)
    assert (ox, oy) == (0, 0)
    assert crop.shape[0] <= 200 and crop.shape[1] <= 300


def test_crop_to_box_degenerate_or_tiny_falls_back_to_full_frame():
    frame = np.zeros((200, 300, 3), dtype=np.uint8)
    crop, ox, oy = crop_to_box(frame, (10, 10, 10, 10))
    assert crop is frame and (ox, oy) == (0, 0)
    crop, ox, oy = crop_to_box(frame, (0, 0, 5, 5))
    assert crop is frame and (ox, oy) == (0, 0)


# --- map_crop_norm_to_full ---

def test_map_crop_norm_to_full_numbers():
    # crop origin (100, 50), crop 200x100, full 400x200; center of crop -> (0.5, 0.5)
    fx, fy = map_crop_norm_to_full(0.5, 0.5, 100, 50, 200, 100, 400, 200)
    assert fx == pytest.approx(0.5) and fy == pytest.approx(0.5)
    # crop top-left -> origin / full size
    fx, fy = map_crop_norm_to_full(0.0, 0.0, 100, 50, 200, 100, 400, 200)
    assert fx == pytest.approx(0.25) and fy == pytest.approx(0.25)


def test_map_crop_norm_to_full_degenerate_is_identity():
    assert map_crop_norm_to_full(0.3, 0.4, 0, 0, 0, 100, 400, 200) == (0.3, 0.4)


# --- _extract_boxes_and_ids ---

class _FakeBoxes:
    def __init__(self, xyxy, ids):
        self.xyxy = np.array(xyxy, dtype=float).reshape(-1, 4)
        self.id = None if ids is None else np.array(ids, dtype=float)


class _FakeResult:
    def __init__(self, xyxy, ids):
        self.boxes = _FakeBoxes(xyxy, ids)


def test_extract_boxes_with_and_without_ids():
    dets = _extract_boxes_and_ids(_FakeResult([[0, 0, 10, 10], [20, 20, 30, 30]], [3, 5]))
    assert dets == [(3, (0.0, 0.0, 10.0, 10.0)), (5, (20.0, 20.0, 30.0, 30.0))]
    dets = _extract_boxes_and_ids(_FakeResult([[0, 0, 10, 10]], None))
    assert dets == [(None, (0.0, 0.0, 10.0, 10.0))]


def test_extract_boxes_empty_or_missing():
    assert _extract_boxes_and_ids(_FakeResult([], [])) == []
    assert _extract_boxes_and_ids(object()) == []


# --- track_persons with a fake model (no weights) ---

def _make_clip(path, n_frames=6, w=320, h=240):
    import cv2

    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10, (w, h))
    for i in range(n_frames):
        writer.write(np.full((h, w, 3), i * 10, dtype=np.uint8))
    writer.release()
    return str(path)


class _FakeTrackModel:
    """Replays a per-frame script of (xyxy, ids) through a .track() API."""

    def __init__(self, script):
        self.script = script
        self.calls = 0

    def track(self, frame, persist=True, verbose=False):
        item = self.script[min(self.calls, len(self.script) - 1)]
        self.calls += 1
        return [_FakeResult(*item)]


class _FakeDetectOnlyModel:
    """Plain detect mode — no .track, no IDs."""

    def __call__(self, frame, verbose=False):
        return [_FakeResult([[0, 0, 10, 10]], None)]


def test_track_persons_selects_consistent_main_subject(tmp_path):
    clip = _make_clip(tmp_path / "clip.mp4")
    # Track 1 present in all 6 frames (small box); track 2 in 2 frames (big box).
    script = [
        ([[0, 0, 10, 20], [100, 100, 200, 200]], [1, 2]),
        ([[0, 0, 10, 20], [100, 100, 200, 200]], [1, 2]),
        ([[0, 0, 10, 20]], [1]),
        ([[0, 0, 10, 20]], [1]),
        ([[0, 0, 10, 20]], [1]),
        ([[0, 0, 10, 20]], [1]),
    ]
    out = track_persons(clip, _FakeTrackModel(script), stride=1)
    assert out["max_persons"] == 2
    assert out["main_track_id"] == 1  # presence beats size
    assert out["tracked"] is True
    assert len(out["tracks"][1]) == 6
    assert out["person_counts"] == [2, 2, 1, 1, 1, 1]


def test_track_persons_empty_video_reports_no_person(tmp_path):
    clip = _make_clip(tmp_path / "empty.mp4", n_frames=3)
    out = track_persons(clip, _FakeTrackModel([([], [])]), stride=1)
    assert out["max_persons"] == 0
    assert out["main_track_id"] is None
    assert out["person_counts"] == [0, 0, 0]


def test_track_persons_without_tracker_api_falls_back_untracked(tmp_path):
    clip = _make_clip(tmp_path / "detect.mp4", n_frames=2)
    out = track_persons(clip, _FakeDetectOnlyModel(), stride=1)
    assert out["person_counts"] == [1, 1]
    assert out["tracked"] is False
    assert out["main_track_id"] is None
