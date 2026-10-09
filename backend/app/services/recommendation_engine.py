from typing import Dict, Any, List

class CorrectiveRecommendationEngine:
    """
    Corrective Recommendation Engine generating targeted biomechanical interventions:
    - Exercise recommendations (sets, reps, coaching cues)
    - Mobility improvement suggestions
    - Strengthening recommendations
    - Recovery planning
    - Training modification suggestions
    """

    def generate_recommendations(
        self,
        biomechanics: Dict[str, Any],
        category_risks: Dict[str, Any],
        risk_category: str
    ) -> Dict[str, Any]:
        acl_risk = category_risks.get("acl_risk", {})
        hamstring_risk = category_risks.get("hamstring_risk", {})
        back_risk = category_risks.get("lower_back_risk", {})
        ankle_risk = category_risks.get("ankle_sprain_risk", {})
        overuse_risk = category_risks.get("overuse_risk", {})

        exercises = []
        mobility_suggestions = []
        strengthening_plan = []
        recovery_planning = []
        training_modifications = []

        # 1. ACL / Knee Valgus Interventions
        if acl_risk.get("risk_level") in ["High", "Critical"] or biomechanics.get("knee_valgus_left_max", 0) > 12.0 or biomechanics.get("knee_valgus_right_max", 0) > 12.0:
            exercises.append({
                "name": "Banded Clamshells & Monster Walks",
                "target_area": "Gluteus Medius & Hip External Rotators",
                "sets": "3 sets",
                "reps": "15 reps / 20 steps",
                "frequency": "4x / week",
                "difficulty": "Intermediate",
                "equipment": "Resistance Band",
                "coaching_cues": [
                    "Keep pelvis neutral without backward rotation",
                    "Drive knee outward against band tension to activate gluteus medius",
                    "Do not let knees collapse inward during walking strides"
                ]
            })
            exercises.append({
                "name": "Drop Jump Soft-Landing Progression",
                "target_area": "Eccentric Quad Control & Knee Deceleration",
                "sets": "3 sets",
                "reps": "6 reps",
                "frequency": "3x / week",
                "difficulty": "Advanced",
                "equipment": "30cm Plyo Box",
                "coaching_cues": [
                    "Land toe-to-heel quietly ('like a ninja')",
                    "Achieve at least 60° knee flexion upon ground contact",
                    "Keep knees directly tracking over 2nd toe, preventing valgus inward snap"
                ]
            })
            strengthening_plan.append("Targeted Gluteus Medius / Minimus isometric holds and single-leg Romanian deadlifts (RDL).")
            mobility_suggestions.append("Ankle dorsiflexion mobility drill (knee-to-wall test > 10cm required to reduce compensatory knee collapse).")

        # 2. Hamstring Interventions
        if hamstring_risk.get("risk_level") in ["High", "Critical"]:
            exercises.append({
                "name": "Nordic Hamstring Curls (Assisted/Eccentric)",
                "target_area": "Biceps Femoris & Semitendinosus Eccentric Strength",
                "sets": "3 sets",
                "reps": "5 reps",
                "frequency": "2x / week",
                "difficulty": "Advanced",
                "equipment": "Ankle Anchor or Partner",
                "coaching_cues": [
                    "Maintain completely straight torso and hips locked in extension",
                    "Control forward fall for 4 full seconds before soft push-off",
                    "Substantially reduces eccentric hamstring strain incidence by >50%"
                ]
            })
            mobility_suggestions.append("Dynamic leg swings and active hamstring flossing with neural glide.")
            strengthening_plan.append("High-speed eccentric hamstring bridging on stability ball or sliders.")

        # 3. Lower Back / Trunk Lean Interventions
        if back_risk.get("risk_level") in ["High", "Critical"] or biomechanics.get("trunk_lean_lateral_max", 0) > 8.0:
            exercises.append({
                "name": "Half-Kneeling Pallof Press with Overhead Raise",
                "target_area": "Core Anti-Rotation & Lumbopelvic Lateral Stabilizers",
                "sets": "3 sets",
                "reps": "10 reps each side",
                "frequency": "3x / week",
                "difficulty": "Intermediate",
                "equipment": "Cable Machine or Resistance Band",
                "coaching_cues": [
                    "Keep ribcage pulled down and pelvis squared forward",
                    "Resist rotational pull of cable without leaning laterally",
                    "Exhale firmly through each repetition"
                ]
            })
            mobility_suggestions.append("Thoracic spine extension foam roller mobilizing and 90/90 hip flow.")
            strengthening_plan.append("Suitcase carries and side plank with leg elevation.")

        # 4. Ankle Stability Interventions
        if ankle_risk.get("risk_level") in ["High", "Critical"]:
            exercises.append({
                "name": "Single-Leg Balance with Star Excursion Reach",
                "target_area": "Proprioception & Peroneal Joint Stabilizers",
                "sets": "3 sets",
                "reps": "8 reaches / leg",
                "frequency": "4x / week",
                "difficulty": "Beginner to Intermediate",
                "equipment": "Balance Pad / Airex",
                "coaching_cues": [
                    "Maintain stable tripod foot contact (big toe, pinky toe, heel)",
                    "Avoid lateral ankle inversion roll during perturbation"
                ]
            })
            mobility_suggestions.append("Subtalar joint traction and talocrural mobilization with resistance band.")

        # Default foundational baseline exercise if list is small
        if len(exercises) < 3:
            exercises.append({
                "name": "Single-Leg Isometric Hip Thrust",
                "target_area": "Posterior Chain Symmetry & Hip Extension",
                "sets": "3 sets",
                "reps": "30 sec hold / side",
                "frequency": "3x / week",
                "difficulty": "Intermediate",
                "equipment": "Bench / Mat",
                "coaching_cues": [
                    "Drive through heel to full hip extension",
                    "Keep anterior superior iliac spines level with horizon"
                ]
            })
            strengthening_plan.append("Progressive multi-planar hip and core stability integration.")

        # Recovery Planning
        if risk_category in ["High Risk", "Critical Risk"]:
            recovery_planning.extend([
                "Schedule 48-hour deload from high-velocity cutting, sprinting, and plyometric drills.",
                "Implement 20-minute post-session contrast water therapy (cold plunge 10°C / hot shower) or pneumatic compression boots.",
                "Ensure target sleep duration minimum 8.5 hours with sleep hygiene protocol to accelerate collagen synthesis.",
                "Daily subjective fatigue, soreness, and resting heart rate variability (HRV) readiness tracking."
            ])
        else:
            recovery_planning.extend([
                "Maintain standard 24-48h recovery cycle between high-load training sessions.",
                "Incorporate 10-15 minute cool-down dynamic mobility routine after training.",
                "Target 8 hours of restorative sleep and balanced hydration."
            ])

        # Training Modifications
        if overuse_risk.get("risk_level") in ["High", "Critical"] or risk_category == "Critical Risk":
            training_modifications.extend([
                "Reduce acute high-speed running and change-of-direction volume by 30% for the next 7-10 days.",
                "Substitute sprint intervals with low-impact cardiovascular work (Wattbike or swimming) to deload joint structures.",
                "Perform all jump/landing sessions on shock-absorbing surfaces (sprung floor or grass) under video feedback.",
                "Cap weekly training load to lower Acute:Chronic Workload Ratio back into the 0.9 - 1.2 optimal corridor."
            ])
        elif risk_category == "High Risk":
            training_modifications.extend([
                "Decrease high-intensity deceleration volume by 15-20% until valgus angles stabilize below 10°.",
                "Add 15 minutes of pre-activation neuromuscular warm-up (FIFA 11+ inspired protocol) prior to every team drill.",
                "Monitor jumping volume via GPS/accelerometer load sensors."
            ])
        else:
            training_modifications.extend([
                "Continue current training microcycle with progressive overload.",
                "Integrate 10-minute FIFA 11+ neuromuscular injury prevention warm-up twice weekly."
            ])

        return {
            "exercises": exercises,
            "mobility_suggestions": mobility_suggestions,
            "strengthening_plan": strengthening_plan,
            "recovery_planning": recovery_planning,
            "training_modifications": training_modifications
        }
