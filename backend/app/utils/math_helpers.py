import numpy as np
from typing import Tuple, List, Dict, Any

def calculate_angle_2d(p1: Tuple[float, float], p2: Tuple[float, float], p3: Tuple[float, float]) -> float:
    """
    Calculate angle at vertex p2 formed by (p1, p2, p3) in degrees [0, 180].
    p1: First point (x, y)
    p2: Vertex point (x, y)
    p3: Third point (x, y)
    """
    v1 = np.array([p1[0] - p2[0], p1[1] - p2[1]])
    v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])
    
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
        
    cosine_val = np.dot(v1, v2) / (norm1 * norm2)
    cosine_val = np.clip(cosine_val, -1.0, 1.0)
    angle_rad = np.arccos(cosine_val)
    return float(np.degrees(angle_rad))

def calculate_valgus_angle(hip: Tuple[float, float], knee: Tuple[float, float], ankle: Tuple[float, float], is_left: bool = True) -> float:
    """
    Calculate Frontal Plane Projection Angle (FPPA) / Dynamic Knee Valgus.
    A positive valgus angle denotes medial knee collapse (inward deviation).
    Normal alignment in frontal plane is ~180° (or 0° deviation).
    Valgus > 10°-15° is a proven clinical risk indicator for ACL rupture.
    """
    # 2D frontal plane vector from hip to ankle
    hip_to_ankle = np.array([ankle[0] - hip[0], ankle[1] - hip[1]])
    # Vector from hip to knee
    hip_to_knee = np.array([knee[0] - hip[0], knee[1] - hip[1]])
    
    # Check medial displacement
    # In normalized image coords: x increases to the right.
    # For Left leg (viewer's right or athlete's left): Medial collapse is inward (towards midline).
    # If athlete faces camera: Left leg is on screen's right (larger x). Inward collapse means knee moves left (smaller x).
    # We can measure deviation angle from the collinear line (hip->ankle):
    angle = calculate_angle_2d(hip, knee, ankle)
    # The straight line is 180°. Deviation is abs(180 - angle)
    valgus_deviation = max(0.0, 180.0 - angle)
    return float(round(valgus_deviation, 2))

def calculate_trunk_lean(shoulder_mid: Tuple[float, float], hip_mid: Tuple[float, float]) -> Tuple[float, float]:
    """
    Calculate trunk lateral lean angle (from vertical) in degrees.
    Vertical axis is vector [0, -1] (or [0, 1] depending on origin).
    """
    dx = shoulder_mid[0] - hip_mid[0]
    dy = shoulder_mid[1] - hip_mid[1]
    
    # Lateral lean angle relative to vertical line
    if abs(dy) < 1e-6:
        lateral_lean = 90.0
    else:
        lateral_lean = float(np.degrees(np.arctan(abs(dx) / abs(dy))))
        
    forward_flexion = float(np.degrees(np.arctan(abs(dy) / (abs(dx) + 1e-6))))
    return float(round(lateral_lean, 2)), float(round(forward_flexion, 2))

def calculate_pelvic_tilt(hip_left: Tuple[float, float], hip_right: Tuple[float, float]) -> float:
    """
    Calculate pelvic drop / obliquity angle relative to horizontal plane in degrees.
    """
    dx = hip_right[0] - hip_left[0]
    dy = hip_right[1] - hip_left[1]
    
    if abs(dx) < 1e-6:
        return 90.0
    angle = float(np.degrees(np.arctan(abs(dy) / abs(dx))))
    return float(round(angle, 2))

def calculate_bilateral_asymmetry(left_val: float, right_val: float) -> float:
    """
    Calculate Bilateral Asymmetry Index (BAI) percentage.
    0% = perfect symmetry.
    >15% indicates clinically significant asymmetry and injury vulnerability.
    """
    max_val = max(abs(left_val), abs(right_val))
    if max_val < 1e-6:
        return 0.0
    asymmetry = (abs(left_val - right_val) / max_val) * 100.0
    return float(round(min(asymmetry, 100.0), 2))

def smooth_time_series(values: List[float], window_size: int = 5) -> List[float]:
    """
    Apply simple moving average smoothing to a kinematic time series.
    """
    if len(values) < window_size:
        return values
    smoothed = []
    half_window = window_size // 2
    for i in range(len(values)):
        start = max(0, i - half_window)
        end = min(len(values), i + half_window + 1)
        smoothed.append(float(np.mean(values[start:end])))
    return smoothed
