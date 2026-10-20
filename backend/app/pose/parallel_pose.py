"""Parallel pose estimation across multiple MediaPipe instances.

The video is still decoded and tracked sequentially (ByteTrack needs frame
continuity), but the cropped ROI frames of each chunk are estimated by several
MediaPipe instances running in parallel threads.

To preserve MediaPipe's temporal tracking quality, the chunk is split into
contiguous slices — each instance sees temporally adjacent frames, and slices
run in parallel across threads.
"""

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from math import ceil
from typing import List, Tuple

import numpy as np

from app.core.config import settings
from app.pose.estimator import Keypoint
from app.pose.mediapipe_pose import MediaPipeBlazePoseEstimator


class ParallelPosePool:
    """Estimates poses for (roi_frame, timestamp) items using N instances."""

    def __init__(self, workers: int = 0):
        if workers <= 0:
            workers = settings.POSE_WORKERS or min(4, os.cpu_count() or 1)
        self.workers = max(1, int(workers))
        self._local = threading.local()
        self._executor = (
            ThreadPoolExecutor(max_workers=self.workers, thread_name_prefix="pose-worker")
            if self.workers > 1
            else None
        )

    def _estimator(self) -> MediaPipeBlazePoseEstimator:
        """One persistent estimator per worker thread."""
        est = getattr(self._local, "estimator", None)
        if est is None:
            est = MediaPipeBlazePoseEstimator(
                model_complexity=settings.POSE_MODEL_COMPLEXITY
            )
            self._local.estimator = est
        return est

    def estimate(self, items: List[Tuple[np.ndarray, float]]) -> List[List[Keypoint]]:
        """
        Estimate poses for a chunk of ROI frames.

        Args:
            items: list of (roi_frame, timestamp_seconds), in frame order

        Returns:
            Keypoint lists aligned with the input order
        """
        if not items:
            return []

        if self._executor is None or len(items) == 1:
            return self._run_slice(items)

        # Balanced contiguous slices: one per worker
        workers = min(self.workers, len(items))
        per_slice = ceil(len(items) / workers)
        slices = [
            items[i:i + per_slice] for i in range(0, len(items), per_slice)
        ]

        futures = [self._executor.submit(self._run_slice, sl) for sl in slices]
        results: List[List[Keypoint]] = []
        for fut in futures:
            results.extend(fut.result())
        return results

    def _run_slice(self, items: List[Tuple[np.ndarray, float]]) -> List[List[Keypoint]]:
        est = self._estimator()
        out: List[List[Keypoint]] = []
        for frame, ts in items:
            # Strictly increasing integer timestamps required by MediaPipe
            # Tasks API video mode
            est._timestamp_ms = int(max(est._timestamp_ms + 1, ts * 1000))
            out.append(est.estimate(frame))
        return out

    def shutdown(self) -> None:
        if self._executor is not None:
            self._executor.shutdown(wait=True)

    def __enter__(self) -> "ParallelPosePool":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.shutdown()
