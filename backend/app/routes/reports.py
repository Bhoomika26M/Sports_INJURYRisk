import json
import io
import csv
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.report import ReportRecord
from app.models.athlete import Athlete
from app.models.prediction import InjuryAssessmentRecord
from app.models.analysis import AnalysisRecord
from app.schemas.report import ReportCreate, ReportOut

router = APIRouter(
    prefix="/reports",
    tags=["Reports & Export System"]
)


def _seed_initial_reports(db: Session):
    if db.query(ReportRecord).count() == 0:
        samples = [
            ReportRecord(
                report_title="Marcus Vance - Biomechanical Valgus & ACL Vulnerability Analysis",
                report_type="INJURY_RISK",
                athlete_id="ATH-101",
                athlete_name="Marcus Vance",
                generated_by="Dr. Sarah Jenkins (Physiotherapist)",
                summary="High dynamic valgus observed (14.2°) with 21% bilateral asymmetry. ACL injury risk score calculated at 74% (HIGH). Prescribed glute medius strengthening and neuromuscular landing retraining.",
                data_json=json.dumps({
                    "valgus_left": 14.2,
                    "valgus_right": 8.5,
                    "asymmetry_index": 21.0,
                    "risk_level": "HIGH",
                    "acl_risk": 78.4,
                    "hamstring_risk": 42.0,
                    "prescribed_exercises": ["Banded Monster Walks", "Single-Leg Romanian Deadlift", "Depth Drop Deceleration"]
                })
            ),
            ReportRecord(
                report_title="Squad Biomechanical Movement Screening - Pre-Season Assessment",
                report_type="TEAM_SUMMARY",
                athlete_id="ALL",
                athlete_name="Varsity Squad",
                generated_by="Coach Roberts",
                summary="Screened 12 varsity athletes. 3 identified with elevated hamstring strain probability due to bilateral asymmetry exceeding 15%. Load management modified for next microcycle.",
                data_json=json.dumps({
                    "squad_size": 12,
                    "avg_movement_score": 76.5,
                    "high_risk_count": 2,
                    "moderate_risk_count": 4,
                    "low_risk_count": 6
                })
            )
        ]
        db.add_all(samples)
        db.commit()


@router.get("/", response_model=List[ReportOut])
def get_all_reports(
    athlete_id: Optional[str] = None,
    report_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Retrieve all generated clinical and coaching reports."""
    _seed_initial_reports(db)
    query = db.query(ReportRecord)
    if athlete_id:
        query = query.filter(ReportRecord.athlete_id == athlete_id)
    if report_type:
        query = query.filter(ReportRecord.report_type == report_type)
    return query.order_by(ReportRecord.created_at.desc()).all()


@router.get("/{report_id}", response_model=ReportOut)
def get_report_by_id(report_id: int, db: Session = Depends(get_db)):
    """Retrieve a single report by ID."""
    report = db.query(ReportRecord).filter(ReportRecord.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.post("/generate", response_model=ReportOut)
def generate_report(req: ReportCreate, db: Session = Depends(get_db)):
    """Generate and store a new clinical biomechanical or risk assessment report."""
    data_str = json.dumps(req.data or {})
    report = ReportRecord(
        report_title=req.report_title,
        report_type=req.report_type.upper(),
        athlete_id=req.athlete_id,
        athlete_name=req.athlete_name,
        generated_by=req.generated_by,
        summary=req.summary,
        data_json=data_str
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get("/export/csv")
def export_athletes_csv(db: Session = Depends(get_db)):
    """Export athlete profiles and biomechanical injury assessments as a CSV file."""
    athletes = db.query(Athlete).all()
    output = io.StringIO()
    writer = csv.writer(output)

    # Headers
    writer.writerow([
        "Athlete ID", "Sport", "Position", "Age", "Height (cm)", "Weight (kg)",
        "Training Load", "Injury History", "Latest Valgus (°)", "Latest Risk Score (%)", "Risk Level"
    ])

    for a in athletes:
        # Get latest assessment if exists
        latest_pred = db.query(InjuryAssessmentRecord).filter(
            InjuryAssessmentRecord.athlete_id == a.athlete_id
        ).order_by(InjuryAssessmentRecord.id.desc()).first()

        latest_analysis = db.query(AnalysisRecord).filter(
            AnalysisRecord.athlete_id == a.athlete_id
        ).order_by(AnalysisRecord.id.desc()).first()

        peak_valgus = latest_analysis.peak_valgus if latest_analysis else "N/A"
        risk_score = latest_pred.overall_risk_score if latest_pred else "N/A"
        risk_level = latest_pred.risk_level if latest_pred else "NOT ASSESSED"

        writer.writerow([
            a.athlete_id,
            a.sport_type,
            a.position,
            a.age,
            a.height,
            a.weight,
            a.training_load,
            a.injury_history or "None",
            peak_valgus,
            risk_score,
            risk_level
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sports_injury_analytics_export.csv"}
    )
