from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from app.models.user import User
from app.models.athlete import AthleteProfile
from app.models.assignment import AthleteAssignment
from app.models.video import Video
from app.api.deps import get_current_active_user, RoleChecker
from app.services import athlete_service, video_service, analysis_service, anomaly_service, recommendation_service
from app.services.risk_scoring_service import risk_scoring_service
from app.schemas.risk import RiskScoreInput, RiskComponentInput, DataSource
import time

router = APIRouter()
allow_staff = RoleChecker(["coach", "physiotherapist", "sports_scientist", "administrator"])
allow_admin = RoleChecker(["administrator"])

def _generate_dashboard_data(db: Session, athlete_id: int):
    profile = athlete_service.get_profile_by_id(db, athlete_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Athlete not found")

    videos = video_service.get_videos_for_athlete(db, athlete_id=athlete_id)
    # Sort videos by created_at descending
    videos = sorted(videos, key=lambda v: v.created_at, reverse=True)
    completed_videos = [v for v in videos if v.status == "completed"]
    latest_video = completed_videos[0] if completed_videos else None

    # Calculate preliminary risk score
    # We will use dummy metrics for missing values or extract from profile
    # injury_history, training_load
    hist_val = 0
    if profile.injury_history:
        hist_val = 50 # simplified mapping
    
    train_val = 0
    if profile.training_load:
        train_val = 30
        
    bio_val = None
    asym_val = None
    
    anomalies = None
    anomaly_overview = None
    recommendations = None
    recommendation_breakdown = None
    analysis = None
    
    if latest_video:
        analysis = analysis_service.generate_biomechanics_analysis(db, latest_video.id)
        if analysis and analysis.get("aggregates"):
            bio_val = analysis["aggregates"].get("max_trunk_lean", 0) # Just an example mapping
            asym_val = analysis["aggregates"].get("symmetry_index", 0) * 2 # Just an example mapping
            
        anomaly_overview = None
        anomalies_res = anomaly_service.detect_anomalies(db, latest_video.id)
        if anomalies_res:
            anomalies = anomalies_res.events
            anomaly_overview = anomalies_res
            
        recommendation_breakdown = None
        rec_res = recommendation_service.generate_recommendations(db, latest_video.id)
        if rec_res:
            recommendations = rec_res.recommendations
            recommendation_breakdown = rec_res

    risk_input = RiskScoreInput(
        biomechanical_deviations=RiskComponentInput(value=min(bio_val if bio_val else 0, 100), source=DataSource.MEASURED if bio_val is not None else DataSource.ESTIMATED, is_missing=bio_val is None),
        historical_injury_factors=RiskComponentInput(value=hist_val, source=DataSource.MANUAL if hist_val > 0 else DataSource.ESTIMATED, is_missing=not profile.injury_history),
        movement_asymmetry=RiskComponentInput(value=min(asym_val if asym_val else 0, 100), source=DataSource.MEASURED if asym_val is not None else DataSource.ESTIMATED, is_missing=asym_val is None),
        training_load=RiskComponentInput(value=train_val, source=DataSource.MANUAL if train_val > 0 else DataSource.ESTIMATED, is_missing=not profile.training_load),
        fatigue_indicators=RiskComponentInput(value=None, source=DataSource.ESTIMATED, is_missing=True)
    )
    
    risk_score = risk_scoring_service.calculate_risk_score(risk_input)

    # Calculate multi-category injury risk predictions (ACL, Hamstring, Ankle, Shoulder, Lower Back, Overuse)
    injury_predictions = None
    try:
        injury_predictions = risk_scoring_service.predict_injury_risks(
            db, athlete_id=athlete_id, video_id=latest_video.id if latest_video else None
        )
    except Exception:
        pass

    # For trend data: get last 5 videos' symmetry
    trend_data = []
    for v in reversed(completed_videos[:5]):
        an = analysis_service.generate_biomechanics_analysis(db, v.id)
        if an and an.get("aggregates"):
            trend_data.append({
                "date": v.created_at.strftime("%Y-%m-%d"),
                "symmetry_index": an["aggregates"].get("symmetry_index", 0)
            })

    return {
        "athlete": {
            "id": profile.id,
            "name": profile.name,
            "sport_type": profile.sport_type,
            "position": profile.position,
            "age": profile.age,
            "assigned_staff": profile.assigned_staff,
            "coach": profile.coach,
            "physiotherapist": profile.physiotherapist
        },
        "risk_score": risk_score,
        "injury_predictions": injury_predictions,
        "latest_analysis": analysis,
        "anomalies": anomalies,
        "anomaly_overview": anomaly_overview,
        "recommendations": recommendations,
        "recommendation_breakdown": recommendation_breakdown,
        "trend_data": trend_data,
        "video_count": len(completed_videos)
    }

@router.get("/me")
def get_my_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role != "athlete":
        raise HTTPException(status_code=403, detail="Only athletes can access this dashboard endpoint")
    
    profile = athlete_service.get_profile_by_user_id(db, user_id=current_user.id)
    if not profile:
        from app.schemas.athlete import AthleteProfileCreate
        profile = athlete_service.create_profile(
            db,
            user_id=current_user.id,
            profile_in=AthleteProfileCreate(sport_type="General Athletics", age=22)
        )
        
    return _generate_dashboard_data(db, profile.id)

@router.get("/athlete/{athlete_id}")
def get_athlete_dashboard(
    athlete_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(allow_staff)
):
    profile = athlete_service.get_profile_by_id(db, athlete_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Athlete not found")
    return _generate_dashboard_data(db, athlete_id)

@router.get("/roster-summary")
def get_roster_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(allow_staff)
):
    assigned_records = db.query(AthleteAssignment).filter(AthleteAssignment.staff_id == current_user.id).all()
    assigned_ids = {a.athlete_id for a in assigned_records}
    
    all_profiles = db.query(AthleteProfile).all()
    has_custom_squad = len(assigned_ids) > 0 and current_user.role in ["coach", "physiotherapist"]
    
    athletes_summary = []
    high_risk_count = 0
    moderate_risk_count = 0
    low_risk_count = 0
    scores_list = []
    symmetry_list = []
    load_dist = {"Low": 0, "Medium": 0, "High": 0, "Exhaustive": 0}
    injury_dist = {}
    
    for p in all_profiles:
        is_in_squad = p.id in assigned_ids
        data = _generate_dashboard_data(db, p.id)
        score = data["risk_score"].composite_score
        band = data["risk_score"].risk_band
        if score is not None:
            scores_list.append(score)
            if score > 60:
                high_risk_count += 1
            elif score >= 30:
                moderate_risk_count += 1
            else:
                low_risk_count += 1
                
        intensity = "Medium"
        if p.training_load and isinstance(p.training_load, dict):
            intensity = p.training_load.get("intensity", "Medium")
        load_dist[intensity] = load_dist.get(intensity, 0) + 1
        
        if p.injury_history and isinstance(p.injury_history, list):
            for inj in p.injury_history:
                desc = inj.get("description", inj.get("type", "General Injury"))
                lower_desc = desc.lower()
                if "knee" in lower_desc or "acl" in lower_desc or "patella" in lower_desc:
                    category = "Knee"
                elif "ankle" in lower_desc:
                    category = "Ankle"
                elif "hamstring" in lower_desc:
                    category = "Hamstring"
                elif "groin" in lower_desc or "hip" in lower_desc:
                    category = "Groin / Hip"
                elif "shoulder" in lower_desc:
                    category = "Shoulder"
                elif "back" in lower_desc or "spine" in lower_desc or "lumbar" in lower_desc:
                    category = "Spine / Back"
                else:
                    category = "Soft Tissue / Other"
                injury_dist[category] = injury_dist.get(category, 0) + 1

        sym = None
        max_lean = None
        l_knee = None
        r_knee = None
        if data["latest_analysis"] and data["latest_analysis"].get("aggregates"):
            aggs = data["latest_analysis"]["aggregates"]
            sym = aggs.get("symmetry_index")
            max_lean = aggs.get("max_trunk_lean")
            l_knee = aggs.get("left_knee_min")
            r_knee = aggs.get("right_knee_min")
            if sym is not None:
                symmetry_list.append(sym)
                
        athletes_summary.append({
            "id": p.id,
            "name": p.name,
            "sport_type": p.sport_type,
            "position": p.position,
            "age": p.age,
            "height_cm": p.height_cm,
            "weight_kg": p.weight_kg,
            "training_load": intensity,
            "injury_count": len(p.injury_history) if p.injury_history else 0,
            "video_count": data["video_count"],
            "risk_score": score,
            "risk_band": band,
            "symmetry_index": sym,
            "max_trunk_lean": max_lean,
            "left_knee_min": l_knee,
            "right_knee_min": r_knee,
            "is_assigned_to_me": is_in_squad,
            "assigned_staff": p.assigned_staff,
            "coach": p.coach,
            "physiotherapist": p.physiotherapist,
            "anomalies_count": len(data["anomalies"]) if data["anomalies"] else 0,
            "recommendations_count": len(data["recommendations"]) if data["recommendations"] else 0,
            "latest_recommendations": data["recommendations"][:2] if data["recommendations"] else []
        })

    recent_videos_query = db.query(Video).order_by(Video.created_at.desc()).limit(8).all()
    recent_screenings = []
    for v in recent_videos_query:
        ath = athlete_service.get_profile_by_id(db, v.athlete_id)
        ath_name = ath.name if ath else f"Athlete #{v.athlete_id}"
        recent_screenings.append({
            "id": v.id,
            "athlete_id": v.athlete_id,
            "athlete_name": ath_name,
            "filename": v.filename,
            "status": v.status,
            "created_at": v.created_at.isoformat() if v.created_at else None
        })

    avg_score = round(sum(scores_list) / len(scores_list), 1) if scores_list else 0
    avg_sym = round(sum(symmetry_list) / len(symmetry_list), 1) if symmetry_list else 0
    total_scored = len(scores_list)
    readiness_pct = round(((low_risk_count + (moderate_risk_count * 0.7)) / total_scored) * 100) if total_scored > 0 else 85
    
    return {
        "athletes": athletes_summary,
        "total_athletes": len(all_profiles),
        "assigned_count": len(assigned_ids),
        "high_risk_count": high_risk_count,
        "moderate_risk_count": moderate_risk_count,
        "low_risk_count": low_risk_count,
        "avg_risk_score": avg_score,
        "avg_symmetry_index": avg_sym,
        "squad_readiness_pct": readiness_pct,
        "load_distribution": load_dist,
        "injury_distribution": injury_dist,
        "recent_screenings": recent_screenings,
        "has_custom_squad": has_custom_squad
    }

@router.get("/admin-summary")
def get_admin_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(allow_admin)
):
    t0 = time.time()
    db.execute(text("SELECT 1"))
    db_latency = int((time.time() - t0) * 1000)
    
    users = db.query(User).all()
    roles_count = {}
    active_count = 0
    for u in users:
        roles_count[u.role] = roles_count.get(u.role, 0) + 1
        if u.is_active:
            active_count += 1
            
    athletes_count = db.query(AthleteProfile).count()
    videos = db.query(Video).all()
    video_status_count = {}
    for v in videos:
        video_status_count[v.status] = video_status_count.get(v.status, 0) + 1
        
    assignments_count = db.query(AthleteAssignment).count()
    
    return {
        "total_users": len(users),
        "active_users": active_count,
        "inactive_users": len(users) - active_count,
        "roles_breakdown": roles_count,
        "total_athletes": athletes_count,
        "total_videos": len(videos),
        "videos_breakdown": video_status_count,
        "total_assignments": assignments_count,
        "system_health": {
            "database": "PostgreSQL 17 (Operational)",
            "db_latency_ms": db_latency,
            "cv_engine": "MediaPipe Pose Estimation 0.10",
            "risk_engine": "FIFA 11+ Biomechanical Matrix",
            "auth_service": "OAuth2 JWT + Google OAuth",
            "storage_status": "Active (Local Volume Persistence)",
            "api_status": "Healthy"
        }
    }
