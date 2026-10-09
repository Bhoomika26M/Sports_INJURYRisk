from typing import Dict, Any, List

class InjuryPredictionEngine:
    """
    Injury Risk Prediction Engine covering the 6 specific injury categories from the PDF:
    - ACL Injury Risk
    - Hamstring Injury Risk
    - Ankle Sprain Risk
    - Shoulder Injury Risk
    - Lower Back Injury Risk
    - Overuse Injury Risk
    """

    def predict_categories(
        self,
        biomechanics: Dict[str, Any],
        athlete_profile: Dict[str, Any],
        weighted_scores: Dict[str, Any]
    ) -> Dict[str, Any]:
        max_valgus = max(
            biomechanics.get("knee_valgus_left_max", 0.0),
            biomechanics.get("knee_valgus_right_max", 0.0)
        )
        trunk_lean = biomechanics.get("trunk_lean_lateral_max", 0.0)
        pelvic_drop = biomechanics.get("pelvic_drop_deg", 0.0)
        landing_score = biomechanics.get("landing_mechanics_score", 80.0)
        symmetry_score = biomechanics.get("movement_symmetry_score", 90.0)
        force_g = biomechanics.get("force_impact_estimation_g", 2.0)
        
        acwr = athlete_profile.get("acwr", 1.15)
        history = [str(x.get("injury_name", "")).lower() + " " + str(x.get("body_part", "")).lower() for x in athlete_profile.get("injury_history", [])]
        history_text = " ".join(history)

        categories = {}

        # 1. ACL Injury Risk
        # Clinical biomarkers: Dynamic Knee Valgus > 12-15°, stiff landing (low knee flexion), high bilateral asymmetry
        acl_factors = []
        acl_score = 15.0
        if max_valgus >= 15.0:
            acl_factors.append(f"Severe Dynamic Knee Valgus ({max_valgus:.1f}deg > 15deg threshold)")
            acl_score += 45.0
        elif max_valgus >= 10.0:
            acl_factors.append(f"Moderate Dynamic Knee Valgus ({max_valgus:.1f}deg)")
            acl_score += 25.0

        if landing_score < 60.0:
            acl_factors.append("Stiff Ground Impact Landing (< 35deg initial knee flexion)")
            acl_score += 25.0

        if symmetry_score < 85.0:
            acl_factors.append(f"Bilateral Deceleration Asymmetry ({100 - symmetry_score:.1f}%)")
            acl_score += 15.0

        if "acl" in history_text or "knee" in history_text:
            acl_factors.append("Prior history of Knee/Ligament trauma")
            acl_score += 20.0

        acl_score = min(98.0, acl_score)
        categories["acl_risk"] = {
            "category_name": "ACL Injury Risk",
            "risk_score": round(acl_score, 1),
            "probability": round(acl_score / 100.0, 2),
            "risk_level": self._level(acl_score),
            "primary_factors": acl_factors or ["Slight valgus within acceptable baseline range"],
            "description": "High anterior cruciate ligament strain generated during plant-and-cut or jump landing."
        }

        # 2. Hamstring Injury Risk
        # Biomarkers: Pelvic tilt/drop, overstriding, asymmetry, previous hamstring strain
        hamstring_factors = []
        hamstring_score = 12.0
        if pelvic_drop >= 4.0:
            hamstring_factors.append(f"Excessive Anterior Pelvic Obliquity ({pelvic_drop:.1f}deg)")
            hamstring_score += 30.0
        if symmetry_score < 82.0:
            hamstring_factors.append("Eccentric hamstring deceleration asymmetry")
            hamstring_score += 25.0
        if "hamstring" in history_text:
            hamstring_factors.append("Previous hamstring strain recurrence vulnerability")
            hamstring_score += 35.0
        if acwr > 1.35:
            hamstring_factors.append("High acute sprint fatigue loading")
            hamstring_score += 15.0

        hamstring_score = min(96.0, hamstring_score)
        categories["hamstring_risk"] = {
            "category_name": "Hamstring Injury Risk",
            "risk_score": round(hamstring_score, 1),
            "probability": round(hamstring_score / 100.0, 2),
            "risk_level": self._level(hamstring_score),
            "primary_factors": hamstring_factors or ["Balanced bilateral hamstring load during extension"],
            "description": "Risk of eccentric myofibrillar strain during rapid terminal swing or high-speed deceleration."
        }

        # 3. Ankle Sprain Risk
        # Biomarkers: Landing stiffness, lateral sway, high G impact
        ankle_factors = []
        ankle_score = 10.0
        if force_g >= 3.0:
            ankle_factors.append(f"Elevated Ground Reaction Force Impact ({force_g:.1f}G)")
            ankle_score += 30.0
        if trunk_lean >= 10.0:
            ankle_factors.append("Lateral center-of-mass displacement over lateral foot margin")
            ankle_score += 25.0
        if "ankle" in history_text or "sprain" in history_text:
            ankle_factors.append("Prior ankle ligament laxity history")
            ankle_score += 25.0

        ankle_score = min(95.0, ankle_score)
        categories["ankle_sprain_risk"] = {
            "category_name": "Ankle Sprain Risk",
            "risk_score": round(ankle_score, 1),
            "probability": round(ankle_score / 100.0, 2),
            "risk_level": self._level(ankle_score),
            "primary_factors": ankle_factors or ["Stable subtalar neutral alignment"],
            "description": "Lateral inversion stress and talocrural joint instability during ground contact."
        }

        # 4. Shoulder Injury Risk
        # Biomarkers: Upper limb asymmetry or sport profile
        shoulder_factors = []
        sport = str(athlete_profile.get("sport_type", "")).lower()
        shoulder_score = 10.0
        if "throw" in sport or "tennis" in sport or "baseball" in sport or "volleyball" in sport:
            shoulder_score += 25.0
            shoulder_factors.append("High overhead repetitive volume sport profile")
        if "shoulder" in history_text or "rotator" in history_text:
            shoulder_score += 35.0
            shoulder_factors.append("Historical rotator cuff or labral irritation")
        if trunk_lean > 12.0:
            shoulder_score += 15.0
            shoulder_factors.append("Kinetic chain trunk leak transmitting compensatory torque to shoulder")

        shoulder_score = min(92.0, shoulder_score)
        categories["shoulder_risk"] = {
            "category_name": "Shoulder Injury Risk",
            "risk_score": round(shoulder_score, 1),
            "probability": round(shoulder_score / 100.0, 2),
            "risk_level": self._level(shoulder_score),
            "primary_factors": shoulder_factors or ["Shoulder girdle kinematic parameters nominal"],
            "description": "Glenohumeral joint shear and impingement vulnerability during kinetic transmission."
        }

        # 5. Lower Back Injury Risk
        # Biomarkers: Excessive lateral trunk lean, lumbar shear, pelvic asymmetry
        back_factors = []
        back_score = 15.0
        if trunk_lean >= 10.0:
            back_factors.append(f"Excessive Lateral Trunk Lean ({trunk_lean:.1f}deg)")
            back_score += 40.0
        elif trunk_lean >= 6.0:
            back_factors.append(f"Moderate trunk lateral tilt ({trunk_lean:.1f}deg)")
            back_score += 20.0
        if pelvic_drop >= 3.5:
            back_factors.append("Pelvic unleveling causing unilateral lumbar facet compression")
            back_score += 25.0
        if "back" in history_text or "lumbar" in history_text:
            back_factors.append("Prior lumbar paraspinal or disc episode")
            back_score += 25.0

        back_score = min(96.0, back_score)
        categories["lower_back_risk"] = {
            "category_name": "Lower Back Injury Risk",
            "risk_score": round(back_score, 1),
            "probability": round(back_score / 100.0, 2),
            "risk_level": self._level(back_score),
            "primary_factors": back_factors or ["Neutral spine orientation maintained"],
            "description": "Lumbopelvic shear stress and core anti-rotation breakdown under dynamic load."
        }

        # 6. Overuse Injury Risk
        # Biomarkers: ACWR > 1.4, cumulative fatigue drift, high weekly load
        overuse_factors = []
        overuse_score = 15.0
        if acwr >= 1.45:
            overuse_factors.append(f"Critical Acute-to-Chronic Workload Ratio ({acwr:.2f} > 1.45)")
            overuse_score += 45.0
        elif acwr >= 1.3:
            overuse_factors.append(f"Elevated Acute-to-Chronic Workload Ratio ({acwr:.2f})")
            overuse_score += 25.0

        fatigue_score = weighted_scores.get("fatigue_indicator_score", 10.0)
        if fatigue_score >= 40.0:
            overuse_factors.append(f"High kinematic fatigue drift ({fatigue_score:.1f}/100)")
            overuse_score += 30.0

        if athlete_profile.get("training_load", 12.0) > 18.0:
            overuse_factors.append("High cumulative weekly training volume (> 18 hrs/wk)")
            overuse_score += 15.0

        overuse_score = min(98.0, overuse_score)
        categories["overuse_risk"] = {
            "category_name": "Overuse Injury Risk",
            "risk_score": round(overuse_score, 1),
            "probability": round(overuse_score / 100.0, 2),
            "risk_level": self._level(overuse_score),
            "primary_factors": overuse_factors or ["Training workload within progressive adaptation sweet spot"],
            "description": "Microtrauma accumulation exceeding tissue remodeling rate due to training load spikes."
        }

        return categories

    def _level(self, score: float) -> str:
        if score <= 30.0:
            return "Low Risk"
        elif score <= 60.0:
            return "Moderate Risk"
        elif score <= 85.0:
            return "High Risk"
        return "Critical Risk"
