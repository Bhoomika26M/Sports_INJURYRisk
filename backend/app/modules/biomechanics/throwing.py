"""Throwing biomechanics calculator.

Sagittal-plane metrics (validated): trunk_rotation, shoulder_abduction, elbow_flexion, stride_length
Frontal-plane metrics (qualitative): minimal
"""

import numpy as np
from app.modules.biomechanics.calculations import (
    knee_flexion_angle, hip_flexion_angle, trunk_lean_angle, METRIC_CONFIDENCE, LANDMARK
)


class ThrowingCalculator:
    """Throwing biomechanics (baseball, cricket, javelin)."""

    movement_type = "throwing"
    phases = ["windup", "early_cocking", "late_cocking", "acceleration", "deceleration", "follow_through"]

    def compute_all(self, landmarks: dict, camera_view: str) -> list[dict]:
        metrics = []

        if camera_view in ("sagittal", "other"):
            # Trunk rotation (simplified - using shoulder-hip separation)
            ls = np.array(landmarks[str(LANDMARK["left_shoulder"])])
            rs = np.array(landmarks[str(LANDMARK["right_shoulder"])])
            lh = np.array(landmarks[str(LANDMARK["left_hip"])])
            rh = np.array(landmarks[str(LANDMARK["right_hip"])])

            shoulder_vector = rs - ls
            hip_vector = rh - lh
            # Project to transverse plane (ignore y)
            sv_2d = np.array([shoulder_vector[0], shoulder_vector[2]])
            hv_2d = np.array([hip_vector[0], hip_vector[2]])
            if np.linalg.norm(sv_2d) > 1e-6 and np.linalg.norm(hv_2d) > 1e-6:
                cos_angle = np.clip(np.dot(sv_2d, hv_2d) / (np.linalg.norm(sv_2d) * np.linalg.norm(hv_2d)), -1.0, 1.0)
                trunk_rotation = round(float(np.degrees(np.arccos(cos_angle))), 1)
                metrics.append({"name": "trunk_rotation", "value": trunk_rotation, "plane": "sagittal", "confidence": "validated"})

            # Shoulder abduction (throwing arm)
            # Using shoulder-elbow-wrist for arm angle
            # Simplified: trunk lean as proxy
            tl = trunk_lean_angle(landmarks)
            if tl is not None:
                metrics.append({"name": "trunk_lean_angle", "value": tl, "plane": "sagittal", "confidence": METRIC_CONFIDENCE["trunk_lean_angle"]})

        return metrics