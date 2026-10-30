from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from app.database import get_db
from app.models.athlete import Athlete
from app.models.video import VideoRecord
from app.models.biomechanics import BiomechanicalAnalysis
from app.models.injury_risk import InjuryRiskAssessment

router = APIRouter(prefix="/dashboards", tags=["Dashboards & Analytics"])

@router.get("/coach")
def get_coach_dashboard(db: Session = Depends(get_db)):
    athletes = db.query(Athlete).all()
    videos = db.query(VideoRecord).all()
    athlete_cards = []

    for ath in athletes:
        latest_risk = db.query(InjuryRiskAssessment).join(
            VideoRecord, VideoRecord.id == InjuryRiskAssessment.video_id
        ).filter(
            InjuryRiskAssessment.athlete_id == ath.id,
            VideoRecord.status == "analyzed",
            VideoRecord.processed_video_path.isnot(None),
        ).order_by(InjuryRiskAssessment.id.desc()).first()
        risk_category = latest_risk.risk_category if latest_risk else "Not analyzed"
        risk_score = latest_risk.overall_injury_risk_score if latest_risk else None
        movement_quality = latest_risk.movement_quality_score if latest_risk else None
        if latest_risk and risk_category in ["High Risk", "Critical Risk"]:
            readiness = "Review flagged result"
        elif latest_risk:
            readiness = "No current flag"
        else:
            readiness = "Assessment needed"

        athlete_cards.append({
            "id": ath.id,
            "athlete_code": ath.athlete_code,
            "name": ath.name,
            "sport_type": ath.sport_type,
            "position": ath.position,
            "acwr": ath.acwr,
            "training_load": ath.training_load,
            "risk_score": risk_score,
            "risk_category": risk_category,
            "movement_quality": movement_quality,
            "readiness_status": readiness,
        })

    assessed = [a for a in athlete_cards if a["risk_score"] is not None]
    high = sum(a["risk_category"] in ["High Risk", "Critical Risk"] for a in assessed)
    moderate = sum(a["risk_category"] == "Moderate Risk" for a in assessed)
    low = sum(a["risk_category"] == "Low Risk" for a in assessed)
    qualities = [a["movement_quality"] for a in assessed if a["movement_quality"] is not None]
    all_assessed = bool(athletes) and len(assessed) == len(athletes)
    athlete_cards.sort(key=lambda x: x["risk_score"] if x["risk_score"] is not None else -1, reverse=True)

    return {
        "summary": {
            "total_squad_size": len(athletes),
            "assessed_athletes": len(assessed),
            "high_risk_athletes": high,
            "moderate_risk_athletes": moderate,
            "low_risk_athletes": low,
            "squad_availability_pct": round(((len(athletes) - high) / len(athletes)) * 100.0, 1) if all_assessed else None,
            "average_squad_movement_quality": round(sum(qualities) / len(qualities), 1) if qualities else None,
        },
        "roster": athlete_cards,
        "coach_action_alerts": [
            {
                "title": f"Review measured result for {a['name']}",
                "severity": a["risk_category"],
                "message": f"Rule-based score {a['risk_score']}/100. Review the analyzed session with a qualified professional; this is not a diagnosis.",
            }
            for a in athlete_cards if a["risk_category"] in ["High Risk", "Critical Risk"]
        ][:4],
        "video_records": len(videos),
    }


@router.get("/physiotherapist")
def get_physio_dashboard(db: Session = Depends(get_db)):
    athletes = db.query(Athlete).all()
    rehab_athletes = []

    for ath in athletes:
        history = ath.injury_history or []
        latest_risk = db.query(InjuryRiskAssessment).join(
            VideoRecord, VideoRecord.id == InjuryRiskAssessment.video_id
        ).filter(
            InjuryRiskAssessment.athlete_id == ath.id,
            VideoRecord.status == "analyzed",
            VideoRecord.processed_video_path.isnot(None),
        ).order_by(InjuryRiskAssessment.id.desc()).first()
        latest_biomech = db.query(BiomechanicalAnalysis).join(
            VideoRecord, VideoRecord.id == BiomechanicalAnalysis.video_id
        ).filter(
            BiomechanicalAnalysis.athlete_id == ath.id,
            VideoRecord.status == "analyzed",
            VideoRecord.processed_video_path.isnot(None),
        ).order_by(BiomechanicalAnalysis.id.desc()).first()

        rehab_athletes.append({
            "id": ath.id,
            "name": ath.name,
            "athlete_code": ath.athlete_code,
            "sport_type": ath.sport_type,
            "injury_history": history,
            "knee_valgus_max": max(latest_biomech.knee_valgus_left_max, latest_biomech.knee_valgus_right_max) if latest_biomech else None,
            "movement_symmetry": latest_biomech.movement_symmetry_score if latest_biomech else None,
            "pelvic_drop": latest_biomech.pelvic_drop_deg if latest_biomech else None,
            "risk_score": latest_risk.overall_injury_risk_score if latest_risk else None,
            "risk_category": latest_risk.risk_category if latest_risk else "Not analyzed",
            "category_risks": latest_risk.category_risks if latest_risk else {},
            "recommendations": latest_risk.corrective_recommendations if latest_risk else {},
        })

    areas = [
        ("Knee Valgus / Dynamic Valgus Collapse", "knee_valgus_max", 12.0, "< 10.0 deg"),
        ("Bilateral Asymmetry Deficit (>15%)", "movement_symmetry", 85.0, "> 90.0 %"),
        ("Pelvic Obliquity / Trendelenburg", "pelvic_drop", 3.0, "< 2.5 deg"),
    ]
    focus_areas = []
    for label, key, threshold, norm in areas:
        observed = [a[key] for a in rehab_athletes if a[key] is not None]
        flagged = sum(value > threshold if key != "movement_symmetry" else value < threshold for value in observed)
        focus_areas.append({"area": label, "flagged_cases": flagged, "assessed_cases": len(observed), "target_norm": norm})

    return {"rehab_registry": rehab_athletes, "clinical_focus_areas": focus_areas}


