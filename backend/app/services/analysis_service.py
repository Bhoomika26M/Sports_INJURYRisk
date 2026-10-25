import os
import json
import math
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app.models.video import Video
from app.core.config import settings
from app.utils.biomechanics import process_frame_biomechanics

def generate_biomechanics_analysis(db: Session, video_id: int) -> Optional[Dict[str, Any]]:
    """
    Biomechanical Analysis Engine:
    - Joint angle analysis (knees, hips, ankles, shoulders, elbows)
    - Range of motion (ROM) analysis
    - Movement symmetry evaluation & Limb Symmetry Index (LSI)
    - Knee Valgus & Frontal Plane Projection Angle (FPPA)
    - Hip stability & pelvic drop (Trendelenburg indicator)
    - Trunk lean (sagittal & coronal sway)
    - Landing mechanics & landing stiffness classification
    - Stride length & step displacement
    - Joint alignment (kinetic chain collinearity)
    - Posture & cervical assessment
    - Dynamic Balance & Center of Mass (COM) sway
    - Force estimation (Peak vertical Ground Reaction Force in body weights & impact loading rate)
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video or video.status != "completed":
        return None
        
    base_name = os.path.splitext(os.path.basename(video.file_path))[0]
    json_path = os.path.join(settings.UPLOAD_DIR, f"{base_name}_landmarks.json")
    
    if not os.path.exists(json_path):
        return None
        
    with open(json_path, "r") as f:
        data = json.load(f)
        
    width = data.get("width", 1)
    height = data.get("height", 1)
    fps = data.get("fps") or 30.0
    frames = data.get("frames", [])
    
    analysis_results = {
        "video_id": video.id,
        "athlete_id": video.athlete_id,
        "movement_type": getattr(video, "movement_type", "general") or "general",
        "fps": fps,
        "width": width,
        "height": height,
        "total_frames": len(frames),
        "metrics_over_time": [],
        "aggregates": {
            # Backward-compatible core keys
            "left_knee_min": None,
            "right_knee_min": None,
            "max_trunk_lean": None,
            "symmetry_index": None,
            # Enhanced Biomechanical Metrics
            "range_of_motion": {},
            "movement_symmetry": {},
            "knee_valgus": {},
            "hip_stability": {},
            "landing_mechanics": {},
            "stride_and_gait": {},
            "joint_alignment": {},
            "posture_assessment": {},
            "balance_metrics": {},
            "force_estimation": {}
        },
        "disclaimer": "WARNING: These measurements are biomechanical video estimates. Camera perspective, sampling rate, and clothing affect 2D precision. This data cannot substitute for 3D laboratory motion capture or formal diagnostic clinical assessment."
    }
    
    # Value accumulators
    left_knees = []
    right_knees = []
    left_hips = []
    right_hips = []
    left_ankles = []
    right_ankles = []
    left_shoulders = []
    right_shoulders = []
    leans = []
    lateral_leans = []
    pelvic_drops = []
    valgus_ratios = []
    left_fppas = []
    right_fppas = []
    stride_lengths = []
    alignments = []
    cervical_angles = []
    com_positions = [] # (t_ms, com_x, com_y)
    
    for frame in frames:
        metrics = process_frame_biomechanics(frame, width, height)
        analysis_results["metrics_over_time"].append(metrics)
        
        if metrics.get("quality_flag") == "OK":
            if metrics["left_knee_angle"] is not None: left_knees.append(metrics["left_knee_angle"])
            if metrics["right_knee_angle"] is not None: right_knees.append(metrics["right_knee_angle"])
            if metrics["left_hip_angle"] is not None: left_hips.append(metrics["left_hip_angle"])
            if metrics["right_hip_angle"] is not None: right_hips.append(metrics["right_hip_angle"])
            if metrics.get("left_ankle_angle") is not None: left_ankles.append(metrics["left_ankle_angle"])
            if metrics.get("right_ankle_angle") is not None: right_ankles.append(metrics["right_ankle_angle"])
            if metrics.get("left_shoulder_angle") is not None: left_shoulders.append(metrics["left_shoulder_angle"])
            if metrics.get("right_shoulder_angle") is not None: right_shoulders.append(metrics["right_shoulder_angle"])
            if metrics["trunk_lean"] is not None: leans.append(metrics["trunk_lean"])
            if metrics.get("lateral_trunk_lean") is not None: lateral_leans.append(metrics["lateral_trunk_lean"])
            if metrics.get("pelvic_drop_angle") is not None: pelvic_drops.append(metrics["pelvic_drop_angle"])
            if metrics.get("knee_valgus_ratio") is not None: valgus_ratios.append(metrics["knee_valgus_ratio"])
            if metrics.get("left_fppa") is not None: left_fppas.append(metrics["left_fppa"])
            if metrics.get("right_fppa") is not None: right_fppas.append(metrics["right_fppa"])
            if metrics.get("stride_length_ratio") is not None: stride_lengths.append(metrics["stride_length_ratio"])
            if metrics.get("joint_alignment_deg") is not None: alignments.append(metrics["joint_alignment_deg"])
            if metrics.get("cervical_angle") is not None: cervical_angles.append(metrics["cervical_angle"])
            if metrics.get("com_x") is not None and metrics.get("com_y") is not None:
                com_positions.append((metrics["timestamp_ms"], metrics["com_x"], metrics["com_y"]))
            
    # 1. Backward-compatible Core Knee Flexion & Symmetry
    if left_knees and right_knees:
        min_l = min(left_knees)
        min_r = min(right_knees)
        analysis_results["aggregates"]["left_knee_min"] = round(min_l, 1)
        analysis_results["aggregates"]["right_knee_min"] = round(min_r, 1)
        sym_diff = abs(min_l - min_r)
        analysis_results["aggregates"]["symmetry_index"] = round(sym_diff, 1)
    elif left_knees:
        analysis_results["aggregates"]["left_knee_min"] = round(min(left_knees), 1)
    elif right_knees:
        analysis_results["aggregates"]["right_knee_min"] = round(min(right_knees), 1)
        
    if leans:
        analysis_results["aggregates"]["max_trunk_lean"] = round(max(leans), 1)

    # 2. Range of Motion (ROM) Analysis
    rom_data = {}
    if left_knees:
        rom_data["left_knee_rom"] = round(max(left_knees) - min(left_knees), 1)
        rom_data["left_knee_max_ext"] = round(max(left_knees), 1)
    if right_knees:
        rom_data["right_knee_rom"] = round(max(right_knees) - min(right_knees), 1)
        rom_data["right_knee_max_ext"] = round(max(right_knees), 1)
    if left_hips:
        rom_data["left_hip_rom"] = round(max(left_hips) - min(left_hips), 1)
    if right_hips:
        rom_data["right_hip_rom"] = round(max(right_hips) - min(right_hips), 1)
    if left_ankles:
        rom_data["left_ankle_rom"] = round(max(left_ankles) - min(left_ankles), 1)
    if right_ankles:
        rom_data["right_ankle_rom"] = round(max(right_ankles) - min(right_ankles), 1)
    if leans:
        rom_data["trunk_lean_rom"] = round(max(leans) - min(leans), 1)
    analysis_results["aggregates"]["range_of_motion"] = rom_data

    # 3. Movement Symmetry & Limb Symmetry Index (LSI)
    symmetry_data = {}
    if left_knees and right_knees:
        knee_diff = abs(min(left_knees) - min(right_knees))
        knee_rom_l = max(left_knees) - min(left_knees)
        knee_rom_r = max(right_knees) - min(right_knees)
        knee_rom_diff = abs(knee_rom_l - knee_rom_r)
        
        # Limb Symmetry Index: (min/max) * 100
        lsi_flexion = round((min(min(left_knees), min(right_knees)) / max(max(left_knees), max(right_knees), 1e-4)) * 100.0, 1) if max(left_knees + right_knees) > 0 else 100.0
        lsi_rom = round((min(knee_rom_l, knee_rom_r) / max(knee_rom_l, knee_rom_r, 1e-4)) * 100.0, 1) if max(knee_rom_l, knee_rom_r) > 0 else 100.0
        
        symmetry_data["knee_flexion_diff_deg"] = round(knee_diff, 1)
        symmetry_data["knee_rom_diff_deg"] = round(knee_rom_diff, 1)
        symmetry_data["limb_symmetry_index_pct"] = lsi_rom
        symmetry_data["symmetry_status"] = "Normal" if knee_diff <= 10.0 else "Borderline" if knee_diff <= 15.0 else "Asymmetric Deficit"
    if left_hips and right_hips:
        hip_diff = abs(min(left_hips) - min(right_hips))
        symmetry_data["hip_flexion_diff_deg"] = round(hip_diff, 1)
    analysis_results["aggregates"]["movement_symmetry"] = symmetry_data

    # 4. Knee Valgus & Frontal Plane Projection Angle (FPPA)
    valgus_data = {}
    if valgus_ratios:
        min_ratio = min(valgus_ratios)
        valgus_data["min_knee_ankle_ratio"] = round(min_ratio, 2)
        valgus_data["dynamic_valgus_detected"] = min_ratio < 0.85
        valgus_data["valgus_risk_tier"] = "High (Medial Collapse)" if min_ratio < 0.80 else "Moderate" if min_ratio < 0.88 else "Low (Aligned)"
    if left_fppas and right_fppas:
        valgus_data["mean_left_fppa"] = round(sum(left_fppas) / len(left_fppas), 1)
        valgus_data["mean_right_fppa"] = round(sum(right_fppas) / len(right_fppas), 1)
    analysis_results["aggregates"]["knee_valgus"] = valgus_data

    # 5. Hip Stability & Pelvic Drop
    hip_stab_data = {}
    if pelvic_drops:
        max_drop = max(pelvic_drops)
        hip_stab_data["max_pelvic_drop_deg"] = round(max_drop, 1)
        hip_stab_data["trendelenburg_sign"] = max_drop > 8.0
        hip_stab_data["stability_status"] = "Stable Pelvis" if max_drop <= 5.0 else "Mild Pelvic Drop" if max_drop <= 8.0 else "Excessive Trendelenburg Drop"
    if left_hips and right_hips:
        hip_stab_data["max_hip_flexion"] = round(min(left_hips + right_hips), 1)
    analysis_results["aggregates"]["hip_stability"] = hip_stab_data

    # 6. Landing Mechanics & Stiffness
    landing_data = {}
    if left_knees and right_knees:
        # Detect landing impact: lowest knee angle achieved during dynamic drop
        deepest_knee = min(min(left_knees), min(right_knees))
        landing_data["peak_landing_knee_flexion"] = round(deepest_knee, 1)
        # Landing stiffness: Stiff < 30 deg flexion (150-180 deg joint angle), Moderate, Soft > 45 deg flexion (< 135 deg joint angle)
        # Note: 180 deg = straight leg. 120 deg = 60 deg of flexion from vertical.
        flexion_depth = 180.0 - deepest_knee
        landing_data["flexion_depth_deg"] = round(flexion_depth, 1)
        if flexion_depth < 30.0:
            stiffness = "Stiff (High ACL Impact)"
        elif flexion_depth < 45.0:
            stiffness = "Moderate"
        else:
            stiffness = "Soft (High Shock Absorption)"
        landing_data["landing_stiffness"] = stiffness
        landing_data["landing_symmetry_diff_deg"] = round(abs(min(left_knees) - min(right_knees)), 1)
    analysis_results["aggregates"]["landing_mechanics"] = landing_data

    # 7. Stride Length & Gait
    stride_data = {}
    if stride_lengths:
        stride_data["mean_stride_ratio"] = round(sum(stride_lengths) / len(stride_lengths), 2)
        stride_data["max_stride_ratio"] = round(max(stride_lengths), 2)
        stride_data["overstriding_risk"] = max(stride_lengths) > 1.35
    analysis_results["aggregates"]["stride_and_gait"] = stride_data

    # 8. Joint Alignment (Kinetic Chain Collinearity)
    alignment_data = {}
    if alignments:
        alignment_data["mean_kinetic_alignment_deg"] = round(sum(alignments) / len(alignments), 1)
        alignment_data["alignment_status"] = "Well-Aligned" if (sum(alignments)/len(alignments)) >= 165.0 else "Suboptimal Deviations"
    analysis_results["aggregates"]["joint_alignment"] = alignment_data

    # 9. Posture Assessment
    posture_data = {}
    if leans:
        posture_data["max_sagittal_trunk_lean"] = round(max(leans), 1)
    if lateral_leans:
        posture_data["max_coronal_lateral_sway"] = round(max(lateral_leans), 1)
    if cervical_angles:
        posture_data["cervical_forward_head_angle"] = round(sum(cervical_angles) / len(cervical_angles), 1)
    analysis_results["aggregates"]["posture_assessment"] = posture_data

    # 10. Balance & Dynamic Center of Mass (COM) Sway
    balance_data = {}
    if com_positions and len(com_positions) > 3:
        xs = [p[1] for p in com_positions]
        mean_x = sum(xs) / len(xs)
        sway_std = math.sqrt(sum((x - mean_x) ** 2 for x in xs) / len(xs))
        sway_range = max(xs) - min(xs)
        balance_data["medial_lateral_sway_std_px"] = round(sway_std, 1)
        balance_data["medial_lateral_sway_range_px"] = round(sway_range, 1)
        balance_data["balance_stability_score"] = round(max(0, 100.0 - (sway_std * 2.5)), 1)
    analysis_results["aggregates"]["balance_metrics"] = balance_data

    # 11. Force Estimation (Peak vGRF & Impact Loading Rate)
    force_data = {}
    if com_positions and len(com_positions) > 4:
        # Calculate vertical acceleration from COM Y trajectory
        dt = 1.0 / max(fps, 10.0)
        v_accels = []
        for i in range(1, len(com_positions) - 1):
            y_prev = com_positions[i - 1][2]
            y_curr = com_positions[i][2]
            y_next = com_positions[i + 1][2]
            # 2nd central difference: d2y/dt2 (in pixels/s^2)
            d2y = (y_next - 2 * y_curr + y_prev) / (dt ** 2)
            # Normalize to estimated body heights (approx height = 0.8 * image height)
            norm_ay = abs(d2y) / max(height * 0.75, 10.0)
            v_accels.append(norm_ay)
            
        if v_accels:
            # Scale acceleration to multiples of gravity (g = 9.81 m/s^2)
            # Peak ground reaction force is typically 1.5x - 3.5x BW in jumping/landing
            max_accel_g = min(max(v_accels) * 0.25, 4.0)
            peak_vgrf = round(1.0 + max_accel_g, 2)
            avg_vgrf = round(1.0 + (sum(v_accels) / len(v_accels)) * 0.15, 2)
            force_data["peak_vgrf_bw"] = peak_vgrf
            force_data["mean_vgrf_bw"] = avg_vgrf
            force_data["impact_severity"] = "High Impact Spike" if peak_vgrf > 2.8 else "Moderate Load" if peak_vgrf > 2.0 else "Low Impact"
            force_data["estimated_loading_rate_bw_per_s"] = round(peak_vgrf / 0.05, 1)
    analysis_results["aggregates"]["force_estimation"] = force_data

    return analysis_results
