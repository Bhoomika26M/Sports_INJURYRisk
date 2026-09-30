"""Analytics + Reports router — dashboards (M4-10) and PDF/Excel export (M4-12)."""

import io
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_role
from app.core.errors import api_error
from app.database import get_db
from app.modules.analytics.schemas import AthleteTrendResponse, MovementAnalyticsResponse, RiskTrendPoint, TeamOverviewResponse
from app.modules.analytics.service import athlete_trends, coach_dashboard_data, movement_type_analytics, team_overview
from app.modules.athletes.models import Athlete
from app.modules.risk_scoring.models import RiskScore
from app.modules.recommendations.models import Recommendation
from app.modules.users.models import User, UserRole
from app.modules.video.models import BiomechanicalMetric, Video

router = APIRouter(prefix="/api/v1", tags=["analytics"])


def _can_access_athlete(user: User, athlete: Athlete) -> bool:
    if user.role in (UserRole.admin, UserRole.physiotherapist, UserRole.sports_scientist):
        return True
    if user.role == UserRole.coach and athlete.coach_id == user.id:
        return True
    if user.role == UserRole.athlete and athlete.user_id == user.id:
        return True
    return False


@router.get("/analytics/team-overview", response_model=TeamOverviewResponse)
async def get_team_overview(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await team_overview(db, current_user)


@router.get("/analytics/athletes/{athlete_id}/trends", response_model=AthleteTrendResponse)
async def get_athlete_trends(
    athlete_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    athlete = await db.scalar(select(Athlete).where(Athlete.id == athlete_id))
    if not athlete:
        raise api_error(404, "NOT_FOUND", "Athlete not found")
    if not _can_access_athlete(current_user, athlete):
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Access denied")
    return await athlete_trends(db, athlete_id, current_user)


@router.get("/analytics/movement-types/{movement_type}", response_model=MovementAnalyticsResponse)
async def get_movement_analytics(
    movement_type: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await movement_type_analytics(db, current_user, movement_type)


@router.get("/analytics/coach")
async def get_coach_dashboard(
    current_user: Annotated[User, Depends(require_role(UserRole.coach, UserRole.admin, UserRole.physiotherapist, UserRole.sports_scientist))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from app.modules.analytics.service import coach_dashboard_data
    return await coach_dashboard_data(db, current_user)


METHODOLOGY_NOTE = (
    "Composite of movement-pattern anomaly vs. population baseline, "
    "a bounded symmetry flag, and a bounded prior-injury flag. "
    "Not a trained injury-prediction model. See docs/SCIENCE_CONSTRAINTS.md."
)


async def _load_report_context(db: AsyncSession, video_id: str, user: User) -> dict:
    video = await db.scalar(select(Video).where(Video.id == video_id))
    if not video:
        raise api_error(404, "NOT_FOUND", "Video not found")
    athlete = await db.scalar(select(Athlete).where(Athlete.id == video.athlete_id))
    if not _can_access_athlete(user, athlete):
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Access denied")
    risk = await db.scalar(select(RiskScore).where(RiskScore.video_id == video_id))
    if not risk:
        raise api_error(404, "NOT_FOUND", "Video not yet scored")
    recs = list((await db.scalars(select(Recommendation).where(Recommendation.risk_score_id == risk.id))).all())
    metrics = list(
        (await db.scalars(select(BiomechanicalMetric).where(BiomechanicalMetric.video_id == video_id).order_by(BiomechanicalMetric.frame_number))).all()
    )
    return {"video": video, "athlete": athlete, "risk": risk, "recs": recs, "metrics": metrics}


@router.get("/videos/{video_id}/report.pdf")
async def export_risk_pdf(
    video_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ctx = await _load_report_context(db, video_id, current_user)
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Injury Risk Report", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"Video: {ctx['video'].original_filename} ({ctx['video'].movement_type})", styles["Normal"]),
        Paragraph(f"Score: {float(ctx['risk'].overall_score):.1f} / 100 — {ctx['risk'].risk_category}", styles["Heading2"]),
        Spacer(1, 8),
    ]
    breakdown = ctx["risk"].score_breakdown or {}
    rows = [["Component", "Points"]]
    for key in ("movement_anomaly", "asymmetry_flag", "prior_injury_flag", "acwr_flag", "fatigue_flag"):
        comp = breakdown.get(key, {}) if isinstance(breakdown, dict) else {}
        rows.append([key, str(comp.get("points", "-"))])
    table = Table(rows, colWidths=[300, 150])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey), ("GRID", (0, 0), (-1, -1), 1, colors.grey)]))
    story += [table, Spacer(1, 12), Paragraph("Recommendations", styles["Heading2"])]
    for r in ctx["recs"]:
        story += [Paragraph(f"- [{r.category}] {r.title} (P{r.priority}): {r.description}", styles["Normal"])]
    story += [Spacer(1, 12), Paragraph(f"Methodology: {METHODOLOGY_NOTE}", styles["Italic"])]
    doc.build(story)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=risk_report_{video_id}.pdf"},
    )


@router.get("/videos/{video_id}/report.xlsx")
async def export_risk_excel(
    video_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ctx = await _load_report_context(db, video_id, current_user)
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "risk_report"
    ws.append(["field", "value"])
    ws.append(["video_id", video_id])
    ws.append(["movement_type", ctx["video"].movement_type])
    ws.append(["overall_score", float(ctx["risk"].overall_score)])
    ws.append(["risk_category", ctx["risk"].risk_category])
    ws.append(["methodology_note", METHODOLOGY_NOTE])
    ws.append([])
    ws.append(["metric", "points", "max"])
    for key in ("movement_anomaly", "asymmetry_flag", "prior_injury_flag", "acwr_flag", "fatigue_flag"):
        comp = ctx["risk"].score_breakdown.get(key, {}) if isinstance(ctx["risk"].score_breakdown, dict) else {}
        ws.append([key, comp.get("points", "-"), comp.get("max", "-")])
    ws.append([])
    ws.append(["recommendations"])
    ws.append(["category", "title", "priority", "description"])
    for r in ctx["recs"]:
        ws.append([r.category, r.title, r.priority, r.description])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=risk_report_{video_id}.xlsx"},
    )