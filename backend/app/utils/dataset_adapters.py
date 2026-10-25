"""
Dataset Adapters for converting external human pose datasets into the
standardized platform landmark schema for biomechanical analysis.

Standard schema expected by biomechanics processor:
List[Dict]:
  - name: str (e.g. "left_hip", "left_knee", "left_ankle", "left_shoulder", "right_hip", etc.)
  - x: float (normalized 0.0 to 1.0)
  - y: float (normalized 0.0 to 1.0)
  - z: float (optional depth in normalized units or meters)
  - visibility: float (0.0 to 1.0)
"""

from typing import Dict, Any, List, Optional
from app.core.dataset_registry import DATASET_REGISTRY

COCO_INDEX_MAP = {
    0: "nose",
    1: "left_eye",
    2: "right_eye",
    3: "left_ear",
    4: "right_ear",
    5: "left_shoulder",
    6: "right_shoulder",
    7: "left_elbow",
    8: "right_elbow",
    9: "left_wrist",
    10: "right_wrist",
    11: "left_hip",
    12: "right_hip",
    13: "left_knee",
    14: "right_knee",
    15: "left_ankle",
    16: "right_ankle",
}

MPII_INDEX_MAP = {
    0: "right_ankle",
    1: "right_knee",
    2: "right_hip",
    3: "left_hip",
    4: "left_knee",
    5: "left_ankle",
    6: "pelvis",
    7: "thorax",
    8: "upper_neck",
    9: "head_top",
    10: "right_wrist",
    11: "right_elbow",
    12: "right_shoulder",
    13: "left_shoulder",
    14: "left_elbow",
    15: "left_wrist",
}

H36M_17_INDEX_MAP = {
    0: "pelvis",
    1: "right_hip",
    2: "right_knee",
    3: "right_ankle",
    4: "left_hip",
    5: "left_knee",
    6: "left_ankle",
    7: "spine",
    8: "thorax",
    9: "neck",
    10: "head",
    11: "left_shoulder",
    12: "left_elbow",
    13: "left_wrist",
    14: "right_shoulder",
    15: "right_elbow",
    16: "right_wrist",
}

SPORTSPOSE_NAME_MAP = {
    "left_hip": "left_hip",
    "right_hip": "right_hip",
    "left_knee": "left_knee",
    "right_knee": "right_knee",
    "left_ankle": "left_ankle",
    "right_ankle": "right_ankle",
    "left_shoulder": "left_shoulder",
    "right_shoulder": "right_shoulder",
    "left_elbow": "left_elbow",
    "right_elbow": "right_elbow",
    "left_wrist": "left_wrist",
    "right_wrist": "right_wrist",
    "neck": "neck",
    "head": "head",
    "left_heel": "left_heel",
    "right_heel": "right_heel",
    "left_toe": "left_foot_index",
    "right_toe": "right_foot_index",
}

