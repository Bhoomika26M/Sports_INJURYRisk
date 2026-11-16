"""Interpolate pose and bounding box across a gap between measured frames.

Why this exists
---------------
Analysis measures pose at ``POSE_FPS`` because measuring every frame is pure
cost. The annotated video, however, should play at the source frame rate so
fast movement flows instead of stepping.

This module supplies the *pose* for the frames in between. The frames
themselves are already in hand during the single analysis pass (which walks
every source frame), so no second decode of the video is needed - the analysis
loop simply renders the in-between frames with an interpolated pose and skips
the detector/pose model on them.

Interpolation is linear. The measured poses are already temporally smoothed
(``TemporalSmoother``), so a spline would add ringing without adding truth;
between two samples ~1/15s apart a straight line is indistinguishable from the
real motion.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from app.pose.estimator import Keypoint

BBox = Tuple[float, float, float, float]


def interpolate_keypoints(
    prev: List[Keypoint], nxt: List[Keypoint], t: float
) -> List[Keypoint]:
    """Linear blend of two poses. ``t`` is 0 (all ``prev``) to 1 (all ``nxt``).

    Confidence is never raised above the LESS certain neighbour: a frame
    synthesised between two uncertain detections is still uncertain, and
    presenting it as confident would inflate pose-quality statistics downstream.
    """
    if not prev:
        return list(nxt)
    if not nxt:
        return list(prev)
    if len(prev) != len(nxt):
        # Landmark sets disagree (one frame partially detected). Snapping is
        # safer than blending mismatched landmarks into nonsense geometry.
        return list(prev) if t < 0.5 else list(nxt)

    out: List[Keypoint] = []
    for p, n in zip(prev, nxt):
        conf = min(
            p.confidence + (n.confidence - p.confidence) * t,
            min(p.confidence, n.confidence),
        )
        out.append(
            Keypoint(
                x=p.x + (n.x - p.x) * t,
                y=p.y + (n.y - p.y) * t,
                confidence=conf,
                name=p.name,
            )
        )
    return out


def interpolate_bbox(
    prev: Optional[BBox], nxt: Optional[BBox], t: float
) -> Optional[BBox]:
    """Linear blend of two bounding boxes (used for the follow-crop)."""
    if prev is None:
        return nxt
    if nxt is None:
        return prev
    return tuple(prev[i] + (nxt[i] - prev[i]) * t for i in range(4))


def fraction_between(t0: float, t1: float, t: float) -> float:
    """Position of ``t`` within ``[t0, t1]``, clamped to 0..1."""
    span = t1 - t0
    if span <= 0:
        return 0.0
    return max(0.0, min(1.0, (t - t0) / span))
