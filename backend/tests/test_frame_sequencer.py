"""Tests for pose interpolation and the full-rate frame sequencer.

The behaviour that matters:
  * interpolation is linear between two measurements;
  * confidence is never raised above the less certain neighbour;
  * held (unmeasured) frames are released in source order, WITH their pixels,
    and with a pose that moves smoothly across the gap rather than holding
    still or jumping;
  * the first frames - before any measurement exists - do not crash and hold
    the nearest pose rather than collapsing to the origin.
"""

import numpy as np
import pytest

from app.pose.estimator import Keypoint
from app.visualization.frame_sequencer import AnnotatedFrameSequencer
from app.visualization.interpolation import (
    fraction_between,
    interpolate_bbox,
    interpolate_keypoints,
)


def kp(x, y, conf=0.9, name="nose"):
    return Keypoint(x=x, y=y, confidence=conf, name=name)


def pose(x, y, conf=0.9):
    return [kp(x, y, conf, "nose"), kp(x + 10, y + 10, conf, "left_eye")]


def img():
    return np.zeros((2, 2, 3), np.uint8)


# --------------------------------------------------------------------------- #
# interpolation primitives
# --------------------------------------------------------------------------- #

def test_interpolate_endpoints():
    a, b = pose(0, 0), pose(100, 200)
    assert interpolate_keypoints(a, b, 0.0)[0].x == 0
    assert interpolate_keypoints(a, b, 1.0)[0].x == 100


def test_interpolate_midpoint():
    out = interpolate_keypoints(pose(0, 0), pose(100, 200), 0.5)
    assert out[0].x == pytest.approx(50)
    assert out[0].y == pytest.approx(100)


def test_interpolate_confidence_not_raised():
    out = interpolate_keypoints(pose(0, 0, conf=0.2), pose(100, 100, conf=0.9), 0.5)
    assert out[0].confidence <= 0.2 + 1e-9


def test_interpolate_empty_sides():
    assert interpolate_keypoints([], pose(5, 5), 0.5)[0].x == 5
    assert interpolate_keypoints(pose(5, 5), [], 0.5)[0].x == 5


def test_interpolate_mismatched_lengths_snaps_not_blends():
    a = pose(0, 0)                       # 2 landmarks
    b = [kp(100, 100, name="nose")]      # 1 landmark
    assert len(interpolate_keypoints(a, b, 0.25)) == 2   # holds prev
    assert len(interpolate_keypoints(a, b, 0.75)) == 1   # holds next


def test_interpolate_bbox():
    assert interpolate_bbox((0, 0, 10, 10), (10, 20, 30, 40), 0.5) == (5.0, 10.0, 20.0, 25.0)


def test_interpolate_bbox_holds_when_one_side_missing():
    assert interpolate_bbox(None, (1, 2, 3, 4), 0.5) == (1, 2, 3, 4)
    assert interpolate_bbox((1, 2, 3, 4), None, 0.5) == (1, 2, 3, 4)


def test_fraction_between_clamps_and_guards_zero_span():
    assert fraction_between(0.0, 1.0, 0.25) == pytest.approx(0.25)
    assert fraction_between(0.0, 1.0, -5.0) == 0.0
    assert fraction_between(0.0, 1.0, 5.0) == 1.0
    assert fraction_between(1.0, 1.0, 1.0) == 0.0  # no divide by zero


# --------------------------------------------------------------------------- #
# sequencer
# --------------------------------------------------------------------------- #

def test_disabled_sequencer_holds_nothing():
    seq = AnnotatedFrameSequencer(enabled=False)
    seq.hold(1, 0.1, img())
    assert not seq.has_pending
    assert seq.drain(None, None, None) == []


def test_held_frames_released_with_positions_across_gap():
    """Two measurements at t=0 and t=1; a frame at t=0.5 sits midway."""
    seq = AnnotatedFrameSequencer(enabled=True)

    seq.begin_measurement(0.0, pose(0, 0), (0, 0, 10, 10))
    seq.hold(1, 0.5, img())                       # unmeasured, halfway
    ready = seq.drain(pose(100, 100), (100, 100, 200, 200), 1.0)

    assert len(ready) == 1
    frame_index, timestamp, frame, p, bbox = ready[0]
    assert frame_index == 1
    assert timestamp == 0.5
    assert frame.shape == (2, 2, 3)               # pixels travel with the entry
    assert p[0].x == pytest.approx(50)            # midway pose
    assert bbox[0] == pytest.approx(50)           # midway bbox


def test_held_frames_released_in_source_order():
    seq = AnnotatedFrameSequencer(enabled=True)
    seq.begin_measurement(0.0, pose(0, 0), None)
    for i, t in enumerate([0.2, 0.4, 0.6, 0.8], start=1):
        seq.hold(i, t, img())

    ready = seq.drain(pose(100, 100), None, 1.0)
    assert [r[0] for r in ready] == [1, 2, 3, 4]          # ordered
    xs = [r[3][0].x for r in ready]
    assert xs == sorted(xs)                                # monotonic motion


def test_no_measurement_yet_holds_nearest_without_crash():
    seq = AnnotatedFrameSequencer(enabled=True)
    seq.hold(0, 0.0, img())          # precedes any measurement
    ready = seq.drain(pose(50, 50), None, 1.0)
    assert len(ready) == 1
    assert ready[0][3][0].x == pytest.approx(50)   # holds next, not the origin


def test_missing_next_pose_holds_previous():
    seq = AnnotatedFrameSequencer(enabled=True)
    seq.begin_measurement(0.0, pose(7, 7), None)
    seq.hold(1, 0.5, img())
    ready = seq.drain(None, None, None)
    assert ready[0][3][0].x == pytest.approx(7)    # held, not extrapolated


def test_drain_clears_pending():
    seq = AnnotatedFrameSequencer(enabled=True)
    seq.hold(1, 0.1, img())
    assert seq.has_pending
    seq.drain(None, None, None)
    assert not seq.has_pending
    assert seq.drain(None, None, None) == []


def test_clear_resets_pending():
    seq = AnnotatedFrameSequencer(enabled=True)
    seq.hold(1, 0.1, img())
    assert seq.has_pending
    seq.clear()
    assert not seq.has_pending


def test_held_frames_exposes_pixels():
    seq = AnnotatedFrameSequencer(enabled=True)
    image = np.ones((4, 4, 3), np.uint8)
    seq.hold(3, 0.3, image)
    held = seq.held_frames()
    assert held[0][0] == 3 and held[0][1] == 0.3
    assert held[0][2].shape == (4, 4, 3)


def test_begin_measurement_records_and_updates_previous():
    """A second measurement re-anchors the interpolation's previous side."""
    seq = AnnotatedFrameSequencer(enabled=True)
    seq.begin_measurement(0.0, pose(0, 0), None)
    seq.begin_measurement(1.0, pose(100, 100), None)
    seq.hold(2, 1.5, img())
    # Only the most recent measurement matters as the "previous" side.
    assert seq.drain(pose(200, 200), None, 2.0)[0][3][0].x == pytest.approx(150)
