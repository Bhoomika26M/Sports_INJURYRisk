from app.modules.risk_scoring.schemas import ScoreBreakdown

RECOMMENDATION_RULES = [
    {
        "trigger": lambda breakdown: breakdown.asymmetry_flag.flagged,
        "category": "strengthening", "priority": 2,
        "title": "Address limb asymmetry",
        "description": "Single-leg strengthening work (single-leg squats, Bulgarian split squats, Nordic hamstring curls) targeting the weaker side, per standard ACL-prevention programs such as FIFA 11+.",
    },
    {
        "trigger": lambda breakdown: breakdown.movement_anomaly.points > 40,
        "category": "mobility", "priority": 1,
        "title": "Movement pattern review",
        "description": "This movement pattern deviates notably from the population baseline for this drill. Recommend a coach/physio review of technique on video before assuming a strength or mobility cause.",
    },
    {
        "trigger": lambda breakdown: breakdown.prior_injury_flag.flagged,
        "category": "recovery", "priority": 1,
        "title": "Prior injury monitoring",
        "description": "This athlete has a documented prior injury relevant to this movement. Recommend continued monitoring and communication with the treating physiotherapist regardless of this session's score.",
    },
]

def generate_recommendations(breakdown: ScoreBreakdown) -> list[dict]:
    return [
        {"category": r["category"], "title": r["title"], "description": r["description"], "priority": r["priority"]}
        for r in RECOMMENDATION_RULES if r["trigger"](breakdown)
    ]
