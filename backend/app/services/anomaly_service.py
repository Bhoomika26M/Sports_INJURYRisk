import math
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.schemas.anomaly import (
    AnomalyEvent, 
    AnomalyDetectionResponse,
    TechniqueAssessment,
    MotionInconsistency
)
from app.services.analysis_service import generate_biomechanics_analysis

class AnomalyDetectionService:
    def __init__(self):
        # Biomechanical Reference Ranges
        self.max_trunk_lean = 30.0
        self.max_asymmetry = 25.0
        self.max_frame_delta = 45.0 # Max degrees change allowed between adjacent frames (~30ms)
        self.valgus_ratio_threshold = 0.85
        self.pelvic_drop_threshold = 8.0
        self.max_lateral_sway = 12.0

    def detect_anomalies(self, db: Session, video_id: int) -> AnomalyDetectionResponse:
        """
        Module 7: Movement Anomaly Detection Engine
        - Movement deviation detection (trunk lean, asymmetry, valgus, pelvic drop, motion jitter)
        - Technique assessment (scoring, technical fault identification, technique grade)
        - Motion inconsistency analysis (coefficient of variation, kinematic smoothness)
        - Fatigue-related movement monitoring (intra-trial kinematic drift between early and late phases)
        - Performance decline detection (damping attenuation, motor control degradation)
        """
        analysis_data = generate_biomechanics_analysis(db, video_id)
        if not analysis_data:
            return AnomalyDetectionResponse(
                video_id=video_id, 
                total_anomalies=0, 
                events=[],
                movement_deviations_count=0
            )
            
        metrics = analysis_data.get("metrics_over_time", [])
        events: List[AnomalyEvent] = []
        
        prev_metrics = None
        valid_frames: List[Dict[str, Any]] = []
        
        for m in metrics:
            timestamp = m.get("timestamp_ms", 0)
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
                continue
                
            valid_frames.append(m)
                
            # Kinematic measurements
            lean = m.get("trunk_lean")
            lat_lean = m.get("lateral_trunk_lean")
            l_knee = m.get("left_knee_angle")
            r_knee = m.get("right_knee_angle")
            valgus_ratio = m.get("knee_valgus_ratio")
            pelvic_drop = m.get("pelvic_drop_angle")
            
            # 2. Reference Range Check: Sagittal Trunk Lean
            if lean is not None and lean > self.max_trunk_lean:
                events.append(AnomalyEvent(
                    timestamp_ms=timestamp,
                    metric="trunk_lean",
                    observed_value=round(lean, 1),
                    reference_rule=f"<= {self.max_trunk_lean} degrees",
                    severity="medium",
                    explanation=f"Excessive trunk lean ({round(lean, 1)}°) exceeds {self.max_trunk_lean}° reference range."
                ))
                
            # 3. Asymmetry Check: Bilateral Knee Flexion
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
                    
            # 4. Dynamic Knee Valgus Collapse (Frontal Plane Deviation)
            if valgus_ratio is not None and valgus_ratio < self.valgus_ratio_threshold:
                events.append(AnomalyEvent(
                    timestamp_ms=timestamp,
                    metric="knee_valgus",
                    observed_value=round(valgus_ratio, 2),
                    reference_rule=f">= {self.valgus_ratio_threshold} knee-to-ankle ratio",
                    severity="high" if valgus_ratio < 0.78 else "medium",
                    explanation=f"Dynamic medial knee collapse detected (Ratio: {round(valgus_ratio, 2)}). Indicates knee valgus strain."
                ))

            # 5. Pelvic Drop / Trendelenburg Instability
            if pelvic_drop is not None and pelvic_drop > self.pelvic_drop_threshold:
                events.append(AnomalyEvent(
                    timestamp_ms=timestamp,
                    metric="pelvic_drop",
                    observed_value=round(pelvic_drop, 1),
                    reference_rule=f"<= {self.pelvic_drop_threshold} degrees",
                    severity="medium",
                    explanation=f"Contralateral pelvic drop ({round(pelvic_drop, 1)}°) indicates abductor motor insufficiency."
                ))

            # 6. Coronal Lateral Trunk Sway
            if lat_lean is not None and lat_lean > self.max_lateral_sway:
                events.append(AnomalyEvent(
                    timestamp_ms=timestamp,
                    metric="lateral_trunk_sway",
                    observed_value=round(lat_lean, 1),
                    reference_rule=f"<= {self.max_lateral_sway} degrees",
                    severity="low",
                    explanation=f"Excessive lateral trunk sway ({round(lat_lean, 1)}°) altering center of gravity alignment."
                ))
                    
            # 7. Frame-to-Frame Variability Check (Jitter/Tracking Error or Jerk)
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

        # Total non-data-quality movement deviations
        deviations = [e for e in events if not e.is_data_quality_issue]
        movement_deviations_count = len(deviations)

        # -----------------------------------------------------------------
        # Technique Assessment
        # -----------------------------------------------------------------
        technique_score = 100.0
        primary_faults: List[str] = []

        if any(e.metric == "knee_valgus" for e in deviations):
            technique_score -= 22.0
            primary_faults.append("Medial knee collapse during dynamic phase (Dynamic Knee Valgus)")
        if any(e.metric == "trunk_lean" for e in deviations):
            technique_score -= 18.0
            primary_faults.append("Excessive forward trunk lean reducing lumbo-pelvic stability")
        if any(e.metric == "knee_asymmetry" for e in deviations):
            technique_score -= 20.0
            primary_faults.append("Bilateral limb asymmetry exceeding reference thresholds")
        if any(e.metric == "pelvic_drop" for e in deviations):
            technique_score -= 15.0
            primary_faults.append("Pelvic unleveling (Trendelenburg sign) during single-leg loading")
        if any(e.metric == "lateral_trunk_sway" for e in deviations):
            technique_score -= 10.0
            primary_faults.append("Excessive coronal lateral trunk sway")

        technique_score = max(20.0, min(100.0, round(technique_score, 1)))

        if technique_score >= 88.0:
            technique_grade = "Optimal"
            execution_summary = "Excellent kinematic alignment with minimal deviation across primary joint chains."
        elif technique_score >= 72.0:
            technique_grade = "Good"
            execution_summary = "Sound general movement mechanics with minor localized postural compensation."
        elif technique_score >= 55.0:
            technique_grade = "Suboptimal"
            execution_summary = "Noticeable kinematic deviations detected; technical cueing recommended."
        else:
            technique_grade = "High Risk"
            execution_summary = "Compensatory motor strategies and elevated joint stress observed; corrective intervention required."

        technique_assessment = TechniqueAssessment(
            technique_grade=technique_grade,
            technique_score=technique_score,
            execution_summary=execution_summary,
            primary_faults=primary_faults or ["Movement pattern meets reference technical guidelines"],
            execution_faults=primary_faults or ["Movement pattern meets reference technical guidelines"]
        )

        # -----------------------------------------------------------------
        # Motion Inconsistency Analysis
        # -----------------------------------------------------------------
        cv_pct = 0.0
        smoothness_score = 90.0
        consistency_rating = "Consistent"

        knee_angles = [f["left_knee_angle"] for f in valid_frames if f.get("left_knee_angle") is not None]
        if len(knee_angles) > 5:
            mean_angle = sum(knee_angles) / len(knee_angles)
            if mean_angle > 0:
                std_angle = math.sqrt(sum((a - mean_angle) ** 2 for a in knee_angles) / len(knee_angles))
                cv_pct = round((std_angle / mean_angle) * 100.0, 1)

            # Frame-to-frame delta jerk estimate
            deltas = [abs(knee_angles[i] - knee_angles[i - 1]) for i in range(1, len(knee_angles))]
            mean_delta = sum(deltas) / len(deltas) if deltas else 0.0
            smoothness_score = max(20.0, min(100.0, round(100.0 - (mean_delta * 4.5), 1)))

            if cv_pct > 24.0 or smoothness_score < 60.0:
                consistency_rating = "High Inconsistency"
            elif cv_pct > 14.0 or smoothness_score < 75.0:
                consistency_rating = "Mild Inconsistency"
            else:
                consistency_rating = "Consistent"

        motion_inconsistency = MotionInconsistency(
            coefficient_of_variation_pct=cv_pct,
            smoothness_jerk_score=smoothness_score,
            consistency_rating=consistency_rating,
            jerk_index=round(100.0 - smoothness_score, 1)
        )

        # -----------------------------------------------------------------
        # Fatigue-Related Movement Monitoring & Performance Decline Detection
        # -----------------------------------------------------------------
        fatigue_indicators: List[str] = []
        performance_decline_alerts: List[str] = []

        if len(valid_frames) >= 12:
            n_third = max(3, len(valid_frames) // 3)
            early_frames = valid_frames[:n_third]
            late_frames = valid_frames[-n_third:]

            # A. Flexion damping attenuation (stiffer landings in late phase)
            early_knees = [f["left_knee_angle"] for f in early_frames if f.get("left_knee_angle") is not None]
            late_knees = [f["left_knee_angle"] for f in late_frames if f.get("left_knee_angle") is not None]

            if early_knees and late_knees:
                early_min = min(early_knees)
                late_min = min(late_knees)
                # If late minimum is higher (less deep flexion), damping decreased
                damping_loss = late_min - early_min
                if damping_loss > 8.0:
                    fatigue_indicators.append(
                        f"Reduced knee flexion depth in late trial ({damping_loss:.1f}° loss), indicating quadriceps eccentric fatigue."
                    )
                    performance_decline_alerts.append(
                        f"Landing shock absorption declined by {round((damping_loss / max(1.0, 180.0 - early_min)) * 100)}%."
                    )

            # B. Core / Trunk stability drift
            early_leans = [f["trunk_lean"] for f in early_frames if f.get("trunk_lean") is not None]
            late_leans = [f["trunk_lean"] for f in late_frames if f.get("trunk_lean") is not None]
            if early_leans and late_leans:
                lean_drift = (sum(late_leans) / len(late_leans)) - (sum(early_leans) / len(early_leans))
                if lean_drift > 5.0:
                    fatigue_indicators.append(
                        f"Trunk posture drifted forward by {lean_drift:.1f}° toward end of trial (spinal erector fatigue)."
                    )

            # C. Asymmetry escalation
            early_diffs = [
                abs(f["left_knee_angle"] - f["right_knee_angle"]) 
                for f in early_frames 
                if f.get("left_knee_angle") is not None and f.get("right_knee_angle") is not None
            ]
            late_diffs = [
                abs(f["left_knee_angle"] - f["right_knee_angle"]) 
                for f in late_frames 
                if f.get("left_knee_angle") is not None and f.get("right_knee_angle") is not None
            ]
            if early_diffs and late_diffs:
                asym_drift = (sum(late_diffs) / len(late_diffs)) - (sum(early_diffs) / len(early_diffs))
                if asym_drift > 6.0:
                    fatigue_indicators.append(
                        f"Bilateral limb asymmetry increased by {asym_drift:.1f}° across trial repetitions."
                    )
                    performance_decline_alerts.append(
                        "Compensatory unilateral limb unloading observed in late repetitions."
                    )

        if technique_score < 70.0:
            performance_decline_alerts.append(
                f"Movement technique degradation flagged ({technique_grade} Grade, {technique_score}/100)."
            )
        if fatigue_indicators and not performance_decline_alerts:
            performance_decline_alerts.append(
                "Performance decline detected: kinematic drift and movement efficiency degradation."
            )

        return AnomalyDetectionResponse(
            video_id=video_id,
            total_anomalies=len(events),
            events=events,
            movement_deviations_count=movement_deviations_count,
            technique_assessment=technique_assessment,
            motion_inconsistency=motion_inconsistency,
            fatigue_indicators=fatigue_indicators,
            performance_decline_alerts=performance_decline_alerts
        )

anomaly_service = AnomalyDetectionService()
