import os
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from typing import List, Dict, Any, Optional

# MediaPipe 33 Landmark Constants
LANDMARK_NAMES = {
    0: "nose",
    11: "left_shoulder", 12: "right_shoulder",
    13: "left_elbow", 14: "right_elbow",
    15: "left_wrist", 16: "right_wrist",
    23: "left_hip", 24: "right_hip",
    25: "left_knee", 26: "right_knee",
    27: "left_ankle", 28: "right_ankle",
    29: "left_heel", 30: "right_heel",
    31: "left_foot_index", 32: "right_foot_index"
}

class PoseEstimator:
    """
    Core Pose Estimation Engine utilizing MediaPipe Tasks API.
    Extracts 33 3D body keypoints for sports kinematic analysis.
    """
    def __init__(self, model_path: Optional[str] = None):
        if model_path is None:
            # Check root models/ or backend models/
            cur_dir = os.path.abspath(os.path.dirname(__file__))
            candidates = [
                os.path.join(cur_dir, "..", "..", "..", "models", "pose_landmarker_lite.task"),
                os.path.join(cur_dir, "..", "..", "models", "pose_landmarker_lite.task"),
                os.path.join(os.getcwd(), "models", "pose_landmarker_lite.task"),
                os.path.join(os.getcwd(), "..", "models", "pose_landmarker_lite.task")
            ]
            for candidate in candidates:
                if os.path.exists(candidate):
                    model_path = os.path.abspath(candidate)
                    break
        
        if model_path is None or not os.path.exists(model_path):
            target_dir = os.path.abspath(os.path.join(cur_dir, "..", "..", "..", "models"))
            os.makedirs(target_dir, exist_ok=True)
            model_path = os.path.join(target_dir, "pose_landmarker_lite.task")
            if not os.path.exists(model_path):
                import urllib.request
                url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
                urllib.request.urlretrieve(url, model_path)
        
        self.model_path = model_path
        base_options = python.BaseOptions(model_asset_path=self.model_path)
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            output_segmentation_masks=False,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.detector = vision.PoseLandmarker.create_from_options(options)

    def extract_landmarks(self, frame_bgr: np.ndarray) -> Optional[List[Dict[str, float]]]:
        """
        Process a single BGR frame and return list of 33 landmarks.
        """
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        
        detection_result = self.detector.detect(mp_image)
        
        if not detection_result.pose_landmarks or len(detection_result.pose_landmarks) == 0:
            return None
        
        first_pose = detection_result.pose_landmarks[0]
        landmarks = []
        for idx, lm in enumerate(first_pose):
            landmarks.append({
                "id": idx,
                "name": LANDMARK_NAMES.get(idx, f"point_{idx}"),
                "x": float(lm.x),
                "y": float(lm.y),
                "z": float(lm.z),
                "visibility": float(lm.visibility) if hasattr(lm, "visibility") else 1.0
            })
        return landmarks

    def process_video(
        self, 
        video_path: str, 
        max_frames: int = 180, 
        stride: int = 2
    ) -> Dict[str, Any]:
        """
        Extract pose landmarks across frames of a video file.
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        frames_data = []
        frame_idx = 0
        processed_count = 0

        while cap.isOpened() and processed_count < max_frames:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % stride == 0:
                timestamp = round(frame_idx / fps, 3)
                landmarks = self.extract_landmarks(frame)
                
                frames_data.append({
                    "frame_index": frame_idx,
                    "timestamp": timestamp,
                    "detected": landmarks is not None,
                    "landmarks": landmarks
                })
                processed_count += 1

            frame_idx += 1

        cap.release()

        return {
            "fps": fps,
            "total_video_frames": total_video_frames,
            "processed_frames": len(frames_data),
            "width": width,
            "height": height,
            "duration": round(total_video_frames / fps, 2) if fps > 0 else 0,
            "frames": frames_data
        }

    def close(self):
        if hasattr(self, "detector") and self.detector:
            self.detector.close()
