import os
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
from app.utils.math_helpers import (
    calculate_angle_2d,
    calculate_valgus_angle,
    calculate_trunk_lean,
    calculate_pelvic_tilt,
    calculate_bilateral_asymmetry
)

# Standard skeleton connection pairs
POSE_CONNECTIONS = [
    # Face & Torso
    (11, 12), # Left Shoulder - Right Shoulder
    (11, 23), # Left Shoulder - Left Hip
    (12, 24), # Right Shoulder - Right Hip
    (23, 24), # Left Hip - Right Hip
    # Left Arm
    (11, 13), # Left Shoulder - Left Elbow
    (13, 15), # Left Elbow - Left Wrist
    # Right Arm
    (12, 14), # Right Shoulder - Right Elbow
    (14, 16), # Right Elbow - Right Wrist
    # Left Leg
    (23, 25), # Left Hip - Left Knee
    (25, 27), # Left Knee - Left Ankle
    (27, 29), # Left Ankle - Left Heel
    (29, 31), # Left Heel - Left Foot Index
    (27, 31), # Left Ankle - Left Foot Index
    # Right Leg
    (24, 26), # Right Hip - Right Knee
    (26, 28), # Right Knee - Right Ankle
    (28, 30), # Right Ankle - Right Heel
    (30, 32), # Right Heel - Right Foot Index
    (28, 32)  # Right Ankle - Right Foot Index
]

MODEL_PATH = Path(__file__).resolve().parent.parent.parent / "models" / "pose_landmarker_full.task"

