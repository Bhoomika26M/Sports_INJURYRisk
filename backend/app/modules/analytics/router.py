"""Analytics + Reports router — dashboards (M4-10) and PDF/Excel export (M4-12, U6)."""

import io
from typing import Annotated
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access import can_access_athlete as _can_access_athlete
from app.core.deps import UuidPath, get_current_user, require_role
from app.core.errors import api_error
from app.database import get_db
from app.modules.analytics.schemas import AthleteTrendResponse, MovementAnalyticsResponse, RiskTrendPoint, TeamOverviewResponse
from app.modules.analytics.service import athlete_trends, coach_dashboard_data, movement_type_analytics, team_overview
from app.modules.athletes.models import Athlete
from app.modules.risk_scoring.models import RiskScore
from app.modules.risk_scoring.scoring import METHODOLOGY_NOTE, WEIGHTS
from app.modules.recommendations.models import Recommendation
from app.modules.users.models import User, UserRole
from app.modules.video.models import BiomechanicalMetric, Video

COMPONENT_KEYS = tuple(WEIGHTS)  # the five spec components, in spec order

router = APIRouter(prefix="/api/v1", tags=["analytics"])


@router.get("/analytics/team-overview", response_model=TeamOverviewResponse)
async def get_team_overview(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await team_overview(db, current_user)


@router.get("/analytics/athletes/{athlete_id}/trends", response_model=AthleteTrendResponse)
async def get_athlete_trends(
    athlete_id: UuidPath,
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
    from app.modules.video.models import MovementType

    known = await db.scalar(select(MovementType).where(MovementType.code == movement_type))
    if not known:
        raise api_error(404, "NOT_FOUND", f"Unknown movement type: {movement_type}")
    return await movement_type_analytics(db, current_user, movement_type)


@router.get("/analytics/coach")
async def get_coach_dashboard(
    current_user: Annotated[User, Depends(require_role(UserRole.coach, UserRole.admin, UserRole.physiotherapist, UserRole.sports_scientist))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await coach_dashboard_data(db, current_user)


async def _load_report_context(db: AsyncSession, video_id: str, user: User) -> dict:
    video = await db.scalar(select(Video).where(Video.id == video_id))
    if not video:
        raise api_error(404, "NOT_FOUND", "Video not found")
    athlete = await db.scalar(select(Athlete).where(Athlete.id == video.athlete_id))
    if not athlete:
        raise api_error(404, "NOT_FOUND", "Athlete not found")
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
    video_id: UuidPath,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ctx = await _load_report_context(db, video_id, current_user)
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    v = ctx["video"]
    risk = ctx["risk"]
    quality = (v.analysis or {}).get("quality") or {}
    grade = quality.get("grade", "unrated")
    coverage_caveat = v.coverage_caveat or "none"

    safe_filename = escape(v.original_filename or f"video_{v.id[:8]}.mp4")
    safe_mv = escape(v.movement_type or "unspecified")
    safe_category = escape(risk.risk_category or "unclassified")

    story = [
        Paragraph("Biomechanical Movement Screening & Risk Report", styles["Title"]),
        Spacer(1, 8),
        Paragraph(f"<b>Video:</b> {safe_filename} | <b>Movement:</b> {safe_mv} ({escape(v.camera_view or 'unknown')})", styles["Normal"]),
        Paragraph(f"<b>Tracking Quality:</b> {escape(str(grade).capitalize())} | <b>Coverage Caveat:</b> {escape(str(coverage_caveat))}", styles["Normal"]),
        Spacer(1, 6),
        Paragraph(f"<b>Movement Risk Score:</b> {float(risk.overall_score):.1f} / 100 — {safe_category.upper()}", styles["Heading2"]),
        Spacer(1, 8),
    ]

    breakdown = risk.score_breakdown or {}
    rows = [["Risk Assessment Component", "Points", "Max Points", "Status"]]
    for key in COMPONENT_KEYS:
        comp = breakdown.get(key, {}) if isinstance(breakdown, dict) else {}
        available = comp.get("available", True)
        pts = f"{float(comp.get('points', 0.0)):.1f}" if available else "unavailable"
        max_pts = str(comp.get("max", "-"))
        status_label = "Active" if available else "Excluded (Insufficient Baseline)"
        rows.append([key.replace("_", " ").title(), pts, max_pts, status_label])

    table = Table(rows, colWidths=[200, 75, 75, 170])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story += [table, Spacer(1, 12)]

    if ctx["recs"]:
        story.append(Paragraph("Evidence-Based Recommendations", styles["Heading2"]))
        story.append(Spacer(1, 4))
        for r in ctx["recs"]:
            title_esc = escape(r.title or "Recommendation")
            desc_esc = escape(r.description or "")
            cat_esc = escape(r.category or "exercise")
            story.append(Paragraph(f"• <b>[{cat_esc.upper()}] {title_esc}</b> (Priority {r.priority}): {desc_esc}", styles["Normal"]))
            story.append(Spacer(1, 4))

    story.append(Spacer(1, 10))
    story.append(Paragraph(f"<b>Methodology:</b> {escape(METHODOLOGY_NOTE)}", styles["Italic"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>Notice:</b> This system is a biomechanical decision-support screening tool. It does not provide medical diagnoses or predict injury probability.", styles["Normal"]))

    doc.build(story)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="risk_report_{video_id[:8]}.pdf"'},
    )


@router.get("/videos/{video_id}/report.xlsx")
async def export_risk_excel(
    video_id: UuidPath,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ctx = await _load_report_context(db, video_id, current_user)
    from openpyxl import Workbook

    wb = Workbook()

    # Sheet 1: Summary / risk_report
    ws_summary = wb.active
    ws_summary.title = "Summary"
    ws_summary.append(["field", "value"])
    ws_summary.append(["video_id", video_id])
    ws_summary.append(["movement_type", ctx["video"].movement_type])
    ws_summary.append(["camera_view", ctx["video"].camera_view])
    ws_summary.append(["overall_score", float(ctx["risk"].overall_score)])
    ws_summary.append(["risk_category", ctx["risk"].risk_category])
    ws_summary.append(["quality_grade", (ctx["video"].analysis or {}).get("quality", {}).get("grade", "unrated")])
    ws_summary.append(["coverage_caveat", ctx["video"].coverage_caveat or "none"])
    ws_summary.append(["methodology_note", METHODOLOGY_NOTE])
    ws_summary.append([])
    ws_summary.append(["biomechanical_deviations", "points", "max"])  # preserves test compatibility
    for key in COMPONENT_KEYS:
        comp = ctx["risk"].score_breakdown.get(key, {}) if isinstance(ctx["risk"].score_breakdown, dict) else {}
        ws_summary.append([key, comp.get("points", "-"), comp.get("max", "-")])

    # Sheet 2: Components
    ws_comp = wb.create_sheet(title="Components")
    ws_comp.append(["component", "points", "max_points", "available"])
    for key in COMPONENT_KEYS:
        comp = ctx["risk"].score_breakdown.get(key, {}) if isinstance(ctx["risk"].score_breakdown, dict) else {}
        ws_comp.append([key, comp.get("points", "-"), comp.get("max", "-"), comp.get("available", True)])

    # Sheet 3: Metrics (real biomechanical_metrics rows from DB, U6 requirement)
    ws_metrics = wb.create_sheet(title="Metrics")
    ws_metrics.append(["frame_number", "metric_name", "value", "plane", "confidence", "movement_phase"])
    for m in ctx["metrics"]:
        val = float(m.metric_value) if m.metric_value is not None else None
        ws_metrics.append([m.frame_number, m.metric_name, val, m.plane, m.confidence, m.movement_phase or ""])

    # Sheet 4: Recommendations
    ws_recs = wb.create_sheet(title="Recommendations")
    ws_recs.append(["category", "title", "priority", "description"])
    for r in ctx["recs"]:
        ws_recs.append([r.category, r.title, r.priority, r.description])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="risk_report_{video_id[:8]}.xlsx"'},
    )
