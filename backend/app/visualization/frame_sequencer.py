"""Sequences annotated-video frames at the source rate from sampled poses.

Why this exists
---------------
The analysis loop walks every source frame but only measures pose on the
sampled ones (``POSE_FPS``). To write the annotated video at the *source* rate
without a second decode of the file, the in-between frames are rendered during
that same pass using an interpolated pose.

An in-between frame cannot be drawn until the NEXT measured pose is known -
interpolation needs both sides of the gap. This helper holds those frames until
the next measurement arrives, then releases them in strict source order. It
owns that ordering concern so the analysis loop stays readable.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np

from app.pose.estimator import Keypoint
from app.visualization.interpolation import (
    BBox,
    fraction_between,
    interpolate_bbox,
    interpolate_keypoints,
)

# A held frame: (frame_index, timestamp, image)
HeldFrame = Tuple[int, float, np.ndarray]


class AnnotatedFrameSequencer:
    """Collects measured + unmeasured frames and hands them back for rendering.

    Usage, per analysis chunk::

        seq.begin_measurement(timestamp, pose, bbox)   # a measured frame
        seq.hold(frame_index, timestamp, frame)        # an unmeasured frame
        ...
        for idx, ts, frame, pose, bbox in seq.drain(next_pose, next_bbox, next_ts):
            render(frame, pose, bbox)
    """

    def __init__(self, enabled: bool):
        self.enabled = enabled
        # Most recent MEASURED pose/bbox/time - the "previous" side of a gap.
        self._prev_pose: List[Keypoint] = []
        self._prev_bbox: Optional[BBox] = None
        self._prev_time: Optional[float] = None
        # Frames held since the last measurement.
        self._held: List[HeldFrame] = []

    # -- measured frames --------------------------------------------------- #

    def begin_measurement(
        self,
        timestamp: float,
        pose: Optional[List[Keypoint]],
        bbox: Optional[BBox],
    ) -> None:
        """Register the pose measured for the frame just processed."""
        self._prev_pose = list(pose) if pose else []
        self._prev_bbox = bbox
        self._prev_time = timestamp

    # -- unmeasured frames ------------------------------------------------- #

    def hold(self, frame_index: int, timestamp: float, frame: np.ndarray) -> None:
        """Hold an unmeasured frame until the next measurement is known."""
        if not self.enabled:
            return
        self._held.append((frame_index, timestamp, frame))

    # -- release ----------------------------------------------------------- #

    def held_frames(self) -> List[HeldFrame]:
        return list(self._held)

    def clear(self) -> None:
        self._held.clear()

    @property
    def has_pending(self) -> bool:
        return bool(self._held)

    def drain(
        self,
        next_pose: Optional[List[Keypoint]],
        next_bbox: Optional[BBox],
        next_timestamp: Optional[float],
    ) -> List[Tuple[int, float, np.ndarray, List[Keypoint], Optional[BBox]]]:
        """Return held frames WITH their pixels, then clear them.

        Each entry is ``(frame_index, timestamp, frame, pose, bbox)``, in source
        order. The pose is interpolated toward the given next measurement (or
        held from the previous one when there is no next).
        """
        out: List[Tuple[int, float, np.ndarray, List[Keypoint], Optional[BBox]]] = []
        for frame_index, timestamp, frame in self._held:
            if next_timestamp is not None and self._prev_time is not None:
                t = fraction_between(self._prev_time, next_timestamp, timestamp)
            else:
                t = 0.0
            pose = interpolate_keypoints(self._prev_pose, next_pose or [], t)
            bbox = interpolate_bbox(self._prev_bbox, next_bbox, t)
            out.append((frame_index, timestamp, frame, pose, bbox))
        self._held.clear()
        return out
