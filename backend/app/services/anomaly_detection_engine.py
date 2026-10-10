import numpy as np
from typing import List, Dict, Any

class AnomalyDetectionEngine:
    """
    Movement Anomaly Detection Engine:
    - Movement deviation detection
    - Technique assessment
    - Motion inconsistency analysis
    - Fatigue-related movement monitoring
    - Performance decline detection
    """

    def detect_anomalies(
        self,
        time_series: List[Dict[str, Any]],
        activity_type: str = "Running"
    ) -> Dict[str, Any]:
        if not time_series:
            return {"events": [], "fatigue_drift_pct": 0.0, "consistency_score": 90.0}

        events = []
        n_frames = len(time_series)

        # 1. Check frame-by-frame threshold breaches
        for idx, f in enumerate(time_series):
            frame_num = f.get("frame", idx)
            t_sec = f.get("time", round(idx / 30.0, 2))
            valgus_l = f.get("knee_valgus_l", 0.0)
            valgus_r = f.get("knee_valgus_r", 0.0)
            trunk_lat = f.get("trunk_lateral_lean", 0.0)
            asym = f.get("bilateral_asymmetry", 0.0)

            # Severe Knee Valgus spike
            if valgus_l >= 15.0 or valgus_r >= 15.0:
                side = "Left" if valgus_l >= valgus_r else "Right"
                v_val = max(valgus_l, valgus_r)
                events.append({
                    "frame_index": frame_num,
                    "timestamp_sec": t_sec,
                    "anomaly_type": f"Severe Dynamic Knee Valgus ({side})",
                    "severity": "Critical" if v_val > 18.0 else "High",
                    "metric_value": v_val,
                    "threshold_value": 15.0,
                    "description": f"Dynamic valgus collapse of {v_val:.1f}deg observed. High risk of ACL and MCL strain during loading phase."
                })

            # Excessive Trunk Lateral Lean
            if trunk_lat >= 12.0:
                events.append({
                    "frame_index": frame_num,
                    "timestamp_sec": t_sec,
                    "anomaly_type": "Excessive Lateral Trunk Lean",
                    "severity": "High",
                    "metric_value": trunk_lat,
                    "threshold_value": 12.0,
                    "description": f"Trunk tilted {trunk_lat:.1f}deg from vertical. Induces compensatory spinal shear and knee abduction torque."
                })

            # Acute Deceleration Asymmetry
            if asym >= 20.0:
                events.append({
                    "frame_index": frame_num,
                    "timestamp_sec": t_sec,
                    "anomaly_type": "Severe Bilateral Kinematic Asymmetry",
                    "severity": "Medium",
                    "metric_value": asym,
                    "threshold_value": 20.0,
                    "description": f"Limb movement discrepancy of {asym:.1f}%. Uneven load distribution increases unilateral injury predisposition."
                })

        # Deduplicate proximate events within 10 frames
        filtered_events = []
        last_t = -1.0
        for ev in events:
            if last_t < 0 or (ev["timestamp_sec"] - last_t) > 0.4:
                filtered_events.append(ev)
                last_t = ev["timestamp_sec"]

        # 2. Fatigue Drift Monitoring: compare first 30% of frames vs last 30%
        first_third = time_series[:max(1, int(n_frames * 0.3))]
        last_third = time_series[int(n_frames * 0.7):]

        fatigue_drift_pct = 0.0
        if first_third and last_third:
            early_valgus = np.mean([max(f.get("knee_valgus_l", 0), f.get("knee_valgus_r", 0)) for f in first_third])
            late_valgus = np.mean([max(f.get("knee_valgus_l", 0), f.get("knee_valgus_r", 0)) for f in last_third])
            
            if early_valgus > 0:
                drift = ((late_valgus - early_valgus) / early_valgus) * 100.0
                fatigue_drift_pct = max(0.0, round(float(drift), 1))

        # 3. Motion Consistency Analysis
        valgus_all = [max(f.get("knee_valgus_l", 0), f.get("knee_valgus_r", 0)) for f in time_series]
        variance = float(np.var(valgus_all)) if valgus_all else 1.0
        consistency_score = max(30.0, min(100.0, round(100.0 - variance * 3.5, 1)))

        return {
            "events": filtered_events[:10], # Top anomaly events
            "fatigue_drift_pct": fatigue_drift_pct,
            "consistency_score": consistency_score,
            "total_anomalies_detected": len(filtered_events)
        }
