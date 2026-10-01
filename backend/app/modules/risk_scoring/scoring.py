"""Risk scoring — transparent additive composite with cited weights.

``anomaly_scores`` are per-frame scores on the 0-anchored scale defined in anomaly.py
(0 = inside the baseline's normal envelope). The movement component is 0.7 x their mean, so a
perfectly normal athlete now contributes ~0 points (previously ~37 of 70 by construction).

Category cut-points (constants.RISK_CATEGORY_UPPER_BOUNDS): low <=25, moderate <=50, high <=75,
critical >75. They are kept at 25/50/75 because (a) they were written as if 0 meant "no anomaly",
which is now true, and (b) there is no injury-outcome data to recalibrate against -- they are
conventional quarter bands of a bounded index, NOT risk probabilities. The movement component
caps at 70, so "critical" cannot be reached by movement pattern alone: it needs corroborating
flags (asymmetry / prior injury / load / fatigue). That is deliberate.
"""

import numpy as np
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.risk_scoring.constants import RISK_CATEGORY_TOP, RISK_CATEGORY_UPPER_BOUNDS
from app.modules.risk_scoring.models import RiskScore
from app.modules.risk_scoring.schemas import ScoreBreakdown, ScoreComponent

LSI_CAVEAT = (
    "LSI benchmarks are informational. Research shows the commonly-used 90% threshold "
    "does not reliably predict re-injury risk on its own — see docs/SCIENCE_CONSTRAINTS.md."
)


def compute_risk_score(
    anomaly_scores: list[float],       # from anomaly detection, per validated metric
    limb_symmetry_index: float | None,  # from biomechanics
    has_prior_relevant_injury: bool,
    acwr: float | None = None,          # from training load (when ≥28 days data)
    rpe_trend: float | None = None,     # from training load RPE trend
    baseline_note: str | None = None,   # what the anomaly baseline was made of, for transparency
) -> dict:
    """Composite score, every component visible in the breakdown — never a single unexplained number."""

    # Movement anomaly component (0-70 pts)
    base = min(70.0, float(np.mean(anomaly_scores)) * 0.7) if anomaly_scores else 0.0

    # Asymmetry flag (0-15 pts)
    asymmetry_flag = limb_symmetry_index is not None and limb_symmetry_index < 90.0
    asymmetry_points = 15.0 if asymmetry_flag else 0.0

    # Prior injury flag (0-10 pts)
    injury_points = 10.0 if has_prior_relevant_injury else 0.0

    # ACWR flag (0-10 pts) — only when data exists
    acwr_flag = acwr is not None and acwr > 1.5
    acwr_points = 10.0 if acwr_flag else 0.0

    # Fatigue flag (0-10 pts) — only when data exists
    fatigue_flag = rpe_trend is not None and rpe_trend > 1.5
    fatigue_points = 10.0 if fatigue_flag else 0.0

    overall = min(100.0, base + asymmetry_points + injury_points + acwr_points + fatigue_points)

    category = next((name for name, upper in RISK_CATEGORY_UPPER_BOUNDS if overall <= upper), RISK_CATEGORY_TOP)

    breakdown = ScoreBreakdown(
        movement_anomaly=ScoreComponent(points=round(base, 1), max=70.0, detail=_anomaly_detail(anomaly_scores, baseline_note)),
        asymmetry_flag=ScoreComponent(points=asymmetry_points, max=15.0, flagged=asymmetry_flag, lsi=limb_symmetry_index, caveat=LSI_CAVEAT),
        prior_injury_flag=ScoreComponent(points=injury_points, max=10.0, flagged=has_prior_relevant_injury),
        acwr_flag=ScoreComponent(points=acwr_points, max=10.0, flagged=acwr_flag, acwr=acwr),
        fatigue_flag=ScoreComponent(points=fatigue_points, max=10.0, flagged=fatigue_flag, rpe_trend=rpe_trend),
    )

    return {"overall_score": round(overall, 1), "risk_category": category, "score_breakdown": breakdown}


def _anomaly_detail(anomaly_scores: list[float], baseline_note: str | None) -> str:
    if not anomaly_scores:
        return "no validated frames scored"
    mean = round(float(np.mean(anomaly_scores)), 1)
    text = f"mean frame anomaly score: {mean} (0 = inside the baseline's normal envelope, 100 = far outside)"
    return f"{text}; {baseline_note}" if baseline_note else text


async def upsert_risk_score(db: AsyncSession, video_id: str, athlete_id: str, overall_score: float, risk_category: str, score_breakdown: dict) -> RiskScore:
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