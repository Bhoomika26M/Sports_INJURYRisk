from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.api import deps
from app.models.user import User
from app.models.athlete import AthleteProfile
from app.services import athlete_service
from app.schemas.report import FullReportData
from app.services.report_service import report_service

router = APIRouter()

def _check_athlete_access(db: Session, current_user: User, athlete_id: int):
    profile = athlete_service.get_profile_by_id(db, athlete_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Athlete profile not found")
        
    if current_user.role == "athlete":
        if profile.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to view another athlete's clinical reports")
    elif current_user.role != "administrator":
        is_assigned = athlete_service.check_staff_assigned_to_athlete(db, staff_id=current_user.id, athlete_id=profile.id)
        if not is_assigned:
            raise HTTPException(status_code=403, detail="Not authorized to access this athlete's reports")
    return profile

@router.get("/{athlete_id}/data", response_model=FullReportData)
def get_report_json(
    athlete_id: int,
    report_type: str = Query("injury_risk", pattern="^(injury_risk|biomechanical|movement_analysis|athlete_performance|rehabilitation)$"),
    video_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Fetch structured JSON report data for UI rendering and preview.
    Valid report types:
    - injury_risk
    - biomechanical
    - movement_analysis
    - athlete_performance
    - rehabilitation
    """
    _check_athlete_access(db, current_user, athlete_id)
    try:
        return report_service.get_report_data(
            db=db,
            athlete_id=athlete_id,
            report_type=report_type,
            video_id=video_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")

@router.get("/{athlete_id}/export/pdf")
def export_report_pdf(
    athlete_id: int,
    report_type: str = Query("injury_risk", pattern="^(injury_risk|biomechanical|movement_analysis|athlete_performance|rehabilitation)$"),
    video_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Generate and download a high-resolution, multi-page PDF report.
    """
    profile = _check_athlete_access(db, current_user, athlete_id)
    try:
        report_data = report_service.get_report_data(
            db=db,
            athlete_id=athlete_id,
            report_type=report_type,
            video_id=video_id
        )
        pdf_bytes = report_service.generate_pdf_report(report_data)
        
        filename = f"AthletiQ_{report_type}_{profile.name.replace(' ', '_')}_{report_data.metadata.report_id}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export PDF: {str(e)}")

@router.get("/{athlete_id}/export/excel")
def export_report_excel(
    athlete_id: int,
    report_type: str = Query("injury_risk", pattern="^(injury_risk|biomechanical|movement_analysis|athlete_performance|rehabilitation)$"),
    video_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Generate and download a structured multi-sheet Excel (.xlsx) workbook.
    """
    profile = _check_athlete_access(db, current_user, athlete_id)
    try:
        report_data = report_service.get_report_data(
            db=db,
            athlete_id=athlete_id,
            report_type=report_type,
            video_id=video_id
        )
        excel_bytes = report_service.generate_excel_report(report_data)
        
        filename = f"AthletiQ_{report_type}_{profile.name.replace(' ', '_')}_{report_data.metadata.report_id}.xlsx"
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export Excel: {str(e)}")