class PoseEstimationEngine:
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or str(MODEL_PATH)
        self.detector = None
        self._init_detector()

    def _init_detector(self):
        try:
            if os.path.exists(self.model_path):
                base_options = mp_python.BaseOptions(model_asset_path=self.model_path)
                options = vision.PoseLandmarkerOptions(
                    base_options=base_options,
                    running_mode=vision.RunningMode.IMAGE,
                    output_segmentation_masks=False,
                    min_pose_detection_confidence=0.5,
                    min_pose_presence_confidence=0.5,
                    min_tracking_confidence=0.5
                )
                self.detector = vision.PoseLandmarker.create_from_options(options)
            else:
                print(f"Warning: Model file not found at {self.model_path}")
        except Exception as e:
            print(f"Failed to initialize MediaPipe detector: {e}")
            self.detector = None

    def process_video(
        self,
        video_input_path: str,
        video_output_path: str,
        max_frames: int = 450
    ) -> Dict[str, Any]:
        """
        Process a video file, extract pose keypoints per frame, compute biomechanical angles,
        and write a video with skeleton and telemetry overlay.
        """
        cap = cv2.VideoCapture(video_input_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open input video: {video_input_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
        total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out_writer = cv2.VideoWriter(video_output_path, fourcc, fps, (width, height))

        frame_index = 0
        time_series = []
        
        while cap.isOpened() and frame_index < max_frames:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            timestamp_sec = round(frame_index / fps, 3)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

            landmarks = None
            if self.detector:
                try:
                    result = self.detector.detect(mp_image)
                    if result.pose_landmarks and len(result.pose_landmarks) > 0:
                        landmarks = result.pose_landmarks[0]
                except Exception as err:
                    pass

            # Extract biomechanical metrics for this frame
            frame_metrics = self._analyze_frame_landmarks(landmarks, width, height, frame_index, timestamp_sec)
            time_series.append(frame_metrics)

            # Draw skeleton overlay and HUD onto frame
            annotated_frame = self._render_overlay(frame, landmarks, frame_metrics, width, height, frame_index, fps)
            out_writer.write(annotated_frame)

            frame_index += 1

        cap.release()
        out_writer.release()

        return {
            "total_frames": frame_index,
            "fps": fps,
            "duration": round(frame_index / fps, 2),
            "width": width,
            "height": height,
            "time_series": time_series
        }

    def _analyze_frame_landmarks(
        self,
        landmarks: Optional[List[Any]],
        width: int,
        height: int,
        frame_idx: int,
        timestamp: float
    ) -> Dict[str, Any]:
        """
        Calculates joint angles and biomechanical metrics from frame keypoints.
        """
        # Default fallback values if athlete is momentarily occluded
        default_metrics = {
            "frame": frame_idx,
            "time": timestamp,
            "detected": False,
            "knee_angle_l": 165.0,
            "knee_angle_r": 165.0,
            "knee_valgus_l": 4.5,
            "knee_valgus_r": 4.0,
            "hip_angle_l": 160.0,
            "hip_angle_r": 160.0,
            "elbow_angle_l": 140.0,
            "elbow_angle_r": 140.0,
            "trunk_lateral_lean": 2.5,
            "trunk_forward_lean": 8.0,
            "pelvic_drop": 1.5,
            "bilateral_asymmetry": 6.2,
            "anomaly_score": 0.15
        }

        if not landmarks or len(landmarks) < 33:
            return default_metrics

        # Convert normalized coords (0..1) to pixel points
        def pt(idx: int) -> Tuple[float, float]:
            lm = landmarks[idx]
            return (lm.x * width, lm.y * height)

        try:
            # Key body points
            l_shldr = pt(11)
            r_shldr = pt(12)
            l_elbow = pt(13)
            r_elbow = pt(14)
            l_wrist = pt(15)
            r_wrist = pt(16)
            l_hip = pt(23)
            r_hip = pt(24)
            l_knee = pt(25)
            r_knee = pt(26)
            l_ankle = pt(27)
            r_ankle = pt(28)

            shldr_mid = ((l_shldr[0] + r_shldr[0]) / 2.0, (l_shldr[1] + r_shldr[1]) / 2.0)
            hip_mid = ((l_hip[0] + r_hip[0]) / 2.0, (l_hip[1] + r_hip[1]) / 2.0)

            # Joint Angles
            knee_angle_l = calculate_angle_2d(l_hip, l_knee, l_ankle)
            knee_angle_r = calculate_angle_2d(r_hip, r_knee, r_ankle)
            
            # Dynamic Knee Valgus Angle (deviation from collinear alignment)
            valgus_l = calculate_valgus_angle(l_hip, l_knee, l_ankle, is_left=True)
            valgus_r = calculate_valgus_angle(r_hip, r_knee, r_ankle, is_left=False)

            hip_angle_l = calculate_angle_2d(l_shldr, l_hip, l_knee)
            hip_angle_r = calculate_angle_2d(r_shldr, r_hip, r_knee)

            elbow_angle_l = calculate_angle_2d(l_shldr, l_elbow, l_wrist)
            elbow_angle_r = calculate_angle_2d(r_shldr, r_elbow, r_wrist)

            trunk_lateral, trunk_forward = calculate_trunk_lean(shldr_mid, hip_mid)
            pelvic_drop = calculate_pelvic_tilt(l_hip, r_hip)
            
            asymmetry = calculate_bilateral_asymmetry(knee_angle_l, knee_angle_r)

            # Instantaneous biomechanical anomaly score [0.0 - 1.0]
            valgus_penalty = max(0.0, (max(valgus_l, valgus_r) - 12.0) / 15.0)
            lean_penalty = max(0.0, (trunk_lateral - 8.0) / 12.0)
            asym_penalty = max(0.0, (asymmetry - 15.0) / 25.0)
            anomaly_score = float(round(min(1.0, valgus_penalty * 0.45 + lean_penalty * 0.3 + asym_penalty * 0.25), 3))

            return {
                "frame": frame_idx,
                "time": timestamp,
                "detected": True,
                "knee_angle_l": round(knee_angle_l, 1),
                "knee_angle_r": round(knee_angle_r, 1),
                "knee_valgus_l": round(valgus_l, 1),
                "knee_valgus_r": round(valgus_r, 1),
                "hip_angle_l": round(hip_angle_l, 1),
                "hip_angle_r": round(hip_angle_r, 1),
                "elbow_angle_l": round(elbow_angle_l, 1),
                "elbow_angle_r": round(elbow_angle_r, 1),
                "trunk_lateral_lean": round(trunk_lateral, 1),
                "trunk_forward_lean": round(trunk_forward, 1),
                "pelvic_drop": round(pelvic_drop, 1),
                "bilateral_asymmetry": round(asymmetry, 1),
                "anomaly_score": anomaly_score
            }
        except Exception:
            return default_metrics

    def _render_overlay(
        self,
        frame: np.ndarray,
        landmarks: Optional[List[Any]],
        metrics: Dict[str, Any],
        width: int,
        height: int,
        frame_idx: int,
        fps: float
    ) -> np.ndarray:
        """
        Draws visual skeleton landmarks, angle callouts, and HUD dashboard overlay.
        """
        img = frame.copy()

        # Draw HUD Header Banner
        hud_h = 75
        cv2.rectangle(img, (0, 0), (width, hud_h), (12, 17, 29), -1)
        cv2.line(img, (0, hud_h), (width, hud_h), (30, 41, 59), 2)

        # Telemetry Text
        valgus_l = metrics.get("knee_valgus_l", 0.0)
        valgus_r = metrics.get("knee_valgus_r", 0.0)
        max_valgus = max(valgus_l, valgus_r)
        
        # Color code risk indicator: Green <10°, Yellow 10°-15°, Red >15°
        if max_valgus >= 15.0 or metrics.get("trunk_lateral_lean", 0) > 12.0:
            status_text = "HIGH RISK ALERT"
            status_color = (40, 40, 235) # Red
        elif max_valgus >= 10.0:
            status_text = "MODERATE RISK"
            status_color = (0, 180, 245) # Yellow / Amber
        else:
            status_text = "NORMAL BIOMECHANICS"
            status_color = (60, 220, 80) # Green

        cv2.putText(img, "SPORTS BIOMECHANICS POSE TRACKER", (20, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (220, 220, 230), 2)
        cv2.putText(img, f"Frame: {frame_idx:04d} | Time: {metrics.get('time', 0.0):.2f}s | FPS: {fps:.1f}", (20, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (148, 163, 184), 1)

        cv2.putText(img, f"L-Valgus: {valgus_l:.1f}deg", (width // 2 - 200, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
        cv2.putText(img, f"R-Valgus: {valgus_r:.1f}deg", (width // 2 - 200, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

        cv2.putText(img, f"Trunk Lean: {metrics.get('trunk_lateral_lean', 0):.1f}deg", (width // 2 + 30, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
        cv2.putText(img, f"Asymmetry: {metrics.get('bilateral_asymmetry', 0):.1f}%", (width // 2 + 30, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

        # Status badge on upper right
        cv2.rectangle(img, (width - 270, 14), (width - 20, 60), status_color, 2)
        cv2.putText(img, status_text, (width - 255, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.55, status_color, 2)

        # Draw Skeleton bones & keypoints if detected
        if landmarks and len(landmarks) >= 33:
            coords = {}
            for i, lm in enumerate(landmarks):
                coords[i] = (int(lm.x * width), int(lm.y * height))

            # Draw bones
            for p1_idx, p2_idx in POSE_CONNECTIONS:
                if p1_idx in coords and p2_idx in coords:
                    pt1 = coords[p1_idx]
                    pt2 = coords[p2_idx]
                    # Highlight knees in red if valgus is high
                    if (p1_idx in [23, 25, 27] or p2_idx in [23, 25, 27]) and valgus_l > 12.0:
                        bone_color = (0, 70, 255)
                        bone_thickness = 4
                    elif (p1_idx in [24, 26, 28] or p2_idx in [24, 26, 28]) and valgus_r > 12.0:
                        bone_color = (0, 70, 255)
                        bone_thickness = 4
                    else:
                        bone_color = (235, 180, 52) # Cyan / Blue
                        bone_thickness = 3
                    cv2.line(img, pt1, pt2, bone_color, bone_thickness)

            # Draw key joints
            for idx in [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32]:
                if idx in coords:
                    c = coords[idx]
                    joint_color = (0, 240, 255) if idx not in [25, 26] else ((0, 70, 255) if max_valgus > 12.0 else (50, 255, 120))
                    cv2.circle(img, c, 6, joint_color, -1)
                    cv2.circle(img, c, 8, (255, 255, 255), 1)

            # Callout angles beside knees
            if 25 in coords:
                cv2.putText(img, f"{metrics.get('knee_angle_l', 0):.0f}deg", (coords[25][0] + 10, coords[25][1]), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
            if 26 in coords:
                cv2.putText(img, f"{metrics.get('knee_angle_r', 0):.0f}deg", (coords[26][0] - 65, coords[26][1]), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)

        return img
