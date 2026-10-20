"""Pose estimation: MediaPipe Pose, with an optional YOLOv8 person-crop step.

Heavy dependencies (mediapipe, ultralytics) are imported lazily so the rest of
the application and the unit tests run without them.
"""

import logging
from dataclasses import dataclass

import numpy as np

from app.core.config import settings
from app.services.video_processing import iter_frames

logger = logging.getLogger(__name__)

# The key body points required by the project spec, in a fixed order.
JOINT_NAMES = [
    "nose",  # head
    "left_shoulder", "right_shoulder",
    "left_elbow", "right_elbow",
    "left_wrist", "right_wrist",
    "left_hip", "right_hip",
    "left_knee", "right_knee",
    "left_ankle", "right_ankle",
    "left_foot", "right_foot",
]
JOINT_INDEX = {name: i for i, name in enumerate(JOINT_NAMES)}

# MediaPipe Pose landmark indices for each joint above
_MEDIAPIPE_LANDMARKS = {
    "nose": 0,
    "left_shoulder": 11, "right_shoulder": 12,
    "left_elbow": 13, "right_elbow": 14,
    "left_wrist": 15, "right_wrist": 16,
    "left_hip": 23, "right_hip": 24,
    "left_knee": 25, "right_knee": 26,
    "left_ankle": 27, "right_ankle": 28,
    "left_foot": 31, "right_foot": 32,  # foot index (toe)
}

# Skeleton edges used by the frontend overlay
SKELETON_EDGES = [
    ("left_shoulder", "right_shoulder"), ("left_hip", "right_hip"),
    ("left_shoulder", "left_hip"), ("right_shoulder", "right_hip"),
    ("left_shoulder", "left_elbow"), ("left_elbow", "left_wrist"),
    ("right_shoulder", "right_elbow"), ("right_elbow", "right_wrist"),
    ("left_hip", "left_knee"), ("left_knee", "left_ankle"), ("left_ankle", "left_foot"),
    ("right_hip", "right_knee"), ("right_knee", "right_ankle"), ("right_ankle", "right_foot"),
    ("nose", "left_shoulder"), ("nose", "right_shoulder"),
]


@dataclass
class PoseSequence:
    fps: float  # effective fps after frame striding
    positions: np.ndarray  # (T, J, 2) normalised image coords, y grows downward; NaN if unseen
    visibility: np.ndarray  # (T, J)
    frame_indices: list[int]
    detection_rate: float  # share of frames with a detected person

    def to_payload(self) -> dict:
        """Compact JSON-serialisable form for storage and the skeleton overlay."""
        frames = []
        for t in range(self.positions.shape[0]):
            frames.append(
                [
                    [None if np.isnan(v) else round(float(v), 4) for v in self.positions[t, j]]
                    for j in range(self.positions.shape[1])
                ]
            )
        return {
            "fps": self.fps,
            "joint_names": JOINT_NAMES,
            "edges": SKELETON_EDGES,
            "frame_indices": self.frame_indices,
            "frames": frames,
        }


class PersonDetector:
    """Optional YOLOv8 detector that crops the largest person for MediaPipe.

    Useful on wide gym/field shots where the athlete is small in frame. For
    several people in shot, the largest box is used (the athlete is assumed to
    be the primary subject). Full multi-person tracking would need DeepSORT.
    """

    def __init__(self) -> None:
        from ultralytics import YOLO  # lazy import

        self.model = YOLO(settings.YOLO_WEIGHTS)

    def largest_person_box(self, frame: np.ndarray) -> tuple[int, int, int, int] | None:
        results = self.model(frame, classes=[0], verbose=False)
        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            return None
        xyxy = boxes.xyxy.cpu().numpy()
        areas = (xyxy[:, 2] - xyxy[:, 0]) * (xyxy[:, 3] - xyxy[:, 1])
        x0, y0, x1, y1 = xyxy[int(np.argmax(areas))]
        return int(x0), int(y0), int(x1), int(y1)


