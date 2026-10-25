from typing import Dict, Any, List
import json
import os
from sqlalchemy.orm import Session
from app.models.video import Video
from app.core.config import settings
from app.core.dataset_registry import DATASET_REGISTRY

SUPPORTED_ACTIVITIES = ["running", "sprinting", "jumping", "squatting", "landing"]
LIMITED_ACTIVITIES = ["throwing", "cutting"]

def evaluate_movement(analysis_data: Dict[str, Any], activity: str) -> Dict[str, Any]:
    activity = activity.lower()
    
    result = {
        "activity": activity,
        "status": "success",
        "warnings": [],
        "flags": [],
        "summary": "",
        "disclaimer": "This is a transparent, rule-based kinematic assessment calibrated against FIFA 11+ clinical references. It is NOT a clinical diagnosis. Force cannot be measured from 2D video.",
        "clinical_reference": "FIFA 11+ / F-MARC Injury Prevention Guidelines",
        "fifa_benchmarks": {}
    }
    
    if activity in LIMITED_ACTIVITIES:
        result["status"] = "limited"
        result["summary"] = f"Analysis for '{activity}' is currently limited. Activity-specific kinematic rules are under development."
        return result
        
    if activity not in SUPPORTED_ACTIVITIES:
        result["status"] = "unsupported"
        result["summary"] = f"Activity '{activity}' is not supported."
        return result

    metrics_over_time = analysis_data.get("metrics_over_time", [])
    valid_frames = [m for m in metrics_over_time if m.get("quality_flag") == "OK"]
    missing_frames = len(metrics_over_time) - len(valid_frames)
    
    if len(metrics_over_time) == 0:
        result["status"] = "insufficient_data"
        result["summary"] = "No frames available to analyze."
        return result
        
    missing_ratio = missing_frames / len(metrics_over_time)
    if missing_ratio > 0.3:
        result["warnings"].append(f"High missing/low-confidence data rate ({int(missing_ratio*100)}%). Assessment may be unreliable.")

    if not valid_frames:
        result["status"] = "insufficient_data"
        result["summary"] = "No high-confidence frames available to assess."
        return result

    # Compute aggregates
    left_knees = [m["left_knee_angle"] for m in valid_frames]
    right_knees = [m["right_knee_angle"] for m in valid_frames]
    leans = [m["trunk_lean"] for m in valid_frames]
    
    min_l_knee = min(left_knees)
    min_r_knee = min(right_knees)
    max_lean = max(leans)
    symmetry_diff = abs(min_l_knee - min_r_knee)

    # Configurable rule-based evaluation with FIFA 11+ clinical criteria
    fifa_factors = DATASET_REGISTRY.get("fifa_reference", {}).get("risk_factors", {})

    if activity in ["squatting", "landing", "jumping"]:
        # Check symmetry
        if symmetry_diff > 15:
            result["flags"].append(f"Asymmetrical knee flexion detected (Diff: {symmetry_diff:.1f}°). Left: {min_l_knee:.1f}°, Right: {min_r_knee:.1f}°.")
        else:
            result["summary"] += "Knee flexion symmetry is within normal ranges (<=15° difference). "
            
        # Check trunk lean
        if max_lean > 25:
            result["flags"].append(f"Excessive forward trunk lean observed (Max: {max_lean:.1f}°).")
        else:
            result["summary"] += "Trunk lean maintained well. "
            
        result["fifa_benchmarks"] = {
            "knee_symmetry": {
                "observed_diff_deg": round(symmetry_diff, 1),
                "fifa_standard": "<= 10.0°",
                "status": "NORMAL" if symmetry_diff <= 10.0 else "BORDERLINE" if symmetry_diff <= 15.0 else "HIGH_RISK",
                "injury_correlation": fifa_factors.get("limb_symmetry_index", {}).get("primary_injury_risk", "Asymmetry risk")
            },
            "trunk_control": {
                "observed_lean_deg": round(max_lean, 1),
                "fifa_standard": "<= 15.0°",
                "status": "NORMAL" if max_lean <= 15.0 else "BORDERLINE" if max_lean <= 25.0 else "HIGH_RISK",
                "injury_correlation": fifa_factors.get("trunk_lean", {}).get("primary_injury_risk", "Trunk stability risk")
            }
        }
            
    elif activity in ["running", "sprinting"]:
        # Check symmetry in running (ROM symmetry approximation)
        rom_l = max(left_knees) - min(left_knees)
        rom_r = max(right_knees) - min(right_knees)
        rom_diff = abs(rom_l - rom_r)
        
        if rom_diff > 20:
            result["flags"].append(f"Asymmetrical knee Range of Motion detected (Diff: {rom_diff:.1f}°).")
        
        if max_lean > 15:
            result["flags"].append(f"Notable trunk lean/sway observed during gait (Max: {max_lean:.1f}°).")

        result["fifa_benchmarks"] = {
            "gait_symmetry": {
                "observed_diff_deg": round(rom_diff, 1),
                "fifa_standard": "<= 10.0°",
                "status": "NORMAL" if rom_diff <= 10.0 else "BORDERLINE" if rom_diff <= 20.0 else "HIGH_RISK"
            },
            "trunk_control": {
                "observed_lean_deg": round(max_lean, 1),
                "fifa_standard": "<= 15.0°",
                "status": "NORMAL" if max_lean <= 15.0 else "HIGH_RISK"
            }
        }
            
    if not result["flags"]:
        result["summary"] += "No major kinematic flags detected based on current configuration."

    return result

def get_assessment(db: Session, video_id: int, activity: str) -> Dict[str, Any]:
    from app.services.analysis_service import generate_biomechanics_analysis
    
    analysis_data = generate_biomechanics_analysis(db, video_id)
    if not analysis_data:
        return None
        
    return evaluate_movement(analysis_data, activity)
