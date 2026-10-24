from typing import List, Dict, Any


CORRECTIVE_EXERCISE_LIBRARY = {
    "VALGUS_ACL": [
        {
            "name": "Banded Monster Walks & Clamshells",
            "category": "Hip Abductor Strengthening",
            "target": "Gluteus Medius & Minimus",
            "frequency": "3 sets x 15 reps (daily warm-up)",
            "purpose": "Strengthens lateral hip stabilizers to prevent inward dynamic knee valgus collapse during cutting and landing.",
            "difficulty": "Beginner to Intermediate"
        },
        {
            "name": "Single-Leg Romanian Deadlift (RDL)",
            "category": "Posterior Chain & Balance",
            "target": "Hamstrings, Gluteus Maximus, Ankle Stabilizers",
            "frequency": "3 sets x 8 reps per leg (3x weekly)",
            "purpose": "Improves single-leg eccentric stability and eliminates bilateral hip hinge asymmetry.",
            "difficulty": "Intermediate"
        },
        {
            "name": "Drop Jump to Soft Landings (Mirror Cues)",
            "category": "Neuromuscular Re-Education",
            "target": "Knee-Ankle Kinematic Alignment",
            "frequency": "4 sets x 5 reps (pre-training)",
            "purpose": "Trains shock absorption with knee flexion > 45° to eliminate stiff-legged high-impact ground reaction forces.",
            "difficulty": "Advanced"
        }
    ],
    "HAMSTRING_ASYMMETRY": [
        {
            "name": "Nordic Hamstring Curls (Eccentric)",
            "category": "Eccentric Hamstring Conditioning",
            "target": "Biceps Femoris & Semitendinosus",
            "frequency": "3 sets x 6 reps (2x weekly)",
            "purpose": "Gold-standard preventative drill shown to reduce acute hamstring strain recurrence by over 50%.",
            "difficulty": "Advanced"
        },
        {
            "name": "Swiss Ball Hamstring Curls (Bilateral to Unilateral)",
            "category": "Dynamic Knee Flexion",
            "target": "Hamstring Complex & Pelvic Control",
            "frequency": "3 sets x 12 reps (3x weekly)",
            "purpose": "Balances bilateral strength differences and builds endurance at extended muscle lengths.",
            "difficulty": "Intermediate"
        }
    ],
    "ANKLE_INSTABILITY": [
        {
            "name": "Single-Leg Balance with Perturbations (Airex/Bosu)",
            "category": "Proprioceptive Training",
            "target": "Peroneal Longus/Brevis & Calcaneal Stabilizers",
            "frequency": "3 sets x 45 seconds per side (daily)",
            "purpose": "Restores mechanoreceptor feedback to resist sudden lateral inversion during rapid direction changes.",
            "difficulty": "Intermediate"
        },
        {
            "name": "Eccentric Calf Drops on Ledge",
            "category": "Achilles & Dorsiflexion Mobility",
            "target": "Gastrocnemius, Soleus, Achilles Tendon",
            "frequency": "3 sets x 15 reps (daily)",
            "purpose": "Expands closed-chain dorsiflexion range of motion, reducing compensatory knee strain.",
            "difficulty": "Beginner"
        }
    ],
    "POSTURE_TRUNK": [
        {
            "name": "Pallof Press with Anti-Rotation Hold",
            "category": "Core Anti-Rotation & Posture",
            "target": "Transverse Abdominis, Obliques",
            "frequency": "3 sets x 10 reps with 3s hold (3x weekly)",
            "purpose": "Resists lateral trunk lean and pelvic tilt during athletic decelerations.",
            "difficulty": "Intermediate"
        },
        {
            "name": "Bird-Dog Isometric Holds",
            "category": "Spinal Alignment",
            "target": "Erector Spinae & Contralateral Glutes",
            "frequency": "3 sets x 8 reps per side (daily)",
            "purpose": "Prevents excessive forward trunk lean during deep squat and acceleration phases.",
            "difficulty": "Beginner"
        }
    ],
    "PATELLAR_TENDON": [
        {
            "name": "Decline Board Eccentric Single-Leg Squats",
            "category": "Patellar Tendon Loading",
            "target": "Patellar Tendon & Quadriceps Complex",
            "frequency": "3 sets x 15 reps (2x daily)",
            "purpose": "Clinical gold standard for jumper's knee: stimulates patellar tendon collagen remodeling under eccentric loads.",
            "difficulty": "Intermediate"
        },
        {
            "name": "Spanish Squats with Heavy Rigid Band",
            "category": "Isometric Quadriceps Deloading",
            "target": "Infrapatellar Tendon & Vastus Medialis",
            "frequency": "5 holds x 45 seconds (pre-activity)",
            "purpose": "Provides proven analgesic pain relief and reduces high-impact patellar landing strain.",
            "difficulty": "Beginner"
        }
    ]
}


