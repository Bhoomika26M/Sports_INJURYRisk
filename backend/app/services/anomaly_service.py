from typing import Dict, Any, List
from app.schemas.anomaly import AnomalyEvent, AnomalyDetectionResponse
from app.services.analysis_service import generate_biomechanics_analysis
from sqlalchemy.orm import Session

class AnomalyDetectionService:
    def __init__(self):
        # Reference ranges
        self.max_trunk_lean = 30.0
        self.max_asymmetry = 25.0
        self.max_frame_delta = 45.0 # Max degrees change allowed between adjacent frames (~30ms)

    def detect_anomalies(self, db: Session, video_id: int) -> AnomalyDetectionResponse:
        analysis_data = generate_biomechanics_analysis(db, video_id)
        if not analysis_data:
            return AnomalyDetectionResponse(video_id=video_id, total_anomalies=0, events=[])
            
        metrics = analysis_data.get("metrics_over_time", [])
        events: List[AnomalyEvent] = []
        
        prev_metrics = None
        
        for m in metrics:
            timestamp = m["timestamp_ms"]
            quality = m.get("quality_flag", "OK")
            
            # 1. Data Quality Checks
            if quality != "OK":
                events.append(AnomalyEvent(
                    timestamp_ms=timestamp,
                    metric="data_quality",
                    observed_value=None,
                    reference_rule="Must have high-confidence landmarks",
                    severity="high",
                    explanation=f"Data quality issue flagged: {quality}. Possible missing landmarks or camera angle limitation.",
                    is_data_quality_issue=True
                ))
                # Skip kinematic checks if data is bad
                continue
                
            # Kinematic checks
            lean = m.get("trunk_lean")
            l_knee = m.get("left_knee_angle")
            r_knee = m.get("right_knee_angle")
            
            # 2. Reference Range Check
            if lean is not None and lean > self.max_trunk_lean:
                events.append(AnomalyEvent(
                    timestamp_ms=timestamp,
                    metric="trunk_lean",
                    observed_value=round(lean, 1),
                    reference_rule=f"<= {self.max_trunk_lean} degrees",
                    severity="medium",
                    explanation=f"Excessive trunk lean ({round(lean, 1)}°) exceeds {self.max_trunk_lean}° reference range."
                ))
                
            # 3. Asymmetry Check
            if l_knee is not None and r_knee is not None:
                diff = abs(l_knee - r_knee)
                if diff > self.max_asymmetry:
                    events.append(AnomalyEvent(
                        timestamp_ms=timestamp,
                        metric="knee_asymmetry",
                        observed_value=round(diff, 1),
                        reference_rule=f"<= {self.max_asymmetry} degrees",
                        severity="medium",
                        explanation=f"High left-right knee asymmetry ({round(diff, 1)}°) exceeds {self.max_asymmetry}° threshold."
                    ))
                    
            # 4. Frame-to-Frame Variability Check (Jitter/Tracking Error or Jerk)
            if prev_metrics and prev_metrics.get("quality_flag") == "OK":
                prev_l = prev_metrics.get("left_knee_angle")
                if prev_l is not None and l_knee is not None:
                    delta = abs(l_knee - prev_l)
                    if delta > self.max_frame_delta:
                        events.append(AnomalyEvent(
                            timestamp_ms=timestamp,
                            metric="movement_variability",
                            observed_value=round(delta, 1),
                            reference_rule=f"Delta <= {self.max_frame_delta} degrees per frame",
                            severity="high",
                            explanation=f"Unrealistic frame-to-frame joint angle change ({round(delta, 1)}°). Likely a tracking anomaly."
                        ))
            
            prev_metrics = m
            
        return AnomalyDetectionResponse(
            video_id=video_id,
            total_anomalies=len(events),
            events=events
        )

anomaly_service = AnomalyDetectionService()
