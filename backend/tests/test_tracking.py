"""Multi-person tracking tests — main-subject selection, cropping, box helpers.

Pure unit tests: no YOLO weights, no MediaPipe model, no database.
Video IO uses tiny synthetic clips written to tmp_path.
"""

import numpy as np
import pytest

from app.modules.pose.coverage import summarize_tracking
from app.modules.pose.pipeline import (
    _extract_boxes_and_ids,
    crop_to_box,
    map_crop_norm_to_full,
    merge_track_fragments,
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

    def track(self, frame, persist=True, verbose=False, **kwargs):
        item = self.script[min(self.calls, len(self.script) - 1)]
        self.calls += 1
        return [_FakeResult(*item)]


class _FakeDetectOnlyModel:
    """Plain detect mode — no .track, no IDs."""

    def __call__(self, frame, verbose=False, **kwargs):
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


# --- merge_track_fragments: one lateral athlete split across IDs ---

FPS = 30.0


def frag_box(x: float, h: float = 400.0):
    return (x, 100.0, x + h * 0.4, 100.0 + h)


def frag_track(frames, x0: float, dx: float = 0.0, h: float = 400.0):
    return {f: frag_box(x0 + dx * (f - frames[0]), h) for f in frames}


def test_merge_id_switch_fragments_of_one_lateral_athlete():
    # One person cutting: track 1 (frames 0-49) hands off to track 2 (frames 55-99),
    # box drifting 50 px across the 0.2 s gap — a single subject, not two people.
    tracks = {
        1: frag_track(range(0, 50), 100.0, dx=1.0),
        2: frag_track(range(55, 100), 150.0, dx=1.0),
    }
    merged = merge_track_fragments(tracks, FPS)
    assert list(merged) == [1]
    assert len(merged[1]) == 95
    assert merged[1][0] == tracks[1][0] and merged[1][99] == tracks[2][99]


def test_merge_is_transitive_across_three_fragments():
    tracks = {
        5: frag_track(range(0, 30), 100.0),
        7: frag_track(range(35, 60), 105.0),
        9: frag_track(range(65, 100), 110.0),
    }
    merged = merge_track_fragments(tracks, FPS)
    assert list(merged) == [5]  # earliest fragment's ID wins
    assert len(merged[5]) == 90


def test_merge_never_combines_simultaneous_people():
    # Two athletes on screen at the same time (crossing paths): never one person,
    # even with identical size and close boxes.
    tracks = {
        1: frag_track(range(0, 100), 100.0),
        2: frag_track(range(40, 100), 110.0),
    }
    merged = merge_track_fragments(tracks, FPS)
    assert set(merged) == {1, 2}


def test_merge_rejects_teleport_across_the_frame():
    # Disjoint in time, but the second box is 1500 px away after a 0.1 s gap —
    # no human moves that fast: two different people.
    tracks = {
        1: frag_track(range(0, 50), 100.0),
        2: frag_track(range(53, 100), 1600.0),
    }
    assert set(merge_track_fragments(tracks, FPS)) == {1, 2}


def test_merge_rejects_very_different_box_sizes():
    # Disjoint, adjacent in time and space, but 400 px vs 150 px tall —
    # an adult and a child / background person, not the same subject.
    tracks = {
        1: frag_track(range(0, 50), 100.0, h=400.0),
        2: frag_track(range(52, 100), 105.0, h=150.0),
    }
    assert set(merge_track_fragments(tracks, FPS)) == {1, 2}


def test_merge_rejects_long_gap_between_fragments():
    # Same size, same spot, but 3 s apart — someone left and someone else arrived.
    tracks = {
        1: frag_track(range(0, 50), 100.0),
        2: frag_track(range(140, 190), 100.0),
    }
    assert set(merge_track_fragments(tracks, FPS)) == {1, 2}


def test_track_persons_merges_fragments_end_to_end(tmp_path):
    # ID switch mid-clip through _FakeTrackModel: the merged result must be ONE
    # substantive track at full coverage, with no false multi-person diagnosis.
    clip = _make_clip(tmp_path / "cut.mp4")
    script = [
        ([[100, 100, 260, 500]], [1]),
        ([[102, 100, 262, 500]], [1]),
        ([[104, 100, 264, 500]], [1]),
        ([[106, 100, 266, 500]], [2]),
        ([[108, 100, 268, 500]], [2]),
        ([[110, 100, 270, 500]], [2]),
    ]
    out = track_persons(clip, _FakeTrackModel(script), stride=1, fps=FPS)
    assert out["main_track_id"] == 1
    assert len(out["tracks"]) == 1 and len(out["tracks"][1]) == 6
    s = summarize_tracking(out)
    assert s.substantive_tracks == 1 and not s.multi_person
    assert s.main_track_coverage == 1.0