class RecommendationEngine:
    """
    Generates prescriptive exercise regimens and load management workflows
    based on predicted injury risks and biomechanical anomalies.
    """

    def generate_recommendations(
        self,
        risk_breakdown: Dict[str, float],
        training_load: float,
        anomalies: List[str]
    ) -> Dict[str, Any]:
        prescribed_exercises: List[Dict[str, Any]] = []
        protocols_added = set()

        acl_risk = risk_breakdown.get("acl_risk", 0.0)
        hamstring_risk = risk_breakdown.get("hamstring_risk", 0.0)
        ankle_risk = risk_breakdown.get("ankle_risk", 0.0)
        patellar_risk = risk_breakdown.get("patellar_risk", 0.0)

        # Rank injury categories by severity so highest risk protocols appear first
        ranked_categories = sorted([
            ("HAMSTRING_ASYMMETRY", hamstring_risk),
            ("VALGUS_ACL", acl_risk),
            ("PATELLAR_TENDON", patellar_risk),
            ("ANKLE_INSTABILITY", ankle_risk)
        ], key=lambda x: x[1], reverse=True)

        for cat, score in ranked_categories:
            if cat == "HAMSTRING_ASYMMETRY" and (score >= 35.0 or any("asymmetry" in a.lower() or "hamstring" in a.lower() for a in anomalies)):
                if "HAMSTRING_ASYMMETRY" not in protocols_added:
                    prescribed_exercises.extend(CORRECTIVE_EXERCISE_LIBRARY["HAMSTRING_ASYMMETRY"])
                    protocols_added.add("HAMSTRING_ASYMMETRY")
            elif cat == "VALGUS_ACL" and (score >= 35.0 or any("valgus" in a.lower() or "acl" in a.lower() for a in anomalies)):
                if "VALGUS_ACL" not in protocols_added:
                    prescribed_exercises.extend(CORRECTIVE_EXERCISE_LIBRARY["VALGUS_ACL"])
                    protocols_added.add("VALGUS_ACL")
            elif cat == "PATELLAR_TENDON" and (score >= 35.0 or any("patellar" in a.lower() or "landing" in a.lower() or "impact" in a.lower() for a in anomalies)):
                if "PATELLAR_TENDON" not in protocols_added:
                    prescribed_exercises.extend(CORRECTIVE_EXERCISE_LIBRARY["PATELLAR_TENDON"])
                    protocols_added.add("PATELLAR_TENDON")
            elif cat == "ANKLE_INSTABILITY" and (score >= 35.0 or any("ankle" in a.lower() for a in anomalies)):
                if "ANKLE_INSTABILITY" not in protocols_added:
                    prescribed_exercises.extend(CORRECTIVE_EXERCISE_LIBRARY["ANKLE_INSTABILITY"])
                    protocols_added.add("ANKLE_INSTABILITY")

        # Target Postural / Trunk Lean if flagged
        if any("trunk" in a.lower() for a in anomalies):
            if "POSTURE_TRUNK" not in protocols_added:
                prescribed_exercises.extend(CORRECTIVE_EXERCISE_LIBRARY["POSTURE_TRUNK"])
                protocols_added.add("POSTURE_TRUNK")

        # Default maintenance if all scores are low
        if not prescribed_exercises:
            prescribed_exercises.extend([
                CORRECTIVE_EXERCISE_LIBRARY["VALGUS_ACL"][0],
                CORRECTIVE_EXERCISE_LIBRARY["HAMSTRING_ASYMMETRY"][0],
                CORRECTIVE_EXERCISE_LIBRARY["POSTURE_TRUNK"][0]
            ])

        # Load Management Protocols
        if training_load >= 80.0:
            load_action = "CRITICAL DELOAD: Reduce acute weekly training volume by 20-30%. Prioritize low-impact aerobic recovery and sleep restoration."
            recovery_status = "DELOAD_REQUIRED"
        elif training_load >= 70.0:
            load_action = "MODERATE LOAD MONITORING: Maintain current training volume. Enforce mandatory 48h spacing between high-intensity plyometric sessions."
            recovery_status = "OPTIMAL_LOAD"
        else:
            load_action = "PROGRESSIVE OVERLOAD APPROVED: Movement mechanics are safe to incrementally increase training volume by 5-10%."
            recovery_status = "READY_FOR_PROGRESSION"

        recovery_tips = [
            "Implement the FIFA 11+ neuromuscular warm-up sequence for 15 minutes prior to sport activity.",
            "Maintain sleep hygiene (> 8 hours) to support muscle protein synthesis and neural recovery.",
            "Conduct post-session foam rolling focused on adductors, tensor fasciae latae, and hamstrings."
        ]

        return {
            "prescribed_exercises": prescribed_exercises,
            "training_load_recommendation": load_action,
            "recovery_status": recovery_status,
            "recovery_guidelines": recovery_tips
        }
