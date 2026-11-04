from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.athlete import Athlete
from app.models.notification import ReportRecord
from app.models.user import Role, User
from app.models.video import Analysis
from app.schemas.notification import ReportFormat, ReportOut, ReportType
from app.services.access import accessible_athletes_query, get_athlete_for
from app.services.report_service import build_excel, build_pdf

router = APIRouter(prefix="/reports", tags=["reports"])

MEDIA_TYPES = {
    "pdf": "application/pdf",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


@router.post("/generate", response_model=ReportOut, status_code=201)
async def generate_report(
    analysis_id: int,
    report_type: ReportType = "injury_risk",
    file_format: ReportFormat = "pdf",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    athlete = get_athlete_for(db, user, analysis.athlete_id)

    history_rows = db.scalars(
        select(Analysis).where(Analysis.athlete_id == athlete.id).order_by(Analysis.created_at.desc()).limit(10)
    ).all()
    history = [(a.created_at, a.risk_score, a.movement_quality) for a in reversed(history_rows)]
    injuries = [
        {"injury_type": i.injury_type, "body_part": i.body_part, "injury_date": i.injury_date, "status": i.status}
        for i in athlete.injuries
    ]

    out_dir = Path(settings.REPORT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{report_type}_{uuid4().hex}.{file_format}"
    builder = build_pdf if file_format == "pdf" else build_excel
    await run_in_threadpool(builder, path, report_type, athlete, analysis, history, injuries)

    record = ReportRecord(
        athlete_id=athlete.id, analysis_id=analysis.id, created_by=user.id,
        report_type=report_type, file_format=file_format, file_path=str(path),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/research")
def research_export(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.sports_scientist.value, Role.administrator.value)),
):
    """Team-level Excel export for research: one row per athlete and one per analysis.

    Athletes are identified by their code only (no names), so the file can be shared more freely.
    """
    from io import BytesIO

    from openpyxl import Workbook
    from openpyxl.styles import Font

    athletes = db.scalars(accessible_athletes_query(user)).all()
    by_id = {a.id: a for a in athletes}
    analyses = db.scalars(
        select(Analysis).where(Analysis.athlete_id.in_(list(by_id) or [0])).order_by(Analysis.created_at)
    ).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Athletes"
    ws.append(["Athlete code", "Sport", "Position", "Age", "Analyses", "Latest analysis", "Latest risk score",
               "Latest risk category", "Mean risk score", "Latest movement quality"])
    per_athlete: dict[int, list[Analysis]] = {}
    for a in analyses:
        per_athlete.setdefault(a.athlete_id, []).append(a)
    for ath in athletes:
        rows = per_athlete.get(ath.id, [])
        last = rows[-1] if rows else None
        ws.append([
            ath.athlete_code, ath.sport_type, ath.position, ath.age, len(rows),
            last.created_at.date().isoformat() if last else None,
            last.risk_score if last else None, last.risk_category if last else None,
            round(sum(r.risk_score for r in rows) / len(rows), 1) if rows else None,
            last.movement_quality if last else None,
        ])

    ws2 = wb.create_sheet("Analyses")
    metric_keys = ["knee_valgus_peak_deg", "hip_stability_pelvic_drop_deg", "trunk_lean_max_deg",
                   "landing_knee_flexion_deg", "stride_variability_pct", "joint_alignment_score"]
    ws2.append(["Date", "Athlete code", "Activity", "Risk score", "Risk category", "Movement quality",
                "Biomechanical efficiency", "Fatigue risk", "Overall health", *metric_keys])
    for a in analyses:
        scores = a.scores or {}
        metrics = (a.biomechanics or {}).get("metrics", {})
        ws2.append([
            a.created_at.date().isoformat(), by_id[a.athlete_id].athlete_code, a.activity, a.risk_score,
            a.risk_category, a.movement_quality, scores.get("biomechanical_efficiency"),
            scores.get("fatigue_risk"), scores.get("overall_health"), *[metrics.get(k) for k in metric_keys],
        ])
    for sheet in (ws, ws2):
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        for col in sheet.columns:
            sheet.column_dimensions[col[0].column_letter].width = max(12, min(30, len(str(col[0].value)) + 2))

    buf = BytesIO()
    wb.save(buf)
    return Response(
        content=buf.getvalue(), media_type=MEDIA_TYPES["xlsx"],
        headers={"Content-Disposition": 'attachment; filename="research_export.xlsx"'},
    )


@router.get("", response_model=list[ReportOut])
def list_reports(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ids = select(accessible_athletes_query(user).subquery().c.id)
    query = select(ReportRecord).where(ReportRecord.athlete_id.in_(ids))
    return db.scalars(query.order_by(ReportRecord.created_at.desc()).limit(100)).all()


def _get_report(db: Session, user: User, report_id: int) -> ReportRecord:
    record = db.get(ReportRecord, report_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Report not found")
    get_athlete_for(db, user, record.athlete_id)
    return record


@router.get("/{report_id}/download")
def download_report(report_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = _get_report(db, user, report_id)
    path = Path(record.file_path)
    if not path.exists():
        raise HTTPException(status_code=410, detail="Report file no longer available")
    return FileResponse(path, media_type=MEDIA_TYPES[record.file_format], filename=f"{record.report_type}_report.{record.file_format}")


@router.delete("/{report_id}", status_code=204)
def delete_report(report_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = _get_report(db, user, report_id)
    if user.role != Role.administrator.value and record.created_by != user.id:
        raise HTTPException(status_code=403, detail="Only the creator or an administrator can delete this report")
    Path(record.file_path).unlink(missing_ok=True)
    db.delete(record)
    db.commit()
