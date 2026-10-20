import cv2
import numpy as np
import os
import threading
from pathlib import Path
from typing import List, Optional
from app.pose.estimator import PoseEstimator, Keypoint
from app.core.config import settings
import mediapipe as mp

# Official MediaPipe pose-landmarker task bundles (used by the Tasks API,
# which is the only pose API available in mediapipe >= 0.10.15 / 1.x)
POSE_MODEL_URLS = {
    0: "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
       "pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
    1: "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
       "pose_landmarker_full/float16/1/pose_landmarker_full.task",
    2: "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
       "pose_landmarker_heavy/float16/1/pose_landmarker_heavy.task",
}
POSE_MODEL_FILES = {0: "pose_landmarker_lite.task", 1: "pose_landmarker_full.task", 2: "pose_landmarker_heavy.task"}

# Serializes model downloads so parallel pose workers cannot race on the file
_MODEL_LOCK = threading.Lock()


def ensure_pose_model_available(model_complexity: int = 1) -> Path:
    """
    Return the path to the pose .task bundle, downloading it once if missing.

    mediapipe 0.10.15+ / 1.x removed the legacy mp.solutions API, so the Tasks
    API requires an explicit model file. The download is lock-guarded because
    the parallel pose workers each build their own estimator.
    """
    complexity = model_complexity if model_complexity in POSE_MODEL_FILES else 1
    model_dir = Path(settings.POSE_MODEL_DIR)
    if not model_dir.is_absolute():
        # backend/ directory = three levels up from app/pose/<this file>
        model_dir = Path(__file__).resolve().parents[2] / model_dir
    model_dir.mkdir(parents=True, exist_ok=True)

    model_path = model_dir / POSE_MODEL_FILES[complexity]
    if model_path.exists():
        return model_path

    with _MODEL_LOCK:
        if model_path.exists():  # another worker finished first
            return model_path

        url = POSE_MODEL_URLS[complexity]
        print(f"Downloading MediaPipe pose model -> {model_path}")
        import tempfile
        import urllib.request
        try:
            fd, tmp_name = tempfile.mkstemp(dir=str(model_dir), suffix=".task.part")
            os.close(fd)
            urllib.request.urlretrieve(url, tmp_name)
            os.replace(tmp_name, model_path)
        except Exception as e:
            raise RuntimeError(
                f"Could not download MediaPipe pose model from {url}: {e}. "
                f"Download it manually and place it at {model_path}"
            )
    return model_path


