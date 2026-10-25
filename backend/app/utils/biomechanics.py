import math
from typing import Dict, Any, Optional, Tuple, List

VISIBILITY_THRESHOLD = 0.50

def get_landmark(frame_data: Dict, name: str) -> Optional[Dict]:
    for lm in frame_data.get("landmarks", []):
        if lm["name"] == name:
            return lm
    return None

def unnormalize(pt: Dict, width: int, height: int) -> Dict:
    return {
        "x": pt["x"] * width,
        "y": pt["y"] * height,
        "z": pt.get("z", 0.0) * width,  # Z is roughly same scale as X
        "visibility": pt.get("visibility", 0.0)
    }

def calculate_angle_2d(a: Dict, b: Dict, c: Dict, width: int, height: int) -> Optional[float]:
    """Calculate 2D planar angle at vertex b using points a, b, c."""
    if not a or not b or not c:
        return None
    if any(pt.get("visibility", 0) < VISIBILITY_THRESHOLD for pt in (a, b, c)):
        return None
        
    ua = unnormalize(a, width, height)
    ub = unnormalize(b, width, height)
    uc = unnormalize(c, width, height)
    
    ang = math.degrees(
        math.atan2(uc["y"] - ub["y"], uc["x"] - ub["x"]) - 
        math.atan2(ua["y"] - ub["y"], ua["x"] - ub["x"])
    )
    ang = abs(ang)
    if ang > 180:
        ang = 360 - ang
    return round(ang, 1)

def calculate_midpoint(a: Dict, b: Dict) -> Optional[Dict]:
    if not a or not b:
        return None
    if a.get("visibility", 0) < VISIBILITY_THRESHOLD or b.get("visibility", 0) < VISIBILITY_THRESHOLD:
        return None
    return {
        "x": (a["x"] + b["x"]) / 2,
        "y": (a["y"] + b["y"]) / 2,
        "z": (a.get("z", 0.0) + b.get("z", 0.0)) / 2,
        "visibility": min(a.get("visibility", 1.0), b.get("visibility", 1.0))
    }

def calculate_distance_2d(a: Dict, b: Dict, width: int, height: int) -> Optional[float]:
    if not a or not b:
        return None
    ua = unnormalize(a, width, height)
    ub = unnormalize(b, width, height)
    return math.sqrt((ua["x"] - ub["x"]) ** 2 + (ua["y"] - ub["y"]) ** 2)

def calculate_trunk_lean(left_shoulder: Dict, right_shoulder: Dict, left_hip: Dict, right_hip: Dict, width: int, height: int) -> Optional[float]:
    """
    Calculate sagittal forward trunk lean relative to vertical (0 degrees = vertical).
    """
    mid_shoulder = calculate_midpoint(left_shoulder, right_shoulder)
    mid_hip = calculate_midpoint(left_hip, right_hip)
    
    if not mid_shoulder or not mid_hip:
        return None
        
    u_shoulder = unnormalize(mid_shoulder, width, height)
    u_hip = unnormalize(mid_hip, width, height)
    
    dx = u_shoulder["x"] - u_hip["x"]
    dy = u_shoulder["y"] - u_hip["y"]
    
    ang = math.degrees(math.atan2(dy, dx))
    lean = abs(ang + 90)
    if lean > 180:
        lean = 360 - lean
    return round(lean, 1)

def calculate_lateral_trunk_lean(left_shoulder: Dict, right_shoulder: Dict, left_hip: Dict, right_hip: Dict, width: int, height: int) -> Optional[float]:
    """
    Calculate coronal lateral trunk lean (lateral sway) relative to vertical.
    """
    mid_shoulder = calculate_midpoint(left_shoulder, right_shoulder)
    mid_hip = calculate_midpoint(left_hip, right_hip)
    if not mid_shoulder or not mid_hip:
        return None
    dx = abs(mid_shoulder["x"] - mid_hip["x"]) * width
    dy = abs(mid_shoulder["y"] - mid_hip["y"]) * height
    if dy == 0:
        return 0.0
    lean = math.degrees(math.atan2(dx, dy))
    return round(lean, 1)

def calculate_pelvic_drop(left_hip: Dict, right_hip: Dict, width: int, height: int) -> Optional[float]:
    """
    Calculate pelvic tilt / pelvic drop angle relative to horizontal (Trendelenburg indicator).
    0 degrees means horizontal level hips.
    """
    if not left_hip or not right_hip:
        return None
    if left_hip.get("visibility", 0) < VISIBILITY_THRESHOLD or right_hip.get("visibility", 0) < VISIBILITY_THRESHOLD:
        return None
    lh = unnormalize(left_hip, width, height)
    rh = unnormalize(right_hip, width, height)
    dy = abs(rh["y"] - lh["y"])
    dx = abs(rh["x"] - lh["x"])
    if dx == 0:
        return 90.0
    angle = math.degrees(math.atan2(dy, dx))
    return round(angle, 1)

