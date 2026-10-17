import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database import get_db
from app.models.athlete import Athlete
from app.models.analysis import AnalysisRecord
from app.models.prediction import InjuryAssessmentRecord
from app.schemas.prediction import (
    InjuryAssessmentResponse,
    InjuryAssessmentRequest,
    RiskBreakdown,
    EarlyWarningItem,
    RecommendationPlan
)
from app.services.injury_predictor import InjuryPredictor
from app.services.recommendations import RecommendationEngine
from app.services.biomechanics import BiomechanicalAnalyzer

router = APIRouter(
    prefix="/prediction",
    tags=["Injury Risk Prediction & Recommendations"]
)

_predictor: Optional[InjuryPredictor] = None
_recommender: Optional[RecommendationEngine] = None
_analyzer: Optional[BiomechanicalAnalyzer] = None


def get_predictor() -> InjuryPredictor:
    global _predictor
    if _predictor is None:
        _predictor = InjuryPredictor()
    return _predictor


def get_recommender() -> RecommendationEngine:
    global _recommender
    if _recommender is None:
        _recommender = RecommendationEngine()
    return _recommender


def get_analyzer() -> BiomechanicalAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = BiomechanicalAnalyzer()
    return _analyzer


@router.post("/assess", response_model=InjuryAssessmentResponse)
def assess_risk_endpoint(
    req: InjuryAssessmentRequest,
    db: Session = Depends(get_db)
):
    """
    Execute AI Injury Risk Prediction, Risk Scoring, Early Warnings, 
    and Prescriptive Corrective Recommendations.
    """
    predictor = get_predictor()
    recommender = get_recommender()
    analyzer = get_analyzer()

    # 1. Fetch Athlete profile if available
    athlete_dict = {
        "age": 22,
        "height": 178,
        "weight": 72,
        "injury_history": "No previous injuries",
        "training_load": 65.0
    }
    if req.athlete_id:
        athlete = db.query(Athlete).filter(
            (Athlete.athlete_id == req.athlete_id) | (Athlete.id == req.athlete_id)
        ).first()
        if athlete:
            athlete_dict = {
                "age": athlete.age,
                "height": athlete.height,
                "weight": athlete.weight,
                "injury_history": athlete.injury_history or "",
                "training_load": athlete.training_load or 65.0
            }

    # 2. Get Biomechanics input
    anomalies: List[str] = []
    if req.biomechanics and "metrics_summary" in req.biomechanics:
        biomech_data = req.biomechanics
        anomalies = req.biomechanics.get("anomalies", [])
    else:
        # Check if athlete has an existing analysis record
        last_record = None
        if req.athlete_id:
            last_record = db.query(AnalysisRecord).filter(
                AnalysisRecord.athlete_id == req.athlete_id
            ).order_by(AnalysisRecord.id.desc()).first()

        if last_record:
            biomech_data = {
                "overall_score": last_record.overall_score,
                "metrics_summary": {
                    "peak_valgus_overall": last_record.peak_valgus,
                    "mean_asymmetry_index": last_record.mean_asymmetry,
                    "peak_flexion_overall": last_record.peak_flexion,
                    "peak_trunk_lean": last_record.peak_trunk_lean
                }
            }
            try:
                anomalies = json.loads(last_record.anomalies) if last_record.anomalies else []
            except Exception:
                anomalies = []
        else:
            # Generate demonstration biomechanics for requested movement
            demo = analyzer.generate_synthetic_biomechanics_demo(req.movement_type or "SQUAT")
            biomech_data = {
                "overall_score": demo["quality_report"]["overall_score"],
                "metrics_summary": demo["quality_report"]["metrics_summary"]
            }
            anomalies = demo["quality_report"]["anomalies"]

    # 3. Predict Injury Risk
    risk_assessment = predictor.assess_injury_risk(biomech_data, athlete_dict)
    risk_breakdown = risk_assessment["risk_breakdown"]

    # 4. Generate Prescriptive Recommendations
    rec_plan = recommender.generate_recommendations(
        risk_breakdown=risk_breakdown,
        training_load=athlete_dict["training_load"],
        anomalies=anomalies
    )

    # 5. Persist Assessment in DB
    db_record = InjuryAssessmentRecord(
        athlete_id=req.athlete_id,
        video_name=f"Assessment_{req.movement_type}",
        movement_type=req.movement_type or "SQUAT",
        overall_risk_score=risk_assessment["overall_risk_score"],
        risk_level=risk_assessment["risk_level"],
        acl_risk=risk_breakdown["acl_risk"],
        hamstring_risk=risk_breakdown["hamstring_risk"],
        ankle_risk=risk_breakdown["ankle_risk"],
        patellar_risk=risk_breakdown["patellar_risk"],
        early_warnings=json.dumps(risk_assessment["early_warnings"]),
        recommendations=json.dumps(rec_plan)
    )
    db.add(db_record)
    db.commit()
    db.refresh(db_record)

    return InjuryAssessmentResponse(
        id=db_record.id,
        athlete_id=req.athlete_id,
        movement_type=req.movement_type or "SQUAT",
        overall_risk_score=risk_assessment["overall_risk_score"],
        risk_level=risk_assessment["risk_level"],
        risk_breakdown=RiskBreakdown(**risk_breakdown),
        early_warnings=[EarlyWarningItem(**w) for w in risk_assessment["early_warnings"]],
        recommendations=RecommendationPlan(**rec_plan),
        created_at=db_record.created_at
    )


@router.get("/athlete/{athlete_id}/latest", response_model=InjuryAssessmentResponse)
def get_latest_risk_assessment(
    athlete_id: str,
    db: Session = Depends(get_db)
):
    """
    Get the most recent injury risk prediction and corrective protocol for an athlete.
    """
    record = db.query(InjuryAssessmentRecord).filter(
        InjuryAssessmentRecord.athlete_id == athlete_id
    ).order_by(InjuryAssessmentRecord.id.desc()).first()

    if not record:
        # Generate default assessment on the fly
        return assess_risk_endpoint(
            InjuryAssessmentRequest(athlete_id=athlete_id, movement_type="SQUAT"),
            db=db
        )

    try:
        warnings = json.loads(record.early_warnings)
    except Exception:
        warnings = []

    try:
        recs = json.loads(record.recommendations)
    except Exception:
        recs = {
            "prescribed_exercises": [],
            "training_load_recommendation": "",
            "recovery_status": "",
            "recovery_guidelines": []
        }

    return InjuryAssessmentResponse(
        id=record.id,
        athlete_id=record.athlete_id,
        movement_type=record.movement_type,
        overall_risk_score=record.overall_risk_score,
        risk_level=record.risk_level,
        risk_breakdown=RiskBreakdown(
            acl_risk=record.acl_risk,
            hamstring_risk=record.hamstring_risk,
            ankle_risk=record.ankle_risk,
            patellar_risk=record.patellar_risk
        ),
        early_warnings=[EarlyWarningItem(**w) for w in warnings],
        recommendations=RecommendationPlan(**recs),
        created_at=record.created_at
    )