class MediaPipeBlazePoseEstimator(PoseEstimator):
    """
    MediaPipe BlazePose estimator.
    
    Using MediaPipe BlazePose instead of MoveNet Lightning due to TensorFlow
    compatibility issues with Python 3.12.
    
    BlazePose provides 33 keypoints (vs MoveNet's 17) and is production-grade.
    """
    
    # MediaPipe BlazePose keypoint names (33 keypoints)
    KEYPOINT_NAMES = [
        "nose",
        "left_eye_inner", "left_eye", "left_eye_outer",
        "right_eye_inner", "right_eye", "right_eye_outer",
        "left_ear", "right_ear",
        "mouth_left", "mouth_right",
        "left_shoulder", "right_shoulder",
        "left_elbow", "right_elbow",
        "left_wrist", "right_wrist",
        "left_pinky", "right_pinky",
        "left_index", "right_index",
        "left_thumb", "right_thumb",
        "left_hip", "right_hip",
        "left_knee", "right_knee",
        "left_ankle", "right_ankle",
        "left_heel", "right_heel",
        "left_foot_index", "right_foot_index"
    ]
    
    def __init__(self, model_complexity: int = 1, min_detection_confidence: float = 0.5):
        """
        Initialize MediaPipe BlazePose estimator.

        Args:
            model_complexity: 0 for lite, 1 for full, 2 for heavier
            min_detection_confidence: Minimum confidence for detection
        """
        self.model_complexity = model_complexity
        self.min_detection_confidence = min_detection_confidence
        self.pose = None
        self.api = None  # "solutions" (legacy) or "tasks" (mediapipe 1.x)
        self._timestamp_ms = 0  # Timestamp counter for video mode
        self._last_used_ms = -1  # Guards monotonicity required by Tasks API
        self._load_model()
    
    def _resolve_model_path(self) -> Path:
        """Locate (and if needed download) the Tasks API .task bundle."""
        return ensure_pose_model_available(self.model_complexity)

    def _load_model(self):
        """Load MediaPipe BlazePose model (legacy API or Tasks API)."""
        try:
            # Try old API first (mp.solutions.pose) — mediapipe <= 0.10.14
            if hasattr(mp, 'solutions') and hasattr(mp.solutions, 'pose'):
                self.pose = mp.solutions.pose.Pose(
                    static_image_mode=False,
                    model_complexity=self.model_complexity,
                    smooth_landmarks=True,
                    enable_segmentation=False,
                    smooth_segmentation=False,
                    min_detection_confidence=self.min_detection_confidence,
                    min_tracking_confidence=self.min_detection_confidence
                )
                self.api = "solutions"
                print("MediaPipe BlazePose model loaded successfully (legacy solutions API)")
                return

            # Tasks API (mediapipe >= 0.10.15 / 1.x) — requires a .task bundle
            BaseOptions = mp.tasks.BaseOptions
            PoseLandmarker = mp.tasks.vision.PoseLandmarker
            PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
            RunningMode = mp.tasks.vision.RunningMode

            model_path = self._resolve_model_path()
            options = PoseLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=str(model_path)),
                running_mode=RunningMode.VIDEO,
                num_poses=1,
                min_pose_detection_confidence=self.min_detection_confidence,
                min_pose_presence_confidence=self.min_detection_confidence,
                min_tracking_confidence=self.min_detection_confidence,
                output_segmentation_masks=False
            )

            self.pose = PoseLandmarker.create_from_options(options)
            self.api = "tasks"
            print(f"MediaPipe BlazePose model loaded successfully (Tasks API: {model_path.name})")
        except Exception as e:
            print(f"Failed to load MediaPipe BlazePose: {e}")
            self.pose = None
    
    def estimate(self, frame: np.ndarray) -> List[Keypoint]:
        """
        Estimate pose from a single frame.

        Args:
            frame: Input image (numpy array, BGR format)

        Returns:
            List of Keypoint objects (33 keypoints for BlazePose)
        """
        if self.pose is None:
            raise RuntimeError("MediaPipe BlazePose model not loaded")

        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Check which API is being used
        if hasattr(self.pose, 'process'):
            # Old API (mp.solutions.pose)
            results = self.pose.process(frame_rgb)

            if results.pose_landmarks is None:
                return []

            landmarks = results.pose_landmarks.landmark
            height, width = frame.shape[:2]

            keypoints = []
            for idx, landmark in enumerate(landmarks):
                if idx < len(self.KEYPOINT_NAMES):
                    x = landmark.x * width
                    y = landmark.y * height
                    confidence = landmark.visibility

                    keypoint = Keypoint(
                        x=float(x),
                        y=float(y),
                        confidence=float(confidence),
                        name=self.KEYPOINT_NAMES[idx]
                    )
                    keypoints.append(keypoint)

            return keypoints
        else:
            # Tasks API (mediapipe >= 0.10.15 / 1.x)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            # Tasks API requires strictly increasing integer timestamps per
            # instance. Callers (sequential loop / parallel pool) may set
            # _timestamp_ms from the real frame time; guarantee monotonic
            # integer values here anyway.
            self._timestamp_ms = int(max(self._timestamp_ms, self._last_used_ms + 1))
            self._last_used_ms = self._timestamp_ms
            results = self.pose.detect_for_video(mp_image, self._timestamp_ms)

            if results.pose_landmarks is None or len(results.pose_landmarks) == 0:
                return []

            landmarks = results.pose_landmarks[0]
            height, width = frame.shape[:2]

            keypoints = []
            for idx, landmark in enumerate(landmarks):
                if idx < len(self.KEYPOINT_NAMES):
                    x = landmark.x * width
                    y = landmark.y * height
                    # visibility = how much of the joint is in view (what the
                    # risk engine wants); presence = likelihood it exists at all
                    confidence = getattr(landmark, "visibility", None)
                    if confidence is None:
                        confidence = getattr(landmark, "presence", 0.0)

                    keypoint = Keypoint(
                        x=float(x),
                        y=float(y),
                        confidence=float(confidence),
                        name=self.KEYPOINT_NAMES[idx]
                    )
                    keypoints.append(keypoint)

            return keypoints
    
    def get_model_name(self) -> str:
        return "MediaPipe BlazePose"
    
    def get_model_version(self) -> str:
        return f"complexity_{self.model_complexity}"
    
    def get_input_size(self) -> tuple:
        return (None, None)  # MediaPipe handles resizing internally
    
    def preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Preprocess frame for MediaPipe.
        
        MediaPipe expects RGB format.
        
        Args:
            frame: Input frame (BGR format from OpenCV)
        
        Returns:
            Preprocessed frame (RGB format)
        """
        # Convert BGR to RGB
        if frame.shape[2] == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        return frame
