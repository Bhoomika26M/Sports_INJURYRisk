"""Recommendation rules — map flagged metrics to corrective exercises."""

from app.modules.risk_scoring.constants import ANOMALY_REVIEW_POINTS, ANOMALY_SIGNIFICANT_POINTS
from app.modules.risk_scoring.schemas import ScoreBreakdown


RECOMMENDATION_RULES = [
    # Asymmetry (LSI < 90%)
    {
        "trigger": lambda breakdown: breakdown.asymmetry_flag.flagged,
        "category": "strengthening",
        "priority": 2,
        "title": "Address limb asymmetry",
        "description": "Single-leg strengthening work (single-leg squats, Bulgarian split squats, Nordic hamstring curls) targeting the weaker side, per standard ACL-prevention programs such as FIFA 11+.",
    },
    # Movement anomaly component above the moderate-band floor (25 of 70 points)
    {
        "trigger": lambda breakdown: breakdown.movement_anomaly.points > ANOMALY_REVIEW_POINTS,
        "category": "mobility",
        "priority": 1,
        "title": "Movement pattern review",
        "description": "This movement pattern deviates notably from the population baseline for this drill. Recommend a coach/physio review of technique on video before assuming a strength or mobility cause.",
    },
    # Prior injury
    {
        "trigger": lambda breakdown: breakdown.prior_injury_flag.flagged,
        "category": "recovery",
        "priority": 1,
        "title": "Prior injury monitoring",
        "description": "This athlete has a documented prior injury relevant to this movement. Recommend continued monitoring and communication with the treating physiotherapist regardless of this session's score.",
    },
    # ACWR flag
    {
        "trigger": lambda breakdown: breakdown.acwr_flag and breakdown.acwr_flag.flagged,
        "category": "training_modification",
        "priority": 2,
        "title": "Training load management",
        "description": "Acute:Chronic Workload Ratio is elevated above 1.5 (see the ACWR value in this score's breakdown). Reduce training volume/intensity this week and monitor recovery. See Gabbett 2016.",
    },
    # Fatigue flag
    {
        "trigger": lambda breakdown: breakdown.fatigue_flag and breakdown.fatigue_flag.flagged,
        "category": "recovery",
        "priority": 2,
        "title": "Fatigue management",
        "description": "RPE trend indicates accumulating fatigue. Recommend active recovery session, sleep hygiene emphasis, and reduced intensity for next 48-72 hours.",
    },
    # High movement anomaly (specific metrics)
    {
        "trigger": lambda breakdown: breakdown.movement_anomaly.points > ANOMALY_SIGNIFICANT_POINTS,
        "category": "mobility",
        "priority": 1,
        "title": "Significant movement deviation detected",
        "description": "Movement pattern shows substantial deviation from population baseline. Immediate technique review recommended. Consider video analysis with coach/physio.",
    },
]


def generate_recommendations(breakdown: ScoreBreakdown) -> list[dict]:
    return [
        {"category": r["category"], "title": r["title"], "description": r["description"], "priority": r["priority"]}
        for r in RECOMMENDATION_RULES if r["trigger"](breakdown)
    ]