"""Corrective recommendation engine.

Maps detected issues to general corrective exercises, mobility work, strengthening,
recovery planning and training modifications. The output is decision support for
coaches and clinicians, not medical advice or a treatment plan.
"""

DISCLAIMER = (
    "Screening output only, not medical advice. High or critical results should be reviewed "
    "by a qualified physiotherapist or physician before training is changed."
)

# issue -> (title, category, exercises[(name, prescription, purpose)])
LIBRARY: dict[str, tuple[str, str, list[tuple[str, str, str]]]] = {
    "knee_valgus": (
        "Control knee alignment", "strengthening",
        [("Banded lateral walks", "3 x 12 steps each way", "Glute medius strength"),
         ("Single-leg squat to box with mirror cue", "3 x 8 each leg", "Knee-over-toe control"),
         ("Clamshells", "3 x 15 each side", "Hip external rotator activation")],
    ),
    "stiff_landing": (
        "Soften landings", "corrective",
        [("Drop landing with 'quiet feet' cue", "3 x 5", "Absorb force through hips and knees"),
         ("Box step-down, slow eccentric", "3 x 8 each leg", "Eccentric quadriceps control"),
         ("Hip hinge to squat pattern drill", "3 x 10", "Load hips as well as knees")],
    ),
    "trunk_control": (
        "Improve trunk control", "strengthening",
        [("Dead bug", "3 x 8 each side", "Anti-extension core control"),
         ("Side plank", "3 x 30 s each side", "Lateral trunk stability"),
         ("Pallof press", "3 x 10 each side", "Anti-rotation strength")],
    ),
    "hip_stability": (
        "Strengthen hip stabilisers", "strengthening",
        [("Single-leg glute bridge", "3 x 10 each leg", "Glute max and medius strength"),
         ("Side-lying hip abduction", "3 x 15 each side", "Pelvic stability"),
         ("Lateral step-down", "3 x 8 each leg", "Pelvic control under load")],
    ),
    "asymmetry": (
        "Balance left and right", "strengthening",
        [("Bulgarian split squat, start with weaker side", "3 x 8 each leg", "Even out unilateral strength"),
         ("Single-leg Romanian deadlift", "3 x 8 each leg", "Posterior chain symmetry"),
         ("Single-leg hop and stick", "3 x 5 each leg", "Landing symmetry")],
    ),
    "ankle_control": (
        "Ankle mobility and control", "mobility",
        [("Wall ankle dorsiflexion mobilisation", "3 x 10 each side", "Dorsiflexion range"),
         ("Calf raises, slow tempo", "3 x 12", "Calf-achilles strength"),
         ("Single-leg balance on unstable surface", "3 x 30 s each leg", "Ankle proprioception")],
    ),
    "balance": (
        "Improve balance", "corrective",
        [("Single-leg stance, eyes open then closed", "3 x 30 s each leg", "Postural control"),
         ("Y-balance reach practice", "3 x 5 each direction", "Dynamic balance"),
         ("Single-leg mini-squat", "3 x 8 each leg", "Control through range")],
    ),
    "shoulder_control": (
        "Shoulder stability", "strengthening",
        [("Band external rotation", "3 x 12 each arm", "Rotator cuff strength"),
         ("Prone Y-T-W raises", "2 x 10 each", "Scapular control"),
         ("Thoracic extension over foam roller", "2 x 10", "Thoracic mobility")],
    ),
    "stride_consistency": (
        "Running rhythm", "corrective",
        [("Metronome-paced running drills", "4 x 1 min", "Consistent cadence"),
         ("A-skips and B-skips", "3 x 20 m", "Running mechanics"),
         ("Strides at 80% effort", "4 x 60 m", "Rhythm at speed")],
    ),
    "posture": (
        "Posture and upper-body alignment", "mobility",
        [("Chin tucks", "3 x 10", "Neck alignment"),
         ("Wall angels", "2 x 10", "Shoulder and thoracic mobility"),
         ("Scapular retraction rows", "3 x 12", "Upper-back strength")],
    ),
    "fatigue": (
        "Manage fatigue", "recovery",
        [("Reduce session volume 20-30% for one week", "-", "Allow technique to recover"),
         ("Low-intensity aerobic recovery", "20-30 min", "Promote recovery"),
         ("Technique work at low fatigue only", "-", "Avoid practising poor form")],
    ),
}