def ensure_pose_model() -> str:
    """Return the path of the MediaPipe pose model, downloading it on first use."""
    import urllib.request
    from pathlib import Path

    path = Path(settings.POSE_MODEL_PATH)
    if path.exists() and path.stat().st_size > 1_000_000:
        return str(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading pose model to %s", path)
    tmp = path.with_suffix(".part")
    try:
        urllib.request.urlretrieve(settings.POSE_MODEL_URL, tmp)
        tmp.replace(path)
    except Exception as exc:  # noqa: BLE001
        tmp.unlink(missing_ok=True)
        raise RuntimeError(
            "Could not download the pose model (check your internet connection). "
            f"Download it manually from {settings.POSE_MODEL_URL} and save it as {path.resolve()}"
        ) from exc
    return str(path)


class _TasksBackend:
    """MediaPipe Tasks PoseLandmarker (current MediaPipe releases)."""

    def __init__(self, mp) -> None:
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision

        self._mp = mp
        options = vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=ensure_pose_model()),
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._landmarker = vision.PoseLandmarker.create_from_options(options)
        self._last_ts = -1

    def detect(self, rgb: np.ndarray, timestamp_ms: int):
        ts = max(timestamp_ms, self._last_ts + 1)  # must strictly increase
        self._last_ts = ts
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        result = self._landmarker.detect_for_video(image, ts)
        if not result.pose_landmarks:
            return None
        return [(p.x, p.y, p.visibility if p.visibility is not None else 0.0) for p in result.pose_landmarks[0]]

    def close(self) -> None:
        self._landmarker.close()


class _LegacyBackend:
    """mp.solutions.pose (MediaPipe 0.10.21 and older)."""

    def __init__(self, mp) -> None:
        self._pose = mp.solutions.pose.Pose(
            static_image_mode=False,
            model_complexity=settings.POSE_MODEL_COMPLEXITY,
            smooth_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    def detect(self, rgb: np.ndarray, timestamp_ms: int):
        result = self._pose.process(rgb)
        if not result.pose_landmarks:
            return None
        return [(p.x, p.y, p.visibility) for p in result.pose_landmarks.landmark]

    def close(self) -> None:
        self._pose.close()


class PoseEstimator:
    def __init__(self) -> None:
        try:
            import mediapipe as mp
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "mediapipe is not installed. Run `pip install mediapipe` to enable pose estimation."
            ) from exc
        self._mp = mp
        self._detector = PersonDetector() if settings.USE_YOLO_PERSON_DETECTOR else None

    def _make_backend(self):
        if hasattr(self._mp, "solutions"):
            return _LegacyBackend(self._mp)
        return _TasksBackend(self._mp)

    def process_video(self, path: str, enhance: bool = True) -> PoseSequence:
        import cv2

        cap = cv2.VideoCapture(path)
        native_fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
        cap.release()
        stride = max(settings.POSE_FRAME_STRIDE, 1)

        positions, visibility, indices = [], [], []
        detected = 0
        backend = self._make_backend()
        try:
            for idx, frame in iter_frames(path, stride=stride, enhance=enhance):
                h, w = frame.shape[:2]
                x0, y0, cw, ch = 0, 0, w, h
                crop = frame
                if self._detector is not None:
                    box = self._detector.largest_person_box(frame)
                    if box is not None:
                        pad_x, pad_y = int(0.1 * (box[2] - box[0])), int(0.1 * (box[3] - box[1]))
                        x0, y0 = max(box[0] - pad_x, 0), max(box[1] - pad_y, 0)
                        x1, y1 = min(box[2] + pad_x, w), min(box[3] + pad_y, h)
                        crop = frame[y0:y1, x0:x1]
                        cw, ch = x1 - x0, y1 - y0

                rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
                landmarks = backend.detect(rgb, int(idx / native_fps * 1000))
                pos = np.full((len(JOINT_NAMES), 2), np.nan)
                vis = np.zeros(len(JOINT_NAMES))
                if landmarks:
                    detected += 1
                    for name, j in JOINT_INDEX.items():
                        x, y, v = landmarks[_MEDIAPIPE_LANDMARKS[name]]
                        vis[j] = v
                        if v >= settings.MIN_KEYPOINT_VISIBILITY:
                            # map crop-normalised coords back to full-frame normalised coords
                            pos[j] = ((x * cw + x0) / w, (y * ch + y0) / h)
                positions.append(pos)
                visibility.append(vis)
                indices.append(idx)
        finally:
            backend.close()

        if not positions:
            raise ValueError("No frames could be read from the video.")
        return PoseSequence(
            fps=native_fps / stride,
            positions=np.stack(positions),
            visibility=np.stack(visibility),
            frame_indices=indices,
            detection_rate=detected / len(positions),
        )
