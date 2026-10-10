"""Sprinting biomechanics calculator.

Sagittal-plane metrics (validated): hip_flexion_swing, knee_flexion_swing, trunk_lean, ankle_plantarflexion
Frontal-plane metrics (qualitative): minimal (sagittal dominant)
"""

from app.modules.biomechanics.calculations import (
    knee_flexion_angle, hip_flexion_angle, trunk_lean_angle, knee_valgus_flag, METRIC_CONFIDENCE, lower_body_extras
)


class SprintingCalculator:
    """Sprinting biomechanics."""

    movement_type = "sprinting"
    phases = ["acceleration", "max_velocity", "deceleration"]

    def compute_all(self, landmarks: dict, camera_view: str) -> list[dict]:
        metrics = []

        if camera_view in ("sagittal", "other"):
            # Hip flexion during swing
            hf_l = hip_flexion_angle(landmarks, "left")
            metrics.append({"name": "hip_flexion_angle_left", "value": hf_l, "plane": "sagittal", "confidence": METRIC_CONFIDENCE["hip_flexion_angle_left"]})

            hf_r = hip_flexion_angle(landmarks, "right")
            metrics.append({"name": "hip_flexion_angle_right", "value": hf_r, "plane": "sagittal", "confidence": METRIC_CONFIDENCE["hip_flexion_angle_right"]})

            # Knee flexion during swing
            kf_l = knee_flexion_angle(landmarks, "left")
            metrics.append({"name": "knee_flexion_angle_left", "value": kf_l, "plane": "sagittal", "confidence": METRIC_CONFIDENCE["knee_flexion_angle_left"]})

            kf_r = knee_flexion_angle(landmarks, "right")
            metrics.append({"name": "knee_flexion_angle_right", "value": kf_r, "plane": "sagittal", "confidence": METRIC_CONFIDENCE["knee_flexion_angle_right"]})

            # Trunk lean
            tl = trunk_lean_angle(landmarks)
            if tl is not None:
                metrics.append({"name": "trunk_lean_angle", "value": tl, "plane": "sagittal", "confidence": METRIC_CONFIDENCE["trunk_lean_angle"]})

        if camera_view in ("frontal", "other"):
            kv_l = knee_valgus_flag(landmarks, "left")
            if kv_l["deviation_pct"] is not None:
                metrics.append({"name": "knee_valgus_deviation_left", "value": kv_l["deviation_pct"], "plane": "frontal", "confidence": METRIC_CONFIDENCE["knee_valgus_deviation_left"]})

            kv_r = knee_valgus_flag(landmarks, "right")
            if kv_r["deviation_pct"] is not None:
                metrics.append({"name": "knee_valgus_deviation_right", "value": kv_r["deviation_pct"], "plane": "frontal", "confidence": METRIC_CONFIDENCE["knee_valgus_deviation_right"]})

        metrics += lower_body_extras(landmarks, camera_view)  # Engine 2.3: ankle dorsiflexion (sagittal), hip adduction (frontal, qualitative)
        return metrics