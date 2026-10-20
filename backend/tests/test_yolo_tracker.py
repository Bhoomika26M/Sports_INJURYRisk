"""Tests for YOLOTracker's detection-cost controls and coordinate mapping.

These stub the Ultralytics model so no weights are loaded and no inference runs;
the point is to verify the *contract*: frames wider than DETECT_MAX_WIDTH are
downscaled before detection, and the returned boxes are mapped back to the
original frame's coordinate space.
"""

from types import SimpleNamespace

import numpy as np
import pytest

from app.tracking.yolo_tracker import YOLOTracker


class FakeBox:
    def __init__(self, xyxy, conf, cls, track_id):
        self.xyxy = np.array([xyxy], dtype=float)
        self.conf = np.array([conf], dtype=float)
        self.cls = np.array([cls], dtype=float)
        self.id = None if track_id is None else np.array([track_id], dtype=float)


class FakeResult:
    def __init__(self, boxes):
        self.boxes = boxes


class FakeModel:
    """Records the last call args and returns a fixed detection."""

    def __init__(self, boxes):
        self._boxes = boxes
        self.calls = []

    def track(self, frame, **kwargs):
        self.calls.append({"shape": frame.shape, "kwargs": kwargs})
        return [FakeResult(self._boxes)]


def _tracker(boxes, detect_max_width, imgsz=640):
    """Build a tracker with a stub model, bypassing _load_model."""
    t = YOLOTracker.__new__(YOLOTracker)
    t.model_name = "stub.pt"
    t.confidence_threshold = 0.5
    t.detect_max_width = detect_max_width
    t.imgsz = imgsz
    t.model = FakeModel(boxes)
    return t


# --------------------------------------------------------------------------- #
# Downscaling
# --------------------------------------------------------------------------- #

def test_wide_frame_is_downscaled_before_detection():
    t = _tracker([FakeBox([10, 20, 110, 220], 0.9, 0, 1)], detect_max_width=1280)
    frame = np.zeros((2160, 4096, 3), dtype=np.uint8)
    t.update(frame, 0, 0.0)

    shape = t.model.calls[0]["shape"]
    assert shape[1] == 1280
    # Aspect ratio preserved (allowing for rounding).
    assert shape[0] == pytest.approx(2160 * 1280 / 4096, abs=1)


def test_narrow_frame_is_not_resized():
    t = _tracker([FakeBox([10, 20, 110, 220], 0.9, 0, 1)], detect_max_width=1280)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    t.update(frame, 0, 0.0)
    assert t.model.calls[0]["shape"][1] == 640


def test_downscale_disabled_keeps_full_frame():
    t = _tracker([FakeBox([10, 20, 110, 220], 0.9, 0, 1)], detect_max_width=0)
    frame = np.zeros((2160, 4096, 3), dtype=np.uint8)
    t.update(frame, 0, 0.0)
    assert t.model.calls[0]["shape"][1] == 4096


# --------------------------------------------------------------------------- #
# Coordinate mapping
# --------------------------------------------------------------------------- #

def test_boxes_are_mapped_back_to_original_coordinates():
    """A box found in the downscaled frame must be scaled up by the inverse."""
    # 4096 -> 1280 is a scale of 0.3125, so inverse is 3.2.
    t = _tracker([FakeBox([100, 50, 200, 300], 0.9, 0, 7)], detect_max_width=1280)
    frame = np.zeros((2160, 4096, 3), dtype=np.uint8)

    objects = t.update(frame, 0, 0.0)
    assert len(objects) == 1
    x1, y1, x2, y2 = objects[0].bbox
    assert x1 == pytest.approx(320.0)
    assert y1 == pytest.approx(160.0)
    assert x2 == pytest.approx(640.0)
    assert y2 == pytest.approx(960.0)


def test_boxes_unchanged_when_no_downscale():
    t = _tracker([FakeBox([100, 50, 200, 300], 0.9, 0, 7)], detect_max_width=0)
    frame = np.zeros((2160, 4096, 3), dtype=np.uint8)
    objects = t.update(frame, 0, 0.0)
    assert objects[0].bbox == (100.0, 50.0, 200.0, 300.0)


# --------------------------------------------------------------------------- #
# Inference arguments
# --------------------------------------------------------------------------- #

def test_classes_filter_and_imgsz_are_passed():
    t = _tracker([], detect_max_width=1280, imgsz=512)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    t.update(frame, 0, 0.0)
    kwargs = t.model.calls[0]["kwargs"]
    assert kwargs["classes"] == [0]
    assert kwargs["imgsz"] == 512
    assert kwargs["persist"] is True


def test_person_class_kept_and_others_dropped():
    boxes = [
        FakeBox([0, 0, 10, 10], 0.9, 0, 1),   # person
        FakeBox([0, 0, 10, 10], 0.9, 2, 2),   # car - must be dropped
    ]
    t = _tracker(boxes, detect_max_width=0)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    objects = t.update(frame, 0, 0.0)
    assert [o.track_id for o in objects] == [1]


def test_low_confidence_detection_dropped():
    boxes = [FakeBox([0, 0, 10, 10], 0.2, 0, 1)]
    t = _tracker(boxes, detect_max_width=0)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    assert t.update(frame, 0, 0.0) == []


def test_missing_track_id_dropped():
    boxes = [FakeBox([0, 0, 10, 10], 0.9, 0, None)]
    t = _tracker(boxes, detect_max_width=0)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    assert t.update(frame, 0, 0.0) == []
