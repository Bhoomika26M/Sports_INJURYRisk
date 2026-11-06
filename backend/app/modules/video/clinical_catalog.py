"""Clinical Biomechanical Corrective Exercise Catalog.

Curated, evidence-based corrective exercise protocols and technical form cues
for sports movement screening and injury risk mitigation.
Follows /docs/SCIENCE_CONSTRAINTS.md — provides actionable neuromuscular training
and biomechanical offloading protocols without pseudo-medical probability claims.
"""

from typing import Any


CORRECTIVE_EXERCISE_CATALOG: dict[str, dict[str, Any]] = {
    "knee_valgus": {
        "title": "Frontal Plane Knee Valgus Collapse Mitigation",
        "primary_fault": "Dynamic medial knee displacement and femoral internal rotation during eccentric loading.",
        "clinical_rationale": (
            "Knee valgus collapse magnifies lateral compartment compressive shear and anterior cruciate ligament "
            "(ACL) tensile strain. Neuromuscular activation of the gluteus medius and external hip rotators restores "
            "frontal-plane knee alignment over the second toe."
        ),
        "verbal_cues": [
            "Spread the floor apart through the outside edges of your feet.",
            "Keep kneecaps tracking in line with your second and third toes.",
            "Screw your hips into the ground to create external rotation torque."
        ],
        "prescribed_exercises": [
            {
                "name": "Banded Spanish Squats",
                "target_muscles": ["Quadriceps (VMO)", "Gluteus Medius", "Patellar Tendon"],
                "frequency": "3x / week",
                "sets": 3,
                "reps": "12 reps",
                "tempo": "3-2-1",
                "notes": "Loop heavy band behind knees; maintain vertical shin angle and press knees gently into band."
            },
            {
                "name": "Banded Clamshells with Lateral Abduction",
                "target_muscles": ["Gluteus Medius", "Deep Hip External Rotators"],
                "frequency": "4x / week",
                "sets": 3,
                "reps": "15 reps / side",
                "tempo": "2-1-2",
                "notes": "Keep pelvis strictly perpendicular to ground; avoid rolling lower back backward."
            },
            {
                "name": "Single-Leg Romanian Deadlift with Wall Tap",
                "target_muscles": ["Contralateral Gluteus Medius", "Hamstrings", "Ankle Stabilizers"],
                "frequency": "3x / week",
                "sets": 3,
                "reps": "8 reps / side",
                "tempo": "3-1-1",
                "notes": "Hinge from hip without letting stance knee buckle inward."
            }
        ]
    },
    "excessive_trunk_lean": {
        "title": "Trunk-Hip Decoupling & Anterior Shear Offloading",
        "primary_fault": "Forward torso inclination exceeding 35° relative to vertical plumb line.",
        "clinical_rationale": (
            "Excessive forward trunk lean increases the lumbar external moment arm and anterior vertebral shear stress, "
            "frequently compensating for restricted ankle dorsiflexion or weak thoracic extensor musculature."
        ),
        "verbal_cues": [
            "Proud chest — show the logo on your shirt to the wall ahead.",
            "Drive your knees forward while keeping heels firmly glued to the floor.",
            "Think of sitting straight down between your hips rather than reaching backward."
        ],
        "prescribed_exercises": [
            {
                "name": "Heel-Elevated Goblet Squat",
                "target_muscles": ["Quadriceps", "Thoracic Erectors", "Soleus"],
                "frequency": "3x / week",
                "sets": 4,
                "reps": "10 reps",
                "tempo": "3-1-1",
                "notes": "Elevate heels 1-2 inches on small plates; hold weight close to chest to reinforce vertical spine."
            },
            {
                "name": "Kneeling Ankle Dorsiflexion Mobilization",
                "target_muscles": ["Gastrocnemius-Soleus Complex", "Talocrural Joint Capsule"],
                "frequency": "Daily",
                "sets": 3,
                "reps": "10 pulses / side",
                "tempo": "2-2-1",
                "notes": "Drive knee forward 3 inches past toes while keeping heel flat on ground."
            },
            {
                "name": "Bird-Dog Core Stabilization",
                "target_muscles": ["Multifidus", "Erector Spinae", "Gluteus Maximus"],
                "frequency": "4x / week",
                "sets": 3,
                "reps": "8 reps / side",
                "tempo": "3-3-1",
                "notes": "Extend opposing arm and leg without arching lumbar spine or tilting hips."
            }
        ]
    },
    "asymmetry": {
        "title": "Bilateral Kinetic Symmetry Restoration",
        "primary_fault": "Inter-limb weight transfer disparity exceeding 15% during bilateral loading or propulsion.",
        "clinical_rationale": (
            "Bilateral kinetic asymmetry places disproportionate eccentric demand on the favored limb while "
            "underloading the contralateral kinetic chain, elevating overuse injury risk."
        ),
        "verbal_cues": [
            "Distribute bodyweight 50/50 through both feet at the turnaround point.",
            "Push the floor away symmetrically with both legs simultaneously."
        ],
        "prescribed_exercises": [
            {
                "name": "Bulgarian Split Squats (Contralateral Loading)",
                "target_muscles": ["Unilateral Gluteals", "Quadriceps", "Adductor Magnus"],
                "frequency": "3x / week",
                "sets": 3,
                "reps": "8 reps / leg",
                "tempo": "3-1-1",
                "notes": "Focus on driving straight down and up on the weaker limb with full foot tripod contact."
            },
            {
                "name": "Single-Leg Box Step-Downs",
                "target_muscles": ["Eccentric Quadriceps", "Pelvic Stabilizers"],
                "frequency": "3x / week",
                "sets": 3,
                "reps": "10 reps / leg",
                "tempo": "4-1-1",
                "notes": "Step down slowly from 6-inch step; lightly tap heel to floor without transferring weight."
            }
        ]
    },
    "stiff_landing": {
        "title": "Deceleration Compliance & Impact Force Dissipation",
        "primary_fault": "Minimal knee flexion (<60°) and rigid ankle contact upon ground landing.",
        "clinical_rationale": (
            "Stiff landings dramatically compress deceleration time, elevating peak vertical ground reaction forces "
            "(vGRF) up to 8–10x body weight and subjecting the passive musculoskeletal structures to abrupt shock."
        ),
        "verbal_cues": [
            "Land like a ninja — make zero sound when your feet touch the floor.",
            "Catch your weight like an accordion, sinking smoothly into your hips and knees.",
            "Absorb force into your muscles, not your joints."
        ],
        "prescribed_exercises": [
            {
                "name": "Drop Freeze / Altitude Landings",
                "target_muscles": ["Eccentric Quadriceps", "Gluteals", "Gastrocnemius-Soleus"],
                "frequency": "2x / week",
                "sets": 4,
                "reps": "5 reps",
                "tempo": "1-3-0",
                "notes": "Step off 12-inch box; absorb immediately into a 90° athletic squat position and hold 3 seconds."
            },
            {
                "name": "Box Jumps with Soft Landing",
                "target_muscles": ["Triple Extensors (Hip, Knee, Ankle)"],
                "frequency": "2x / week",
                "sets": 3,
                "reps": "6 reps",
                "tempo": "Explosive",
                "notes": "Jump onto box landing in the exact same partial-squat depth as takeoff; step down gently."
            }
        ]
    },
    "optimal": {
        "title": "Optimal Movement Mechanics Maintenance",
        "primary_fault": "None. Balanced kinetic chain alignment, adequate depth, and controlled tempo.",
        "clinical_rationale": (
            "Movement patterns meet high-performance kinematic criteria with controlled frontal plane stability, "
            "adequate joint mobility, and balanced inter-limb symmetry."
        ),
        "verbal_cues": [
            "Maintain current movement rhythm and joint stacking.",
            "Focus on progressive progressive load or velocity while preserving form integrity."
        ],
        "prescribed_exercises": [
            {
                "name": "Full Kinetic Chain Warmup Protocol",
                "target_muscles": ["Hip Rotators", "Thoracic Spine", "Ankle Complex"],
                "frequency": "Pre-training",
                "sets": 2,
                "reps": "8 reps",
                "tempo": "Dynamic",
                "notes": "Continue standard multi-joint mobility and dynamic activation work."
            }
        ]
    }
}


def get_corrective_protocol_for_faults(fault_keys: list[str]) -> list[dict[str, Any]]:
    """Return prioritized corrective protocols based on detected biomechanical faults."""
    protocols = []
    seen = set()
    for key in fault_keys:
        if key in CORRECTIVE_EXERCISE_CATALOG and key not in seen:
            protocols.append(CORRECTIVE_EXERCISE_CATALOG[key])
            seen.add(key)
    if not protocols:
        protocols.append(CORRECTIVE_EXERCISE_CATALOG["optimal"])
    return protocols
