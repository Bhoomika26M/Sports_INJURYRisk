from typing import Dict, Any, List

class RiskScoringEngine:
    """
    Weighted Scoring Engine implementing Page 6 of the PDF:
    Injury Risk Score =
      Biomechanical Deviations (35%)
    + Historical Injury Factors (20%)
    + Movement Asymmetry (20%)
    + Training Load Indicators (15%)
    + Fatigue Indicators (10%)
    """

    def compute_scores(
        self,
        biomechanics: Dict[str, Any],
        athlete_profile: Dict[str, Any],
        fatigue_drift_pct: float
    ) -> Dict[str, Any]:
        # 1. Biomechanical Deviations (35% weight)
        # Based on knee valgus, trunk lean, and landing stiffness
        max_valgus = max(
            biomechanics.get("knee_valgus_left_max", 0.0),
            biomechanics.get("knee_valgus_right_max", 0.0)
        )
        trunk_lean = biomechanics.get("trunk_lean_lateral_max", 0.0)
        landing_score = biomechanics.get("landing_mechanics_score", 80.0)

        # Scale biomechanical deviation from 0 to 100
        valgus_penalty = min(60.0, (max_valgus / 20.0) * 60.0)
        lean_penalty = min(25.0, (trunk_lean / 15.0) * 25.0)
        landing_penalty = (100.0 - landing_score) * 0.25
        biomechanical_deviation_score = round(min(100.0, valgus_penalty + lean_penalty + landing_penalty), 1)

        # 2. Historical Injury Factors (20% weight)
        history = athlete_profile.get("injury_history", [])
        if not history:
            historical_injury_score = 10.0
        else:
            # Score based on number and severity of past injuries
            score = 15.0
            for item in history:
                sev = str(item.get("severity", "")).lower()
                status = str(item.get("status", "")).lower()
                if "severe" in sev or "surgical" in sev:
                    score += 35.0
                elif "moderate" in sev:
                    score += 20.0
                else:
                    score += 10.0
                if "ongoing" in status or "vulnerable" in status:
                    score += 15.0
            historical_injury_score = round(min(100.0, score), 1)

        # 3. Movement Asymmetry (20% weight)
        symmetry_score = biomechanics.get("movement_symmetry_score", 90.0)
        # Asymmetry is 100 - symmetry score, scaled up
        asymmetry_score = round(min(100.0, max(0.0, (100.0 - symmetry_score) * 3.5)), 1)

        # 4. Training Load Indicators (15% weight)
        # Normal ACWR (Acute:Chronic Workload Ratio) safe sweet spot is 0.8 - 1.3
        # ACWR > 1.5 represents the "danger zone"
        acwr = athlete_profile.get("acwr", 1.15)
        training_hrs = athlete_profile.get("training_load", 12.0)
        if acwr <= 1.2:
            training_load_score = 15.0 + max(0.0, (training_hrs - 15.0) * 2.0)
        elif acwr <= 1.4:
            training_load_score = 45.0 + (acwr - 1.2) * 100.0
        else:
            training_load_score = 75.0 + min(25.0, (acwr - 1.4) * 125.0)
        training_load_score = round(min(100.0, training_load_score), 1)

        # 5. Fatigue Indicators (10% weight)
        # Driven by fatigue drift percentage
        fatigue_indicator_score = round(min(100.0, max(10.0, fatigue_drift_pct * 3.2)), 1)

        # Weighted Total Score:
        injury_risk_score = round(
            (0.35 * biomechanical_deviation_score) +
            (0.20 * historical_injury_score) +
            (0.20 * asymmetry_score) +
            (0.15 * training_load_score) +
            (0.10 * fatigue_indicator_score),
            1
        )

        # Categorize into 4 PDF Risk Categories
        if injury_risk_score <= 30.0:
            risk_category = "Low Risk"
        elif injury_risk_score <= 60.0:
            risk_category = "Moderate Risk"
        elif injury_risk_score <= 85.0:
            risk_category = "High Risk"
        else:
            risk_category = "Critical Risk"

        # Additional Scores required by PDF:
        movement_quality_score = round(max(10.0, 100.0 - (biomechanical_deviation_score * 0.6 + asymmetry_score * 0.4)), 1)
        biomechanical_efficiency_score = round(max(15.0, (symmetry_score * 0.5) + (landing_score * 0.3) + ((100.0 - max_valgus * 3.0) * 0.2)), 1)
        fatigue_risk_score = fatigue_indicator_score
        overall_athlete_health_score = round(max(10.0, 100.0 - (injury_risk_score * 0.7 + (100.0 - movement_quality_score) * 0.3)), 1)

        return {
            "overall_injury_risk_score": injury_risk_score,
            "risk_category": risk_category,
            "biomechanical_deviation_score": biomechanical_deviation_score,
            "historical_injury_factor_score": historical_injury_score,
            "movement_asymmetry_score": asymmetry_score,
            "training_load_indicator_score": training_load_score,
            "fatigue_indicator_score": fatigue_indicator_score,
            "movement_quality_score": movement_quality_score,
            "biomechanical_efficiency_score": biomechanical_efficiency_score,
            "fatigue_risk_score": fatigue_risk_score,
            "overall_athlete_health_score": overall_athlete_health_score
        }