def convert_coco_keypoints(keypoints: List[float], width: float = 640.0, height: float = 480.0) -> List[Dict[str, Any]]:
    """
    Converts COCO format [x1, y1, v1, x2, y2, v2, ...] to standard landmarks list.
    v is visibility: 0=unlabeled, 1=occluded, 2=visible.
    """
    landmarks = []
    num_pts = min(17, len(keypoints) // 3)
    for i in range(num_pts):
        name = COCO_INDEX_MAP.get(i)
        if not name:
            continue
        x = keypoints[i * 3]
        y = keypoints[i * 3 + 1]
        v = keypoints[i * 3 + 2]
        
        # Normalize if in pixel coords
        norm_x = (x / width) if x > 1.0 else x
        norm_y = (y / height) if y > 1.0 else y
        vis = 1.0 if v == 2 else 0.5 if v == 1 else 0.0
        
        landmarks.append({
            "name": name,
            "x": round(float(norm_x), 4),
            "y": round(float(norm_y), 4),
            "z": 0.0,
            "visibility": vis
        })
    return landmarks

def convert_mpii_joints(joints: List[List[float]], width: float = 640.0, height: float = 480.0) -> List[Dict[str, Any]]:
    """
    Converts MPII 16 joints [[x, y, [vis]], ...] to standard landmarks list.
    """
    landmarks = []
    for i, pt in enumerate(joints[:16]):
        name = MPII_INDEX_MAP.get(i)
        if not name:
            continue
        x = pt[0]
        y = pt[1]
        vis = pt[2] if len(pt) > 2 else 1.0
        
        norm_x = (x / width) if x > 1.0 else x
        norm_y = (y / height) if y > 1.0 else y
        
        landmarks.append({
            "name": name,
            "x": round(float(norm_x), 4),
            "y": round(float(norm_y), 4),
            "z": 0.0,
            "visibility": round(float(vis), 2)
        })
    return landmarks

def convert_human36m_joints(joints_3d: List[List[float]], is_normalized: bool = False) -> List[Dict[str, Any]]:
    """
    Converts Human3.6M 17 3D joints [[x, y, z], ...] to standard landmarks list.
    Coordinates can be in millimeters/meters centered at pelvis or normalized.
    """
    landmarks = []
    for i, pt in enumerate(joints_3d[:17]):
        name = H36M_17_INDEX_MAP.get(i)
        if not name:
            continue
        x = pt[0]
        y = pt[1]
        z = pt[2] if len(pt) > 2 else 0.0
        
        # If in millimeter/meter coordinate space, convert to normalized unit sphere
        if not is_normalized and (abs(x) > 1.0 or abs(y) > 1.0):
            # Typical H36M is +/- 1000mm from root
            norm_x = (x + 1000.0) / 2000.0
            norm_y = (y + 1000.0) / 2000.0
            norm_z = z / 2000.0
        else:
            norm_x = x
            norm_y = y
            norm_z = z
            
        landmarks.append({
            "name": name,
            "x": round(float(max(0.0, min(1.0, norm_x))), 4),
            "y": round(float(max(0.0, min(1.0, norm_y))), 4),
            "z": round(float(norm_z), 4),
            "visibility": 1.0
        })
    return landmarks

def convert_sportspose_frame(sports_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Converts SportsPose keypoint dictionary to standard landmarks list.
    """
    landmarks = []
    keypoints = sports_dict.get("keypoints", {})
    for sp_name, coords in keypoints.items():
        std_name = SPORTSPOSE_NAME_MAP.get(sp_name, sp_name)
        x = coords.get("x", 0.0)
        y = coords.get("y", 0.0)
        z = coords.get("z", 0.0)
        vis = coords.get("visibility", 1.0)
        
        landmarks.append({
            "name": std_name,
            "x": round(float(x), 4),
            "y": round(float(y), 4),
            "z": round(float(z), 4),
            "visibility": round(float(vis), 2)
        })
    return landmarks

def generate_sample_dataset_payload(dataset_id: str) -> Dict[str, Any]:
    """
    Generates synthetic realistic sample benchmark frames for testing and development.
    """
    if dataset_id == "coco":
        # 17 keypoints: [x, y, v, ...] for a standing athletic pose
        return {
            "dataset": "coco",
            "frame_index": 0,
            "image_dimensions": {"width": 640, "height": 480},
            "keypoints": [
                320, 80, 2,   # nose
                310, 75, 2,   # left_eye
                330, 75, 2,   # right_eye
                295, 80, 2,   # left_ear
                345, 80, 2,   # right_ear
                280, 140, 2,  # left_shoulder
                360, 140, 2,  # right_shoulder
                260, 210, 2,  # left_elbow
                380, 210, 2,  # right_elbow
                250, 280, 2,  # left_wrist
                390, 280, 2,  # right_wrist
                290, 270, 2,  # left_hip
                350, 270, 2,  # right_hip
                285, 360, 2,  # left_knee
                355, 360, 2,  # right_knee
                280, 440, 2,  # left_ankle
                360, 440, 2,  # right_ankle
            ]
        }
    elif dataset_id == "mpii":
        return {
            "dataset": "mpii",
            "frame_index": 0,
            "activity_name": "squatting / conditioning",
            "activity_code": "02020",
            "joints": [
                [360, 440, 1.0],  # 0: right_ankle
                [355, 360, 1.0],  # 1: right_knee
                [350, 270, 1.0],  # 2: right_hip
                [290, 270, 1.0],  # 3: left_hip
                [285, 360, 1.0],  # 4: left_knee
                [280, 440, 1.0],  # 5: left_ankle
                [320, 270, 1.0],  # 6: pelvis
                [320, 160, 1.0],  # 7: thorax
                [320, 100, 1.0],  # 8: upper_neck
                [320, 60, 1.0],   # 9: head_top
                [390, 280, 1.0],  # 10: right_wrist
                [380, 210, 1.0],  # 11: right_elbow
                [360, 140, 1.0],  # 12: right_shoulder
                [280, 140, 1.0],  # 13: left_shoulder
                [260, 210, 1.0],  # 14: left_elbow
                [250, 280, 1.0],  # 15: left_wrist
            ]
        }
    elif dataset_id == "human36m":
        return {
            "dataset": "human36m",
            "subject": "S1",
            "action": "Directions",
            "subaction": "1",
            "frame_index": 120,
            "joints_3d_mm": [
                [0.0, 0.0, 0.0],        # 0: pelvis
                [132.0, -18.0, 45.0],   # 1: right_hip
                [145.0, -20.0, -420.0], # 2: right_knee
                [140.0, -25.0, -840.0], # 3: right_ankle
                [-132.0, -18.0, 45.0],  # 4: left_hip
                [-145.0, -20.0, -420.0],# 5: left_knee
                [-140.0, -25.0, -840.0],# 6: left_ankle
                [0.0, 5.0, 230.0],      # 7: spine
                [0.0, 10.0, 480.0],     # 8: thorax
                [0.0, 12.0, 560.0],     # 9: neck
                [0.0, 15.0, 680.0],     # 10: head
                [-185.0, 10.0, 450.0],  # 11: left_shoulder
                [-280.0, 15.0, 200.0],  # 12: left_elbow
                [-320.0, 20.0, -50.0],  # 13: left_wrist
                [185.0, 10.0, 450.0],   # 14: right_shoulder
                [280.0, 15.0, 200.0],   # 15: right_elbow
                [320.0, 20.0, -50.0],   # 16: right_wrist
            ]
        }
    elif dataset_id == "sportspose":
        return {
            "dataset": "sportspose",
            "activity": "drop_jump_landing",
            "fps": 120,
            "frame_index": 45,
            "keypoints": {
                "head": {"x": 0.50, "y": 0.12, "z": 0.0, "visibility": 0.99},
                "neck": {"x": 0.50, "y": 0.20, "z": 0.0, "visibility": 0.99},
                "left_shoulder": {"x": 0.42, "y": 0.25, "z": -0.05, "visibility": 0.98},
                "right_shoulder": {"x": 0.58, "y": 0.25, "z": 0.05, "visibility": 0.98},
                "left_elbow": {"x": 0.38, "y": 0.38, "z": -0.04, "visibility": 0.95},
                "right_elbow": {"x": 0.62, "y": 0.38, "z": 0.04, "visibility": 0.95},
                "left_wrist": {"x": 0.36, "y": 0.50, "z": -0.02, "visibility": 0.95},
                "right_wrist": {"x": 0.64, "y": 0.50, "z": 0.02, "visibility": 0.95},
                "pelvis": {"x": 0.50, "y": 0.50, "z": 0.0, "visibility": 0.99},
                "left_hip": {"x": 0.44, "y": 0.52, "z": -0.03, "visibility": 0.98},
                "right_hip": {"x": 0.56, "y": 0.52, "z": 0.03, "visibility": 0.98},
                "left_knee": {"x": 0.45, "y": 0.70, "z": -0.02, "visibility": 0.98},
                "right_knee": {"x": 0.55, "y": 0.70, "z": 0.02, "visibility": 0.98},
                "left_ankle": {"x": 0.43, "y": 0.88, "z": 0.0, "visibility": 0.98},
                "right_ankle": {"x": 0.57, "y": 0.88, "z": 0.0, "visibility": 0.98},
                "left_heel": {"x": 0.42, "y": 0.91, "z": 0.05, "visibility": 0.92},
                "right_heel": {"x": 0.58, "y": 0.91, "z": 0.05, "visibility": 0.92},
                "left_toe": {"x": 0.44, "y": 0.93, "z": -0.08, "visibility": 0.92},
                "right_toe": {"x": 0.56, "y": 0.93, "z": -0.08, "visibility": 0.92},
            }
        }
    elif dataset_id == "fifa_reference":
        return DATASET_REGISTRY["fifa_reference"]
    else:
        raise ValueError(f"Unknown dataset_id: {dataset_id}")

def evaluate_fifa_risk_compliance(observed_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates kinematic metrics against the FIFA 11+ and F-MARC clinical criteria.
    """
    fifa_rules = DATASET_REGISTRY["fifa_reference"]["risk_factors"]
    evaluations = []
    
    # 1. Trunk Lean Check
    trunk_lean = observed_metrics.get("trunk_lean")
    if trunk_lean is not None:
        rule = fifa_rules["trunk_lean"]
        if trunk_lean > rule["high_risk_deg"]:
            risk_level = "HIGH_RISK"
        elif trunk_lean > rule["moderate_risk_deg"]:
            risk_level = "MODERATE_RISK"
        else:
            risk_level = "NORMAL_LOW_RISK"
            
        evaluations.append({
            "factor_key": "trunk_lean",
            "name": rule["name"],
            "observed_value": round(trunk_lean, 1),
            "unit": "degrees",
            "threshold_target": f"<= {rule['target_threshold_deg']}°",
            "risk_level": risk_level,
            "primary_injury_risk": rule["primary_injury_risk"],
            "intervention_protocol": rule["intervention_protocol"]
        })

    # 2. Limb Asymmetry Check
    l_knee = observed_metrics.get("left_knee_angle")
    r_knee = observed_metrics.get("right_knee_angle")
    if l_knee is not None and r_knee is not None:
        asymmetry_diff = abs(l_knee - r_knee)
        rule = fifa_rules["limb_symmetry_index"]
        if asymmetry_diff > rule["high_risk_pct"]:
            risk_level = "HIGH_RISK"
        elif asymmetry_diff > rule["moderate_risk_pct"]:
            risk_level = "MODERATE_RISK"
        else:
            risk_level = "NORMAL_LOW_RISK"
            
        evaluations.append({
            "factor_key": "limb_symmetry",
            "name": rule["name"],
            "observed_value": round(asymmetry_diff, 1),
            "unit": "degrees discrepancy",
            "threshold_target": f"<= {rule['target_threshold_pct']}°",
            "risk_level": risk_level,
            "primary_injury_risk": rule["primary_injury_risk"],
            "intervention_protocol": rule["intervention_protocol"]
        })
        
    return {
        "clinical_reference": "FIFA 11+ / F-MARC Clinical Injury Prevention Standards",
        "total_factors_evaluated": len(evaluations),
        "factors": evaluations,
        "overall_fifa_compliance": "SATISFACTORY" if all(e["risk_level"] == "NORMAL_LOW_RISK" for e in evaluations) else "NEEDS_INTERVENTION"
    }
