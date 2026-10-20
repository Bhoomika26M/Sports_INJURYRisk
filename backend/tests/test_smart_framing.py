"""Tests for athlete-following ("smart crop") annotated-output framing.

These are pure-geometry tests: no model inference, no video decoding.
"""

import numpy as np
import pytest

from app.visualization.smart_framing import (
    SmoothFramer,
    apply_crop,
    compute_crop_window,
)

FRAME = (1920, 1080)  # wide 16:9 source
OUT = (1280, 720)  # 16:9 output


# --------------------------------------------------------------------------- #
# Window geometry
# --------------------------------------------------------------------------- #

def test_no_bbox_returns_full_frame():
    win = compute_crop_window(None, FRAME, OUT)
    assert win == (0, 0, 1920, 1080)


def test_window_respects_output_aspect_ratio():
    """The crop must match the output aspect or the resize would distort."""
    win = compute_crop_window((800, 400, 1000, 900), FRAME, OUT)
    _, _, w, h = win
    assert w / h == pytest.approx(OUT[0] / OUT[1], rel=0.02)


def test_window_contains_the_athlete_with_padding():
    """The detected body must sit fully inside the crop."""
    bbox = (900, 300, 1100, 900)
    win = compute_crop_window(bbox, FRAME, OUT, padding=0.55)
    x, y, w, h = win
    x1, y1, x2, y2 = bbox
    assert x <= x1 and y <= y1
    assert x + w >= x2 and y + h >= y2


def test_window_is_inside_the_frame():
    for bbox in [(0, 0, 200, 400), (1800, 800, 1920, 1080), (500, 100, 900, 1000)]:
        x, y, w, h = compute_crop_window(bbox, FRAME, OUT)
        assert x >= 0 and y >= 0
        assert x + w <= FRAME[0]
        assert y + h <= FRAME[1]


def test_window_zooms_in_for_a_centred_small_person():
    """A small subject should yield a crop smaller than the full frame."""
    win = compute_crop_window((900, 450, 1000, 700), FRAME, OUT)
    _, _, w, h = win
    assert w < FRAME[0]
    assert h < FRAME[1]


def test_tiny_detection_does_not_overzoom():
    """A spurious 2px box must not upscale into mush."""
    win = compute_crop_window((500, 500, 502, 502), FRAME, OUT, min_scale=0.35)
    _, _, w, h = win
    # min_scale is relative to the frame's smaller side (1080).
    assert min(w, h) >= int(1080 * 0.35) - 2


def test_huge_bbox_clamped_to_frame():
    win = compute_crop_window((-500, -500, 5000, 5000), FRAME, OUT)
    x, y, w, h = win
    assert (x, y) == (0, 0)
    assert w <= FRAME[0] and h <= FRAME[1]


def test_zero_size_frame_is_safe():
    assert compute_crop_window((0, 0, 10, 10), (0, 0), OUT) == (0, 0, 0, 0)


def test_portrait_source_still_produces_valid_window():
    portrait = (720, 1280)
    x, y, w, h = compute_crop_window((300, 400, 420, 900), portrait, (640, 640))
    assert w > 0 and h > 0
    assert x + w <= portrait[0]
    assert y + h <= portrait[1]


# --------------------------------------------------------------------------- #
# Smoothing
# --------------------------------------------------------------------------- #

def test_first_window_is_adopted_directly():
    framer = SmoothFramer(alpha=0.25)
    win = framer.window((800, 300, 1000, 900), FRAME, OUT)
    assert win == compute_crop_window(
        (800, 300, 1000, 900), FRAME, OUT, framer.padding, framer.min_scale
    )


def test_smoothing_reduces_jitter():
    """A one-pixel wobble must not move the window a full pixel."""
    framer = SmoothFramer(alpha=0.25)
    framer.window((800, 300, 1000, 900), FRAME, OUT)
    before = framer.window((800, 300, 1000, 900), FRAME, OUT)
    after = framer.window((801, 300, 1001, 900), FRAME, OUT)
    # Smoothing keeps the change to at most the smoothed step, not the raw one.
    assert abs(after[0] - before[0]) <= 1


def test_large_jump_snaps_instead_of_lagging():
    """A cut / fast move should jump, not ease across the frame."""
    framer = SmoothFramer(alpha=0.10, snap_threshold=0.35)
    framer.window((100, 100, 300, 700), FRAME, OUT)
    # Move the athlete right across the frame.
    snapped = framer.window((1500, 100, 1700, 700), FRAME, OUT)
    expected = compute_crop_window(
        (1500, 100, 1700, 700), FRAME, OUT, framer.padding, framer.min_scale
    )
    assert snapped == expected


def test_missing_bbox_holds_window_and_resets_state():
    framer = SmoothFramer(alpha=0.25)
    framer.window((800, 300, 1000, 900), FRAME, OUT)
    held = framer.window(None, FRAME, OUT)
    # Holding = full frame (no target), and it must not crash.
    assert held == (0, 0, *FRAME)


def test_reset_clears_state():
    framer = SmoothFramer()
    framer.window((800, 300, 1000, 900), FRAME, OUT)
    framer.reset()
    assert framer._state is None


# --------------------------------------------------------------------------- #
# Apply
# --------------------------------------------------------------------------- #

def test_apply_crop_returns_correct_shape():
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    out = apply_crop(frame, (100, 50, 640, 360))
    assert out.shape == (360, 640, 3)


def test_apply_crop_degenerate_window_is_safe():
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    assert apply_crop(frame, (0, 0, 0, 0)).shape == (100, 100, 3)
    assert apply_crop(frame, (500, 500, 10, 10)).shape == (100, 100, 3)
