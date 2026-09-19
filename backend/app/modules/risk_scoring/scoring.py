import numpy as np
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.modules.risk_scoring.models import RiskScore
from app.modules.risk_scoring.schemas import ScoreBreakdown, ScoreComponent

LSI_CAVEAT = (
    "LSI benchmarks are informational. Research shows the commonly-used 90% threshold "
    "does not reliably predict re-injury risk on its own — see docs/SCIENCE_CONSTRAINTS.md."
)

def compute_risk_score(
    anomaly_scores: list[float],
    limb_symmetry_index: float | None,
    has_prior_relevant_injury: bool,
) -> dict:
    """Composite score, every component visible in the breakdown — never a single
    unexplained number."""
    base = min(70.0, float(np.mean(anomaly_scores)) * 0.7) if anomaly_scores else 0.0

    asymmetry_flag = limb_symmetry_index is not None and limb_symmetry_index < 90.0
    asymmetry_points = 15.0 if asymmetry_flag else 0.0

    injury_points = 15.0 if has_prior_relevant_injury else 0.0

    overall = min(100.0, base + asymmetry_points + injury_points)

    if overall <= 30:
        category = "low"
    elif overall <= 60:
        category = "moderate"
    elif overall <= 85:
        category = "high"
    else:
        category = "critical"

    breakdown = ScoreBreakdown(
        movement_anomaly=ScoreComponent(points=round(base, 1), max=70.0, detail=f"mean anomaly percentile: {round(float(np.mean(anomaly_scores)), 1) if anomaly_scores else None}"),
        asymmetry_flag=ScoreComponent(points=asymmetry_points, max=15.0, flagged=asymmetry_flag, lsi=limb_symmetry_index, caveat=LSI_CAVEAT),
        prior_injury_flag=ScoreComponent(points=injury_points, max=15.0, flagged=has_prior_relevant_injury)
    )

    return {"overall_score": round(overall, 1), "risk_category": category, "score_breakdown": breakdown}

async def upsert_risk_score(db, video_id: str, athlete_id: str, overall_score: float, risk_category: str, score_breakdown: dict) -> RiskScore:
    stmt = pg_insert(RiskScore).values(
        video_id=video_id, athlete_id=athlete_id,
        overall_score=overall_score, risk_category=risk_category,
        score_breakdown=score_breakdown,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[RiskScore.video_id],
        set_={
            "overall_score": stmt.excluded.overall_score,
            "risk_category": stmt.excluded.risk_category,
            "score_breakdown": stmt.excluded.score_breakdown,
        },
    ).returning(RiskScore)
    result = await db.execute(stmt)
    await db.commit()
    return result.scalar_one()