RECOVERY_BY_LEVEL = {
    "low": ["Keep your normal recovery routine and aim for 7-9 hours of sleep."],
    "moderate": [
        "Schedule at least one full rest day per week.",
        "Add 10 minutes of mobility work after each session.",
        "Aim for 7-9 hours of sleep and adequate protein and fluids.",
    ],
    "high": [
        "Add a lower-load recovery day after every high-intensity session.",
        "Book a physiotherapy screening within the next week.",
        "Prioritise sleep and soft-tissue recovery between sessions.",
    ],
    "critical": [
        "Pause high-risk movements until a clinician has assessed you.",
        "Book a physiotherapy or sports-medicine assessment now.",
        "Limit training to low-impact, pain-free activity meanwhile.",
    ],
}

TRAINING_BY_LEVEL = {
    "low": "Continue current programme and re-assess in 4-6 weeks.",
    "moderate": "Reduce high-intensity volume 10-20% and add the corrective work below; re-assess in 2-3 weeks.",
    "high": "Reduce high-intensity and high-impact volume 30-50% until reviewed by a physiotherapist.",
    "critical": "Suspend high-risk movements (jumping, cutting, sprinting) pending clinical review.",
}


def build_recommendations(
    deviations: list[dict],
    risk_level: str,
    load_stats: dict | None,
    fatigue: dict | None,
    category_risks: list[dict],
) -> dict:
    # Collect issues from flagged deviations, keeping the worst severity per issue
    issues: dict[str, dict] = {}
    for d in deviations:
        if d["level"] == "normal":
            continue
        cur = issues.get(d["issue"])
        if cur is None or d["severity_fraction"] > cur["severity"]:
            issues[d["issue"]] = {"severity": d["severity_fraction"], "evidence": d["label"], "level": d["level"]}
    if fatigue and fatigue["fatigue_index"] >= 0.4:
        issues["fatigue"] = {"severity": fatigue["fatigue_index"], "evidence": "Movement quality drifts across repetitions", "level": "moderate"}

    corrective = []
    for issue, info in sorted(issues.items(), key=lambda kv: kv[1]["severity"], reverse=True):
        title, category, exercises = LIBRARY[issue]
        corrective.append(
            {
                "issue": issue,
                "title": title,
                "category": category,
                "priority": "high" if info["level"] == "high" else "medium",
                "evidence": info["evidence"],
                "exercises": [{"name": n, "prescription": p, "purpose": why} for n, p, why in exercises],
            }
        )

    training = [TRAINING_BY_LEVEL[risk_level]]
    if load_stats:
        acwr = load_stats["acwr"]
        if acwr > 1.5:
            training.append(f"Workload spike detected (acute:chronic ratio {acwr}): cut this week's load to bring the ratio under 1.3.")
        elif acwr > 1.3:
            training.append(f"Load is rising quickly (acute:chronic ratio {acwr}): hold volume steady this week.")
        elif acwr < 0.8:
            training.append(f"Load is well below your recent average (ratio {acwr}): build back gradually, no more than ~10% a week.")

    top = [c["category"] for c in category_risks[:2] if c["level"] in ("moderate", "high", "critical")]
    return {
        "risk_level": risk_level,
        "focus_areas": top,
        "corrective_exercises": corrective,
        "training_modifications": training,
        "recovery_plan": RECOVERY_BY_LEVEL[risk_level],
        "clinical_referral_suggested": risk_level in ("high", "critical"),
        "disclaimer": DISCLAIMER,
    }
