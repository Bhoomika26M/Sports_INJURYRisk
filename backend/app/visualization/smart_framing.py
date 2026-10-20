"""Athlete-following ("smart crop") framing for the annotated output.

Why
---
The annotated video previously rendered the *entire* camera frame. When the
athlete is small in frame, far away, or off to one side, the skeleton overlay is
technically correct but hard to read - the person occupies a small part of the
view. This module computes a moving, aspect-correct crop window that keeps the
athlete framed and fully visible.

Design
------
* **Aspect preservation.** The crop window matches the output aspect ratio, so
  the final resize never distorts the body. The window is grown to cover the
  requested padding *and* satisfy the aspect ratio, never shrunk below it.
* **Full-body guarantee.** Padding is applied generously around the detected
  bounding box (which covers the person), so head and feet stay inside. The
  window is also clamped to the source frame.
* **Temporal smoothing.** Tracking boxes jitter frame to frame. A raw crop would
  visibly shake, which is worse than no crop at all. `SmoothFramer` applies an
  exponential moving average to the window, with a snap-through for large jumps
  (e.g. a cut or a genuine fast movement) so it does not lag behind reality.
* **Degenerate-input safety.** A missing/zero-size box, or a frame too small to
  crop, returns the full frame unchanged rather than raising.

Everything here is pure geometry on arrays - no model inference - so it adds
negligible cost compared to the pose pipeline.
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np

BBox = Tuple[float, float, float, float]
Size = Tuple[int, int]  # (width, height)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def compute_crop_window(
    bbox: Optional[BBox],
    frame_size: Size,
    out_size: Size,
    padding: float = 0.55,
    min_scale: float = 0.35,
) -> Tuple[int, int, int, int]:
    """Compute an aspect-correct crop window (x, y, w, h) around ``bbox``.

    Args:
        bbox: Detected athlete box ``(x1, y1, x2, y2)`` in source pixels. When
            None the whole frame is returned.
        frame_size: Source frame ``(width, height)``.
        out_size: Output frame ``(width, height)``; defines the target aspect.
        padding: Fractional padding added around the box. 0.55 keeps a good
            margin of context while still zooming in meaningfully.
        min_scale: Smallest allowed crop as a fraction of the frame's smaller
            dimension. Prevents an absurdly tight crop when the detector returns
            a tiny box (e.g. a mis-detection), which would upscale into mush.

    Returns:
        ``(x, y, w, h)`` integer crop window fully inside the source frame.
    """
    frame_w, frame_h = int(frame_size[0]), int(frame_size[1])
    out_w, out_h = (out_size if out_size and out_size[0] and out_size[1] else frame_size)
    out_w, out_h = int(out_w), int(out_h)

    if frame_w <= 0 or frame_h <= 0:
        return (0, 0, max(frame_w, 0), max(frame_h, 0))

    # Nothing to follow: keep the whole frame (a plain resize handles aspect).
    if bbox is None:
        return (0, 0, frame_w, frame_h)

    x1, y1, x2, y2 = (float(v) for v in bbox)
    box_w = max(1.0, x2 - x1)
    box_h = max(1.0, y2 - y1)

    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0

    # Grow the box by the requested padding.
    target_w = box_w * (1.0 + 2.0 * padding)
    target_h = box_h * (1.0 + 2.0 * padding)

    # Enforce the output aspect ratio by growing the smaller dimension.
    # Growing (never shrinking) is what guarantees the athlete stays inside.
    target_aspect = out_w / out_h if out_h else 1.0
    if target_w / target_h < target_aspect:
        target_w = target_h * target_aspect
    else:
        target_h = target_w / target_aspect

    # Don't zoom in beyond a sensible floor (guards tiny false detections).
    # The floor applies to the window's SMALLER side: enforcing the aspect
    # ratio above can already have grown the other side, so testing both
    # dimensions would let a 2px detection slip through.
    min_dim = min(frame_w, frame_h) * _clamp(min_scale, 0.05, 1.0)
    if min(target_w, target_h) < min_dim:
        scale = min_dim / max(min(target_w, target_h), 1e-6)
        target_w *= scale
        target_h *= scale

    # Never exceed the source frame; keep the target aspect after clamping.
    if target_w > frame_w or target_h > frame_h:
        fit = min(frame_w / target_w, frame_h / target_h)
        target_w *= fit
        target_h *= fit

    crop_w = int(round(target_w))
    crop_h = int(round(target_h))
    crop_w = int(_clamp(crop_w, 1, frame_w))
    crop_h = int(_clamp(crop_h, 1, frame_h))

    # Centre on the athlete, then clamp inside the frame.
    x = int(round(cx - crop_w / 2.0))
    y = int(round(cy - crop_h / 2.0))
    x = int(_clamp(x, 0, frame_w - crop_w))
    y = int(_clamp(y, 0, frame_h - crop_h))

    return (x, y, crop_w, crop_h)


class SmoothFramer:
    """Temporally smoothed crop window, to stop the output shaking.

    An exponential moving average is applied to the window's position and size.
    When the target window moves further than ``snap_threshold`` (a fraction of
    the frame) the filter jumps straight to the new window instead of easing -
    that is a cut or a real fast movement, and lagging behind it would look far
    worse than a jump.
    """

    def __init__(
        self,
        alpha: float = 0.25,
        snap_threshold: float = 0.35,
        padding: float = 0.55,
        min_scale: float = 0.35,
    ):
        self.alpha = _clamp(alpha, 0.01, 1.0)
        self.snap_threshold = snap_threshold
        self.padding = padding
        self.min_scale = min_scale
        self._state: Optional[Tuple[float, float, float, float]] = None

    def reset(self) -> None:
        self._state = None

    def window(
        self, bbox: Optional[BBox], frame_size: Size, out_size: Size
    ) -> Tuple[int, int, int, int]:
        """Return the (smoothed) crop window for this frame."""
        target = compute_crop_window(
            bbox, frame_size, out_size, self.padding, self.min_scale
        )

        # First frame, or following was lost: adopt the target directly.
        if self._state is None or bbox is None:
            self._state = tuple(float(v) for v in target)
            return target

        px, py, pw, ph = self._state
        tx, ty, tw, th = (float(v) for v in target)

        # Snap on a large move rather than easing through it.
        frame_diag = max(frame_size[0], frame_size[1])
        movement = max(abs(tx - px), abs(ty - py))
        if frame_diag > 0 and movement / frame_diag > self.snap_threshold:
            self._state = (tx, ty, tw, th)
            return target

        a = self.alpha
        nx = px + a * (tx - px)
        ny = py + a * (ty - py)
        nw = pw + a * (tw - pw)
        nh = ph + a * (th - ph)
        self._state = (nx, ny, nw, nh)

        # Re-clamp after smoothing so the window stays valid.
        fw, fh = int(frame_size[0]), int(frame_size[1])
        w = int(_clamp(round(nw), 1, fw))
        h = int(_clamp(round(nh), 1, fh))
        x = int(_clamp(round(nx), 0, fw - w))
        y = int(_clamp(round(ny), 0, fh - h))
        return (x, y, w, h)


def apply_crop(frame: np.ndarray, window: Tuple[int, int, int, int]) -> np.ndarray:
    """Crop ``frame`` to ``window``, returning the frame when it is degenerate."""
    if frame is None:
        return frame
    x, y, w, h = window
    if w <= 0 or h <= 0:
        return frame
    fh, fw = frame.shape[:2]
    if x >= fw or y >= fh:
        return frame
    return frame[y : min(y + h, fh), x : min(x + w, fw)]