@router.get("/sports_scientist")
def get_sports_scientist_dashboard(db: Session = Depends(get_db)):
    biomech_list = db.query(BiomechanicalAnalysis).join(
        VideoRecord, VideoRecord.id == BiomechanicalAnalysis.video_id
    ).filter(
        VideoRecord.status == "analyzed",
        VideoRecord.processed_video_path.isnot(None),
    ).all()

    def mean_metric(attribute):
        values = [getattr(row, attribute) for row in biomech_list if getattr(row, attribute) is not None]
        return round(sum(values) / len(values), 2) if values else None

    avg_valgus = mean_metric("knee_valgus_avg")
    avg_symmetry = mean_metric("movement_symmetry_score")
    avg_impact_g = mean_metric("force_impact_estimation_g")

    return {
        "scientific_overview": {
            "mean_dynamic_valgus_deg": avg_valgus,
            "mean_bilateral_symmetry_pct": avg_symmetry,
            "mean_ground_reaction_force_g": avg_impact_g,
            "total_analyses_completed": len(biomech_list),
        },
        "biomechanical_distributions": [],
        "research_insights": [],
    }


@router.get("/admin")
def get_admin_dashboard(db: Session = Depends(get_db)):
    import os
    from app.models.user import User
    from app.config import UPLOAD_DIR, SAMPLE_DIR, settings

    users = db.query(User).all()
    athletes = db.query(Athlete).all()
    videos = db.query(VideoRecord).all()
    analyses = db.query(BiomechanicalAnalysis).join(
        VideoRecord, VideoRecord.id == BiomechanicalAnalysis.video_id
    ).filter(VideoRecord.status == "analyzed", VideoRecord.processed_video_path.isnot(None)).all()
    assessments = db.query(InjuryRiskAssessment).join(
        VideoRecord, VideoRecord.id == InjuryRiskAssessment.video_id
    ).filter(VideoRecord.status == "analyzed", VideoRecord.processed_video_path.isnot(None)).all()

    # User role distribution
    role_counts = {
        "athlete": sum(1 for u in users if u.role == "athlete"),
        "coach": sum(1 for u in users if u.role == "coach"),
        "physiotherapist": sum(1 for u in users if u.role == "physiotherapist"),
        "sports_scientist": sum(1 for u in users if u.role == "sports_scientist"),
        "administrator": sum(1 for u in users if u.role == "administrator")
    }

    # Calculate storage footprint
    storage_bytes = 0
    for folder in [UPLOAD_DIR, SAMPLE_DIR]:
        if folder.exists():
            for f in folder.iterdir():
                if f.is_file():
                    storage_bytes += f.stat().st_size
    storage_mb = round(storage_bytes / (1024 * 1024), 2)

    # Recent activity log
    recent_videos = db.query(VideoRecord).order_by(VideoRecord.id.desc()).limit(5).all()
    audit_logs = [
        {
            "id": v.id,
            "action": f"Video {v.status}: '{v.title}'",
            "athlete_id": v.athlete_id,
            "status": v.status,
            "created_at": v.created_at.strftime("%Y-%m-%d %H:%M UTC") if v.created_at else "Recent"
        }
        for v in recent_videos
    ]

    return {
        "system_metrics": {
            "total_registered_users": len(users),
            "total_athletes": len(athletes),
            "total_video_records": len(videos),
            "total_biomechanical_analyses": len(analyses),
            "storage_usage_mb": storage_mb,
            "database_engine": "PostgreSQL (configured)" if "postgres" in settings.DATABASE_URL.lower() else "SQLite (Local Dev)",
            "cv_runtime": "MediaPipe Pose Tasks"
        },
        "role_breakdown": role_counts,
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "created_at": u.created_at.strftime("%Y-%m-%d") if u.created_at else "2026-10-20"
            }
            for u in users
        ],
        "audit_logs": audit_logs,
        "methodology_notice": "Kinematix uses transparent rule-based calculations for software demonstration. Screening thresholds and scores are not clinically validated and are not a diagnosis."
    }
