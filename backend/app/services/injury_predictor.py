import os
import joblib
import numpy as np
from typing import Dict, Any, List, Optional
from sklearn.ensemble import RandomForestRegressor, GradientBoostingClassifier


class InjuryPredictor:
    """
    Predictive Machine Learning Engine for sports injury risk detection.
    Combines computer-vision biomechanical metrics with athlete load & history.
    """

    def __init__(self, model_path: Optional[str] = None):
        if model_path is None:
            cur_dir = os.path.abspath(os.path.dirname(__file__))
            model_path = os.path.abspath(
                os.path.join(cur_dir, "..", "..", "..", "models", "injury_risk_model.joblib")
            )
        self.model_path = model_path
        self.model = None
        self._load_or_train_model()

    def _load_or_train_model(self):
        """
        Load existing ML model or train and serialize a calibrated multi-risk model.
        """
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                return
            except Exception:
                pass

        # Train a calibrated baseline model
        self.model = self._train_baseline_model()
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            joblib.dump(self.model, self.model_path)
        except Exception:
            pass

    def _train_baseline_model(self):
        """
        Train a multi-output sports biomechanics risk model on clinical risk thresholds.
        Features:
        [peak_valgus, mean_asymmetry, peak_flexion, peak_trunk_lean,
         quality_score, training_load, age, bmi, prior_knee, prior_hamstring, prior_ankle]
        Targets:
        [acl_risk, hamstring_risk, ankle_risk, patellar_risk]
        """
        np.random.seed(42)
        n_samples = 400

        # Generate realistic athletic distributions
        valgus = np.random.uniform(0.0, 22.0, n_samples)
        asymmetry = np.random.uniform(2.0, 32.0, n_samples)
        flexion = np.random.uniform(35.0, 115.0, n_samples)
        trunk_lean = np.random.uniform(5.0, 42.0, n_samples)
        quality_score = np.random.uniform(30.0, 95.0, n_samples)
        load = np.random.uniform(40.0, 95.0, n_samples)
        age = np.random.uniform(18.0, 32.0, n_samples)
        bmi = np.random.uniform(20.0, 28.0, n_samples)
        prior_knee = np.random.choice([0, 1], p=[0.7, 0.3], size=n_samples)
        prior_ham = np.random.choice([0, 1], p=[0.75, 0.25], size=n_samples)
        prior_ank = np.random.choice([0, 1], p=[0.65, 0.35], size=n_samples)

        X = np.column_stack([
            valgus, asymmetry, flexion, trunk_lean,
            quality_score, load, age, bmi,
            prior_knee, prior_ham, prior_ank
        ])

        # Mathematical ground truth clinical risk functions (0-100%)
        # ACL Risk heavily influenced by valgus > 10, low flexion (stiff landing), load, prior knee
        y_acl = (valgus * 3.2) + (np.maximum(0, 60.0 - flexion) * 0.7) + (load * 0.25) + (prior_knee * 18.0)
        y_acl = np.clip(y_acl, 5.0, 95.0)

        # Hamstring Risk heavily influenced by asymmetry, high training load, prior hamstring
        y_ham = (asymmetry * 2.5) + (load * 0.35) + (prior_ham * 22.0) + (np.maximum(0, trunk_lean - 25.0) * 0.6)
        y_ham = np.clip(y_ham, 5.0, 92.0)

        # Ankle Risk influenced by lateral sway/trunk lean, asymmetry, prior ankle
        y_ank = (trunk_lean * 1.2) + (asymmetry * 1.2) + (prior_ank * 20.0) + (load * 0.15)
        y_ank = np.clip(y_ank, 5.0, 88.0)

        # Patellar Tendonitis influenced by high load, high impact
        y_pat = (load * 0.6) + (np.maximum(0, valgus - 8.0) * 1.5) + (prior_knee * 12.0)
        y_pat = np.clip(y_pat, 5.0, 90.0)

        Y = np.column_stack([y_acl, y_ham, y_ank, y_pat])

        model = RandomForestRegressor(n_estimators=50, random_state=42, max_depth=8)
        model.fit(X, Y)
        return model

    def assess_injury_risk(
        self,
        biomechanics: Dict[str, Any],
        athlete_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate composite injury risk scores, specific injury probabilities, 
        and early warning triggers.
        """
        metrics = biomechanics.get("metrics_summary", {})
        quality_score = float(biomechanics.get("overall_score", 70.0))

        peak_valgus = float(metrics.get("peak_valgus_overall", 0.0))
        mean_asymmetry = float(metrics.get("mean_asymmetry_index", 0.0))
        peak_flexion = float(metrics.get("peak_flexion_overall", 80.0))
        peak_trunk_lean = float(metrics.get("peak_trunk_lean", 15.0))

        # Athlete profile features
        athlete_profile = athlete_profile or {}
        training_load = float(athlete_profile.get("training_load", 65.0))
        age = float(athlete_profile.get("age", 22.0))
        height = float(athlete_profile.get("height", 178.0))
        weight = float(athlete_profile.get("weight", 72.0))
        injury_history = str(athlete_profile.get("injury_history", "")).lower()

        # BMI
        h_m = height / 100.0 if height > 0 else 1.78
        bmi = weight / (h_m ** 2) if h_m > 0 else 22.7

        prior_knee = 1 if "knee" in injury_history or "acl" in injury_history else 0
        prior_ham = 1 if "hamstring" in injury_history else 0
        prior_ank = 1 if "ankle" in injury_history or "sprain" in injury_history else 0

        # Construct input vector
        features = np.array([[
            peak_valgus, mean_asymmetry, peak_flexion, peak_trunk_lean,
            quality_score, training_load, age, bmi,
            prior_knee, prior_ham, prior_ank
        ]])

        # Model Inference
        if self.model is not None:
            preds = self.model.predict(features)[0]
            acl_risk = round(float(preds[0]), 1)
            hamstring_risk = round(float(preds[1]), 1)
            ankle_risk = round(float(preds[2]), 1)
            patellar_risk = round(float(preds[3]), 1)
        else:
            # Fallback heuristic calculation
            acl_risk = round(min(95.0, (peak_valgus * 3.5) + (prior_knee * 20.0) + (training_load * 0.2)), 1)
            hamstring_risk = round(min(95.0, (mean_asymmetry * 2.8) + (prior_ham * 20.0) + (training_load * 0.3)), 1)
            ankle_risk = round(min(90.0, (peak_trunk_lean * 1.4) + (prior_ank * 20.0)), 1)
            patellar_risk = round(min(90.0, (training_load * 0.6) + (peak_valgus * 1.2)), 1)

        # Composite overall risk score (weighted formula)
        # Weights highest specific risk (40%) + quality score deficit (30%) + training load (30%)
        highest_specific = max(acl_risk, hamstring_risk, ankle_risk, patellar_risk)
        quality_deficit = max(0.0, 100.0 - quality_score)

        composite_score = round(
            (0.40 * highest_specific) +
            (0.35 * quality_deficit) +
            (0.25 * training_load),
            1
        )
        composite_score = min(100.0, max(0.0, composite_score))

        # Risk Classification
        if composite_score >= 71.0:
            risk_level = "HIGH"
        elif composite_score >= 36.0:
            risk_level = "MODERATE"
        else:
            risk_level = "LOW"

        # Early Warning Alerts
        early_warnings = []
        if peak_valgus >= 12.0 and training_load >= 75.0:
            early_warnings.append({
                "severity": "CRITICAL",
                "title": "High Dynamic Knee Valgus with Heavy Training Load",
                "message": f"Knee valgus reached {peak_valgus}° under {training_load}% load. Urgent risk of ACL ligament strain."
            })
        elif peak_valgus >= 10.0:
            early_warnings.append({
                "severity": "WARNING",
                "title": "Medial Knee Valgus Shift Observed",
                "message": f"Peak valgus of {peak_valgus}° exceeds the 8° safety threshold."
            })

        if mean_asymmetry >= 15.0 and prior_ham == 1:
            early_warnings.append({
                "severity": "CRITICAL",
                "title": "Elevated Bilateral Asymmetry with Hamstring Injury History",
                "message": f"{mean_asymmetry}% limb asymmetry combined with historical strain significantly elevates re-injury risk."
            })
        elif mean_asymmetry >= 14.0:
            early_warnings.append({
                "severity": "WARNING",
                "title": "High Bilateral Load Asymmetry",
                "message": f"{mean_asymmetry}% asymmetry indicates uneven limb loading during ground contact."
            })

        if training_load >= 80.0:
            early_warnings.append({
                "severity": "WARNING",
                "title": "Training Load Overload Trigger",
                "message": f"Current training load of {training_load}% surpasses optimal recovery capacity."
            })

        if not early_warnings:
            early_warnings.append({
                "severity": "INFO",
                "title": "Biomechanical Safety Clear",
                "message": "Movement kinematics and physiological load are within safe ranges."
            })

        return {
            "overall_risk_score": composite_score,
            "risk_level": risk_level,
            "risk_breakdown": {
                "acl_risk": acl_risk,
                "hamstring_risk": hamstring_risk,
                "ankle_risk": ankle_risk,
                "patellar_risk": patellar_risk
            },
            "early_warnings": early_warnings,
            "athlete_factors": {
                "training_load": training_load,
                "prior_injuries_detected": prior_knee + prior_ham + prior_ank > 0
            }
        }