def calculate_knee_valgus(left_hip: Dict, right_hip: Dict, left_knee: Dict, right_knee: Dict, left_ankle: Dict, right_ankle: Dict, width: int, height: int) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Biomechanical Knee Valgus Metrics:
    Returns (valgus_ratio, left_fppa, right_fppa).
    - valgus_ratio: knee-to-ankle width ratio (< 0.85 during landing/squat indicates dynamic knee valgus collapse).
    - FPPA: Frontal Plane Projection Angle (2D angle between hip-knee vector and knee-ankle vector).
    """
    if not all([left_hip, right_hip, left_knee, right_knee, left_ankle, right_ankle]):
        return None, None, None
        
    d_knee = calculate_distance_2d(left_knee, right_knee, width, height)
    d_ankle = calculate_distance_2d(left_ankle, right_ankle, width, height)
    
    valgus_ratio = None
    if d_knee is not None and d_ankle is not None and d_ankle > 10:
        valgus_ratio = round(d_knee / d_ankle, 2)
        
    left_fppa = calculate_angle_2d(left_hip, left_knee, left_ankle, width, height)
    right_fppa = calculate_angle_2d(right_hip, right_knee, right_ankle, width, height)
    
    return valgus_ratio, left_fppa, right_fppa

def calculate_stride_length(left_ankle: Dict, right_ankle: Dict, left_hip: Dict, right_hip: Dict, width: int, height: int) -> Optional[float]:
    """
    Calculates step/stride length normalized by average leg length (hip to ankle).
    """
    d_ankles = calculate_distance_2d(left_ankle, right_ankle, width, height)
    l_leg = calculate_distance_2d(left_hip, left_ankle, width, height)
    r_leg = calculate_distance_2d(right_hip, right_ankle, width, height)
    
    if not d_ankles or not l_leg or not r_leg:
        return None
    avg_leg = (l_leg + r_leg) / 2.0
    if avg_leg == 0:
        return None
    return round(d_ankles / avg_leg, 2)

def calculate_center_of_mass(landmarks: List[Dict], width: int, height: int) -> Tuple[Optional[float], Optional[float]]:
    """
    Estimates 2D center of mass (COM) using weighted anatomical body segment coordinates.
    """
    if not landmarks:
        return None, None
    lm_map = {lm["name"]: lm for lm in landmarks if lm.get("visibility", 0) >= VISIBILITY_THRESHOLD}
    
    # Required core hubs
    mid_sh = calculate_midpoint(lm_map.get("left_shoulder"), lm_map.get("right_shoulder"))
    mid_hp = calculate_midpoint(lm_map.get("left_hip"), lm_map.get("right_hip"))
    mid_kn = calculate_midpoint(lm_map.get("left_knee"), lm_map.get("right_knee"))
    mid_ak = calculate_midpoint(lm_map.get("left_ankle"), lm_map.get("right_ankle"))
    
    if not mid_hp:
        return None, None
        
    # Segment weightings: Torso (50%), Thighs (30%), Shanks/Feet (20%)
    sh_pt = mid_sh or mid_hp
    kn_pt = mid_kn or mid_hp
    ak_pt = mid_ak or kn_pt
    
    com_x = 0.50 * ((sh_pt["x"] + mid_hp["x"]) / 2) + 0.30 * kn_pt["x"] + 0.20 * ak_pt["x"]
    com_y = 0.50 * ((sh_pt["y"] + mid_hp["y"]) / 2) + 0.30 * kn_pt["y"] + 0.20 * ak_pt["y"]
    
    return round(com_x * width, 1), round(com_y * height, 1)

def calculate_cervical_posture(nose: Dict, left_shoulder: Dict, right_shoulder: Dict, width: int, height: int) -> Optional[float]:
    """
    Calculates cervical spine / forward head posture angle relative to thoracic spine.
    """
    mid_sh = calculate_midpoint(left_shoulder, right_shoulder)
    if not nose or not mid_sh:
        return None
    u_nose = unnormalize(nose, width, height)
    u_sh = unnormalize(mid_sh, width, height)
    dx = abs(u_nose["x"] - u_sh["x"])
    dy = abs(u_nose["y"] - u_sh["y"])
    if dy == 0:
        return 0.0
    return round(math.degrees(math.atan2(dx, dy)), 1)

def process_frame_biomechanics(frame_data: Dict, width: int, height: int) -> Dict:
    """
    Comprehensive frame-by-frame biomechanical extraction:
    - Joint angles (knees, hips, ankles, shoulders, elbows)
    - Frontal plane knee valgus (FPPA, knee-ankle ratio)
    - Hip stability and pelvic drop (Trendelenburg)
    - Sagittal and coronal trunk lean
    - Stride length & step displacement
    - Joint alignment (kinetic chain collinearity)
    - Posture & cervical alignment
    - Center of Mass (COM) coordinates
    """
    metrics = {
        "timestamp_ms": frame_data["timestamp_ms"],
        "left_knee_angle": None,
        "right_knee_angle": None,
        "left_hip_angle": None,
        "right_hip_angle": None,
        "left_ankle_angle": None,
        "right_ankle_angle": None,
        "left_shoulder_angle": None,
        "right_shoulder_angle": None,
        "left_elbow_angle": None,
        "right_elbow_angle": None,
        "trunk_lean": None,
        "lateral_trunk_lean": None,
        "pelvic_drop_angle": None,
        "knee_valgus_ratio": None,
        "left_fppa": None,
        "right_fppa": None,
        "stride_length_ratio": None,
        "joint_alignment_deg": None,
        "cervical_angle": None,
        "com_x": None,
        "com_y": None,
        "quality_flag": "OK"
    }
    
    # Extract landmarks
    l_hip = get_landmark(frame_data, "left_hip")
    r_hip = get_landmark(frame_data, "right_hip")
    l_knee = get_landmark(frame_data, "left_knee")
    r_knee = get_landmark(frame_data, "right_knee")
    l_ankle = get_landmark(frame_data, "left_ankle")
    r_ankle = get_landmark(frame_data, "right_ankle")
    l_shoulder = get_landmark(frame_data, "left_shoulder")
    r_shoulder = get_landmark(frame_data, "right_shoulder")
    l_elbow = get_landmark(frame_data, "left_elbow")
    r_elbow = get_landmark(frame_data, "right_elbow")
    l_wrist = get_landmark(frame_data, "left_wrist")
    r_wrist = get_landmark(frame_data, "right_wrist")
    l_foot = get_landmark(frame_data, "left_foot_index") or get_landmark(frame_data, "left_heel")
    r_foot = get_landmark(frame_data, "right_foot_index") or get_landmark(frame_data, "right_heel")
    nose = get_landmark(frame_data, "nose")
    
    # Baseline existence check
    if not all([l_hip, r_hip, l_knee, r_knee, l_ankle, r_ankle, l_shoulder, r_shoulder]):
        metrics["quality_flag"] = "MISSING_LANDMARKS"
        return metrics

    # 1. Joint angles
    metrics["left_knee_angle"] = calculate_angle_2d(l_hip, l_knee, l_ankle, width, height)
    metrics["right_knee_angle"] = calculate_angle_2d(r_hip, r_knee, r_ankle, width, height)
    metrics["left_hip_angle"] = calculate_angle_2d(l_shoulder, l_hip, l_knee, width, height)
    metrics["right_hip_angle"] = calculate_angle_2d(r_shoulder, r_hip, r_knee, width, height)
    
    if l_foot:
        metrics["left_ankle_angle"] = calculate_angle_2d(l_knee, l_ankle, l_foot, width, height)
    if r_foot:
        metrics["right_ankle_angle"] = calculate_angle_2d(r_knee, r_ankle, r_foot, width, height)
        
    if l_elbow:
        metrics["left_shoulder_angle"] = calculate_angle_2d(l_hip, l_shoulder, l_elbow, width, height)
        if l_wrist:
            metrics["left_elbow_angle"] = calculate_angle_2d(l_shoulder, l_elbow, l_wrist, width, height)
    if r_elbow:
        metrics["right_shoulder_angle"] = calculate_angle_2d(r_hip, r_shoulder, r_elbow, width, height)
        if r_wrist:
            metrics["right_elbow_angle"] = calculate_angle_2d(r_shoulder, r_elbow, r_wrist, width, height)

    # 2. Trunk & Posture
    metrics["trunk_lean"] = calculate_trunk_lean(l_shoulder, r_shoulder, l_hip, r_hip, width, height)
    metrics["lateral_trunk_lean"] = calculate_lateral_trunk_lean(l_shoulder, r_shoulder, l_hip, r_hip, width, height)
    metrics["pelvic_drop_angle"] = calculate_pelvic_drop(l_hip, r_hip, width, height)
    metrics["cervical_angle"] = calculate_cervical_posture(nose, l_shoulder, r_shoulder, width, height)

    # 3. Knee Valgus & Alignment
    valgus_ratio, l_fppa, r_fppa = calculate_knee_valgus(l_hip, r_hip, l_knee, r_knee, l_ankle, r_ankle, width, height)
    metrics["knee_valgus_ratio"] = valgus_ratio
    metrics["left_fppa"] = l_fppa
    metrics["right_fppa"] = r_fppa
    
    # Joint alignment (average left & right kinetic collinearity)
    if l_fppa is not None and r_fppa is not None:
        metrics["joint_alignment_deg"] = round((l_fppa + r_fppa) / 2.0, 1)

    # 4. Stride Length
    metrics["stride_length_ratio"] = calculate_stride_length(l_ankle, r_ankle, l_hip, r_hip, width, height)

    # 5. Center of Mass
    com_x, com_y = calculate_center_of_mass(frame_data.get("landmarks", []), width, height)
    metrics["com_x"] = com_x
    metrics["com_y"] = com_y

    # Quality check
    if any(v is None for v in [metrics["left_knee_angle"], metrics["right_knee_angle"], metrics["left_hip_angle"], metrics["right_hip_angle"], metrics["trunk_lean"]]):
        metrics["quality_flag"] = "LOW_CONFIDENCE"

    return metrics
