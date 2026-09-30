"""Running biomechanics calculator.

Sagittal-plane metrics (validated): knee_flexion_stance, hip_extension, trunk_lean, pelvic_drop
Frontal-plane metrics (qualitative): pelvic_drop, knee_window
"""

from app.modules.biomechanics.calculations import (
    knee_flexion_angle, hip_flexion_angle, trunk_lean_angle, knee_valgus_flag, METRIC_CONFIDENCE
)


class RunningCalculator:
    """Running gait biomechanics."""

    movement_type = "running"
    phases = ["initial_contact", "midstance", "terminal_stance", "swing"]

    def compute_all(self, landmarks: dict, camera_view: str) -> list[dict]:
        metrics = []

        if camera_view in ("sagittal", "other"):
            # Knee flexion during stance
            kf_l = knee_flexion_angle(landmarks, "left")
            metrics.append({"name": "knee_flexion_angle_left", "value": kf_l, "plane": "sagittal", "confidence": METRIC_CONFIDENCE["knee_flexion_angle_left"]})

            kf_r = knee_flexion_angle(landmarks, "right")
            metrics.append({"name": "knee_flexion_angle_right", "value": kf_r, "plane": "sagittal", "confidence": METRIC_CONFIDENCE["knee_flexion_angle_right"]})

            # Hip extension (negative hip flexion)
            hf_l = hip_flexion_angle(landmarks, "left")
            metrics.append({"name": "hip_flexion_angle_left", "value": hf_l, "plane": "sagittal", "confidence": METRIC_CONFIDENCE["hip_flexion_angle_left"]})

            hf_r = hip_flexion_angle(landmarks, "right")
            metrics.append({"name": "hip_flexion_angle_right", "value": hf_r, "plane": "sagittal", "confidence": METRIC_CONFIDENCE["hip_flexion_angle_right"]})

            # Trunk lean
            tl = trunk_lean_angle(landmarks)
            if tl is not None:
                metrics.append({"name": "trunk_lean_angle", "value": tl, "plane": "sagittal", "confidence": METRIC_CONFIDENCE["trunk_lean_angle"]})

        if camera_view in ("frontal", "other"):
            # Pelvic drop (contralateral hip drop) - qualitative
            kv_l = knee_valgus_flag(landmarks, "left")
            if kv_l["deviation_pct"] is not None:
                metrics.append({"name": "knee_valgus_deviation_left", "value": kv_l["deviation_pct"], "plane": "frontal", "confidence": METRIC_CONFIDENCE["knee_valgus_deviation_left"]})

            kv_r = knee_valgus_flag(landmarks, "right")
            if kv_r["deviation_pct"] is not None:
                metrics.append({"name": "knee_valgus_deviation_right", "value": kv_r["deviation_pct"], "plane": "frontal", "confidence": METRIC_CONFIDENCE["knee_valgus_deviation_right"]})

        return metrics