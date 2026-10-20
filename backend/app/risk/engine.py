"""Explainable risk scoring engine."""

import numpy as np
from typing import Dict, List, Optional, Tuple
from app.pose.estimator import Keypoint
from app.biomechanics.calculator import BiomechanicsCalculator
from app.risk.rules import RiskRuleSet
from app.risk.anatomy import BODY_PARTS
from app.risk.knowledge_base import get_joint_muscles, get_risk_knowledge


class RiskFinding:
    """An individual explainable risk finding."""

    def __init__(self):
        self.severity = "low"  # low, moderate, high, critical
        self.risk_type = "biomechanical"
        self.risk_tag = ""  # knowledge-base key, e.g. "lumbar_strain"
        self.body_parts = []
        self.issue = ""
        self.rationale = ""
        self.evidence = []  # list of metric values with units
        self.recommended_actions = []
        self.score_contribution = 0.0  # 0-100 impact
        # Anatomical context (filled from the knowledge base)
        self.scientific_term = ""
        self.structures_at_risk = []
        self.muscles = {"primary": [], "stabilizers": []}
        self.muscles_overactive = []
        self.muscles_underactive = []
        self.mechanism = ""


class InjuryRiskEngine:
    """Computes explainable risk scores from biomechanical measurements."""

    def __init__(self):
        self.biomech = BiomechanicsCalculator()
        self.rules = RiskRuleSet()

    def _severity_from_contribution(self, c: float) -> str:
        if c >= 40:
            return "critical"
        if c >= 25:
            return "high"
        if c >= 12:
            return "moderate"
        return "low"

    def evaluate(
        self,
        keypoints_sequence: List[List[Keypoint]],
        timestamps: List[float],
        activity: str = "squat",
        pose_quality: Optional[Dict] = None,
    ) -> Dict:
        """Evaluate injury risk across frames."""
        results = {
            "overall_risk_score": 0.0,
            "risk_level": "low",
            "risk_of": [],
            "findings": [],
            "joints_and_muscles": [],
            "explanation": {
                "how_score_arrived_at": [],
                "components": {
                    "movement_quality": 0.0,
                    "symmetry": 0.0,
                    "alignment": 0.0,
                    "control": 0.0,
                    "pose_quality_penalty": 0.0,
                },
                "weights": {
                    "movement_quality": 0.4,
                    "symmetry": 0.25,
                    "alignment": 0.2,
                    "control": 0.15,
                },
            },
            "suggestions": [],
            "frame_insights": [],  # optional per-frame key deviations
        }

        if not keypoints_sequence or not any(keypoints_sequence):
            results["explanation"]["how_score_arrived_at"].append(
                "No valid pose keypoints detected across frames; risk assessment unavailable."
            )
            return results

        # Compute frame angles
        lk, rk, lh, rh, tl = [], [], [], [], []
        for frame_kps in keypoints_sequence:
            lk.append(self.biomech.calculate_knee_angle(frame_kps, "left"))
            rk.append(self.biomech.calculate_knee_angle(frame_kps, "right"))
            lh.append(self.biomech.calculate_hip_angle(frame_kps, "left"))
            rh.append(self.biomech.calculate_hip_angle(frame_kps, "right"))
            tl.append(self.biomech.calculate_trunk_lean(frame_kps))

        lk_v = [a for a in lk if a is not None]
        rk_v = [a for a in rk if a is not None]
        lh_v = [a for a in lh if a is not None]
        rh_v = [a for a in rh if a is not None]
        tl_v = [a for a in tl if a is not None]

        # Joint angles measured + the muscles acting on/around each joint.
        # This is the "what was measured, and what it loads" inventory that the
        # UI lists alongside the risk findings.
        joints_and_muscles = []
        for joint, side, series in (
            ("knee", "left", lk_v), ("knee", "right", rk_v),
            ("hip", "left", lh_v), ("hip", "right", rh_v),
            ("trunk", "center", tl_v),
        ):
            muscles = get_joint_muscles(joint)
            entry = {
                "joint": joint,
                "side": side,
                "muscles_primary": muscles["primary"],
                "muscles_stabilizers": muscles["stabilizers"],
                "samples": len(series),
            }
            if series:
                entry.update({
                    "mean_deg": round(float(np.mean(series)), 2),
                    "min_deg": round(float(np.min(series)), 2),
                    "max_deg": round(float(np.max(series)), 2),
                    "rom_deg": round(float(np.max(series) - np.min(series)), 2),
                })
            joints_and_muscles.append(entry)
        results["joints_and_muscles"] = joints_and_muscles

        findings: List[Dict] = []

        # Symmetry
        if lk_v and rk_v:
            minl = min(len(lk_v), len(rk_v))
            diffs = [abs(lk_v[i] - rk_v[i]) for i in range(minl)]
            asym_knee = float(np.mean(diffs)) if diffs else 0.0
            max_asym = float(np.max(diffs)) if diffs else 0.0
            tol = self.rules.squat_rules()["asymmetry_tolerance_deg"] if activity == "squat" else 5.0
            symmetry_score = max(0.0, 100.0 - asym_knee * 10.0)
            results["explanation"]["components"]["symmetry"] = float(symmetry_score)
            if max_asym > tol:
                f = RiskFinding()
                f.risk_type = "asymmetry"
                f.risk_tag = "knee_overload_asymmetry"
                f.body_parts = ["knee"]
                f.issue = "Knee movement asymmetry detected"
                f.rationale = "Repeated side-to-side differences in knee flexion suggest uneven loading and reduced control."
                f.evidence = [
                    {"metric": "mean_knee_asymmetry_deg", "value": round(asym_knee, 2), "unit": "°"},
                    {"metric": "max_knee_asymmetry_deg", "value": round(max_asym, 2), "unit": "°"},
                    {"metric": "tolerance_deg", "value": tol, "unit": "°"},
                ]
                f.score_contribution = min(30.0, max_asym * 3.0)
                f.severity = self._severity_from_contribution(f.score_contribution)
                f.recommended_actions = [
                    "Focus on bilateral control (mirror squats, tempo work)",
                    "Check limb dominance/load distribution",
                    "Progress gradually with volume",
                ]
                findings.append(self._to_dict(f))
                results["risk_of"].append("knee_overload_asymmetry")

        # Alignment (trunk lean)
        if tl_v:
            max_lean = float(np.max([abs(x) for x in tl_v]))
            mean_lean = float(np.mean([abs(x) for x in tl_v]))
            lean_thresh = self.rules.squat_rules()["excessive_trunk_lean"]
            align_score = max(0.0, 100.0 - mean_lean * 3.0)
            results["explanation"]["components"]["alignment"] = float(align_score)
            if max_lean > lean_thresh:
                f = RiskFinding()
                f.risk_type = "alignment"
                f.risk_tag = "lumbar_strain"
                f.body_parts = ["trunk", "lower_back"]
                f.issue = "Excessive trunk lean observed"
                f.rationale = "Forward lean beyond typical thresholds can shift load to lumbar spine and reduce knee drive."
                f.evidence = [
                    {"metric": "max_trunk_lean_abs_deg", "value": round(max_lean, 2), "unit": "°"},
                    {"metric": "mean_trunk_lean_abs_deg", "value": round(mean_lean, 2), "unit": "°"},
                    {"metric": "threshold_deg", "value": lean_thresh, "unit": "°"},
                ]
                f.score_contribution = min(25.0, (max_lean - lean_thresh) * 2.0)
                f.severity = self._severity_from_contribution(f.score_contribution)
                f.recommended_actions = [
                    "Mobility: ankles/hips; squat form cues (chest up, sit back)",
                    "Reduce depth/load temporarily",
                    "Consider box squats to control depth",
                ]
                findings.append(self._to_dict(f))
                results["risk_of"].append("lumbar_strain")

        # ROM / movement quality
        if lk_v:
            rom_k = float(np.max(lk_v) - np.min(lk_v))
            rules = self.rules.squat_rules()
            mq = 100.0
            if rom_k < rules["min_acceptable_rom_knee"]:
                mq -= (rules["min_acceptable_rom_knee"] - rom_k) * 1.5
            if rom_k > rules["max_acceptable_rom_knee"]:
                mq -= (rom_k - rules["max_acceptable_rom_knee"]) * 1.0
            mq = max(0.0, mq)
            results["explanation"]["components"]["movement_quality"] = float(mq)
            if rom_k < rules["min_acceptable_rom_knee"]:
                f = RiskFinding()
                f.risk_type = "range_of_motion"
                f.risk_tag = "limited_rom_knee"
                f.body_parts = ["knee"]
                f.issue = "Limited knee range of motion"
                f.rationale = "Insufficient ROM may reflect mobility restriction or compensation pattern increasing strain elsewhere."
                f.evidence = [
                    {"metric": "knee_rom_deg", "value": round(rom_k, 2), "unit": "°"},
                    {"metric": "min_target_deg", "value": rules["min_acceptable_rom_knee"], "unit": "°"},
                ]
                f.score_contribution = min(20.0, (rules["min_acceptable_rom_knee"] - rom_k))
                f.severity = self._severity_from_contribution(f.score_contribution)
                f.recommended_actions = [
                    "Ankle dorsiflexion + hip mobility drills",
                    "Box squats to safe depth",
                    "Gradual ROM progression",
                ]
                findings.append(self._to_dict(f))
                results["risk_of"].append("limited_rom_knee")

        # Control/smoothness
        if len(lk_v) > 1:
            diffs_a = [abs(lk_v[i + 1] - lk_v[i]) for i in range(len(lk_v) - 1)]
            jerk_like = float(np.std(diffs_a)) if diffs_a else 0.0
            ctrl = max(0.0, 100.0 - jerk_like * 4.0)
            results["explanation"]["components"]["control"] = float(ctrl)
            if jerk_like > 8.0:
                f = RiskFinding()
                f.risk_type = "control"
                f.risk_tag = "movement_control_deficit"
                f.body_parts = ["knee"]
                f.issue = "Movement lacks smoothness (jerky transitions)"
                f.rationale = "High angular velocity variability suggests reduced eccentric control."
                f.evidence = [{"metric": "knee_angle_diff_std_deg_per_frame", "value": round(jerk_like, 2), "unit": "°/step"}]
                f.score_contribution = min(15.0, jerk_like * 1.2)
                f.severity = self._severity_from_contribution(f.score_contribution)
                f.recommended_actions = [
                    "Tempo training (slower eccentric)",
                    "Isometric holds at key positions",
                    "Lighten load until control stabilizes",
                ]
                findings.append(self._to_dict(f))
                results["risk_of"].append("movement_control_deficit")

        # Pose quality penalty
        pq_pen = 0.0
        if pose_quality:
            mq_pq = pose_quality.get("quality_percentage", 100.0)
            mean_c = pose_quality.get("mean_confidence", 1.0)
            pq_pen = max(0.0, 100.0 - (mq_pq * 0.6 + mean_c * 40.0))
            results["explanation"]["components"]["pose_quality_penalty"] = float(pq_pen)
            if pq_pen > 20.0:
                f = RiskFinding()
                f.risk_type = "data_quality"
                f.risk_tag = "pose_quality"
                f.body_parts = ["system"]
                f.issue = "Reduced pose estimation confidence"
                f.rationale = "Low confidence/valid frames reduce measurement reliability."
                f.evidence = [
                    {"metric": "quality_percentage", "value": round(mq_pq, 1), "unit": "%"},
                    {"metric": "mean_confidence", "value": round(mean_c, 3), "unit": ""},
                ]
                f.score_contribution = min(10.0, pq_pen * 0.3)
                f.severity = "low"
                f.recommended_actions = ["Better lighting, clearer view, slower movement, stable camera"]
                findings.append(self._to_dict(f))
                results["risk_of"].append("pose_quality")

        # Weighted overall (0-100, higher = risk)
        w = results["explanation"]["weights"]
        c = results["explanation"]["components"]
        base = (
            (100.0 - c["movement_quality"]) * w["movement_quality"]
            + (100.0 - c["symmetry"]) * w["symmetry"]
            + (100.0 - c["alignment"]) * w["alignment"]
            + (100.0 - c["control"]) * w["control"]
        )
        overall = base + pq_pen * 0.15
        overall = float(max(0.0, min(100.0, overall)))

        results["overall_risk_score"] = round(overall, 2)
        if overall >= 70:
            results["risk_level"] = "critical"
        elif overall >= 50:
            results["risk_level"] = "high"
        elif overall >= 30:
            results["risk_level"] = "moderate"
        else:
            results["risk_level"] = "low"

        results["findings"] = findings
        results["explanation"]["how_score_arrived_at"] = self._explain_score(overall, c, w, pq_pen)

        # Top suggestions
        seen = set()
        for f in findings:
            for a in f["recommended_actions"]:
                if a not in seen:
                    results["suggestions"].append(a)
                    seen.add(a)
                    if len(results["suggestions"]) >= 8:
                        break
            if len(results["suggestions"]) >= 8:
                break
        if not results["suggestions"]:
            results["suggestions"] = [
                "Maintain current form with controlled tempo",
                "Focus on symmetry and consistency",
                "Progress volume gradually",
            ]

        return results

    def _to_dict(self, f: RiskFinding) -> Dict:
        # Attach the anatomical knowledge for this finding's risk tag
        self._apply_knowledge(f)
        return {
            "severity": f.severity,
            "risk_type": f.risk_type,
            "risk_tag": f.risk_tag,
            "body_parts": f.body_parts,
            "issue": f.issue,
            "rationale": f.rationale,
            "evidence": f.evidence,
            "recommended_actions": f.recommended_actions,
            "score_contribution": round(f.score_contribution, 2),
            "scientific_term": f.scientific_term,
            "structures_at_risk": f.structures_at_risk,
            "muscles": f.muscles,
            "muscles_overactive": f.muscles_overactive,
            "muscles_underactive": f.muscles_underactive,
            "mechanism": f.mechanism,
        }

    def _apply_knowledge(self, f: RiskFinding) -> None:
        """Fill a finding's anatomical context from the knowledge base."""
        kb = get_risk_knowledge(f.risk_tag)
        f.scientific_term = kb.get("scientific_term", "")
        f.structures_at_risk = kb.get("structures_at_risk", [])
        f.muscles_overactive = kb.get("muscles_overactive", [])
        f.muscles_underactive = kb.get("muscles_underactive", [])
        f.mechanism = kb.get("mechanism", "")

        muscles: Dict[str, List[str]] = {"primary": [], "stabilizers": []}
        for body_part in f.body_parts:
            joint_muscles = get_joint_muscles(body_part)
            for group in ("primary", "stabilizers"):
                for muscle in joint_muscles.get(group, []):
                    if muscle not in muscles[group]:
                        muscles[group].append(muscle)
        f.muscles = muscles

    def _explain_score(self, overall: float, c: Dict, w: Dict, pq_pen: float) -> List[str]:
        """Show the arithmetic that produced the score, line by line."""
        labels = {
            "movement_quality": "Movement quality (ROM/technique)",
            "symmetry": "Left/right symmetry",
            "alignment": "Trunk/body alignment",
            "control": "Smoothness / eccentric control",
        }
        lines = [
            f"Overall risk score = {overall:.1f} / 100  (higher = greater biomechanical injury risk)",
            "Each component below is scored 0-100 where 100 = ideal. The risk it "
            "contributes is its deficit (100 - score) scaled by its weight:",
        ]
        total = 0.0
        for key in ("movement_quality", "symmetry", "alignment", "control"):
            deficit = 100.0 - c.get(key, 0.0)
            contribution = deficit * w.get(key, 0.0)
            total += contribution
            lines.append(
                f"  - {labels[key]}: (100 - {c.get(key, 0.0):.1f}) x {w.get(key, 0.0):.2f} "
                f"= {contribution:.1f} points"
            )
        if pq_pen > 0:
            penalty_points = pq_pen * 0.15
            lines.append(
                f"  - Pose-quality penalty: {pq_pen:.1f} x 0.15 = {penalty_points:.1f} points"
            )
            lines.append(
                f"Total = {total:.1f} (movement) + {penalty_points:.1f} (data quality) "
                f"= {overall:.1f} / 100"
            )
        else:
            lines.append(f"Total = {total:.1f} / 100")
        lines.append(
            "Weights: movement quality 0.40, symmetry 0.25, alignment 0.20, "
            "control 0.15 (activity-specific thresholds applied to each metric)."
        )
        return lines
