from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.deps import get_current_user
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
