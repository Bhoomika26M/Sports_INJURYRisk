"""
Dataset Registry for Sports Injury Risk Detection Platform.

This module formalizes the integration of:
1. Human3.6M Dataset (3D human pose, joint tracking, movement analysis)
2. MPII Human Pose Dataset (body keypoint detection, activity recognition)
3. COCO Keypoints Dataset (pose estimation training, human motion analysis)
4. SportsPose Dataset (sports-specific movement analysis, athlete posture)
5. FIFA Injury Reference (FIFA 11+ / F-MARC clinical injury trend analysis & risk modeling)
"""

from typing import Dict, Any, List

DATASET_REGISTRY: Dict[str, Dict[str, Any]] = {
    "human36m": {
        "id": "human36m",
        "name": "Human3.6M Dataset",
        "category": "3D Human Pose Estimation & Kinematics",
        "purposes": [
            "Human pose estimation",
            "3D joint tracking",
            "Movement analysis and range of motion (ROM)"
        ],
        "keypoint_count": 17,
        "keypoint_topology": [
            "Pelvis (Root)", "Right Hip", "Right Knee", "Right Ankle",
            "Left Hip", "Left Knee", "Left Ankle", "Spine",
            "Thorax", "Neck/Nose", "Head", "Left Shoulder",
            "Left Elbow", "Left Wrist", "Right Shoulder", "Right Elbow", "Right Wrist"
        ],
        "coordinate_type": "3D (x, y, z in millimeters/meters relative to pelvis)",
        "clinical_role": "Serves as the 3D ground-truth benchmark for evaluating joint depth inference and angular velocities during complex movement patterns.",
        "licensing": "Academic use only (requires formal university registration).",
        "reference_link": "http://vision.imar.ro/human3.6m/description.php"
    },
    "mpii": {
        "id": "mpii",
        "name": "MPII Human Pose Dataset",
        "category": "2D Body Keypoint Detection & Activity Recognition",
        "purposes": [
            "Body keypoint detection",
            "Activity recognition",
            "Real-world posture diversity testing"
        ],
        "keypoint_count": 16,
        "keypoint_topology": [
            "Right Ankle", "Right Knee", "Right Hip", "Left Hip",
            "Left Knee", "Left Ankle", "Pelvis", "Thorax",
            "Upper Neck", "Head Top", "Right Wrist", "Right Elbow",
            "Right Shoulder", "Left Shoulder", "Left Elbow", "Left Wrist"
        ],
        "activity_classes_count": 410,
        "coordinate_type": "2D (x, y pixel coordinates + visibility scale)",
        "clinical_role": "Provides standardized activity labels and baseline 2D joint topologies across 410 everyday and athletic activities.",
        "licensing": "Non-commercial scientific research.",
        "reference_link": "http://human-pose.mpi-inf.mpg.de/"
    },
    "coco": {
        "id": "coco",
        "name": "COCO Keypoints Dataset",
        "category": "General Pose Estimation Standard",
        "purposes": [
            "Pose estimation training",
            "Human motion analysis",
            "Standard benchmark validation"
        ],
        "keypoint_count": 17,
        "keypoint_topology": [
            "nose", "left_eye", "right_eye", "left_ear", "right_ear",
            "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
            "left_wrist", "right_wrist", "left_hip", "right_hip",
            "left_knee", "right_knee", "left_ankle", "right_ankle"
        ],
        "coordinate_type": "2D (x, y, v where v=0: unannotated, v=1: occluded, v=2: visible)",
        "clinical_role": "Used as the underlying pretraining dataset for pose detection backbones (MediaPipe, YOLOv8-pose). Our adapter maps COCO joints into platform landmarks.",
        "licensing": "Creative Commons Attribution 4.0",
        "reference_link": "https://cocodataset.org/#keypoints-2020"
    },
    "sportspose": {
        "id": "sportspose",
        "name": "SportsPose Dataset",
        "category": "Dynamic Sports Biomechanics",
        "purposes": [
            "Sports-specific movement analysis",
            "Athlete posture assessment",
            "High-velocity dynamic joint kinematics"
        ],
        "keypoint_count": 24,
        "keypoint_topology": [
            "head", "neck", "right_shoulder", "right_elbow", "right_wrist",
            "left_shoulder", "left_elbow", "left_wrist", "pelvis",
            "right_hip", "right_knee", "right_ankle", "right_heel", "right_toe",
            "left_hip", "left_knee", "left_ankle", "left_heel", "left_toe",
            "chest", "mid_spine"
        ],
        "coordinate_type": "3D markerless optical capture (high-speed camera arrays)",
        "clinical_role": "Calibrates dynamic athletic ranges of motion (e.g. max knee flexion velocity, ground contact loading, sprint acceleration trunk lean).",
        "licensing": "Open access for sports science research.",
        "reference_link": "https://sportspose.org"
    },
    "fifa_reference": {
        "id": "fifa_reference",
        "name": "FIFA Injury Dataset & Clinical Reference (FIFA 11+ / F-MARC)",
        "category": "Clinical Injury Prevention & Risk Modeling",
        "purposes": [
            "Injury trend analysis",
            "Risk factor modeling",
            "Clinical threshold establishment"
        ],
        "coordinate_type": "Clinical Kinematic & Kinetic Guidelines",
        "clinical_role": "Establishes validated medical thresholds for ACL tears, hamstring strains, ankle sprains, and valgus collapse.",
        "risk_factors": {
            "knee_valgus": {
                "name": "Dynamic Knee Valgus (Inward Knee Collapse)",
                "description": "Inward deviation of the knee joint relative to the hip and ankle during deceleration or landing.",
                "target_threshold_deg": 10.0,
                "moderate_risk_deg": 18.0,
                "high_risk_deg": 25.0,
                "primary_injury_risk": "Non-contact Anterior Cruciate Ligament (ACL) tear, Patellofemoral Pain Syndrome.",
                "intervention_protocol": "FIFA 11+ Part 2: Dynamic knee alignment jumping, single-leg squats, and hip abductor strengthening."
            },
            "landing_knee_flexion": {
                "name": "Landing Knee Flexion (Stiff Landing)",
                "description": "Angle of knee flexion at initial ground impact during drop jumps or deceleration.",
                "target_threshold_deg": 45.0,
                "moderate_risk_deg": 35.0,
                "high_risk_deg": 25.0,
                "primary_injury_risk": "High ground reaction impact transmission; elevated shear stress across the patellar tendon and ACL.",
                "intervention_protocol": "FIFA 11+ Box jumps and soft landing drills with cueing: 'land softly on the balls of your feet and bend your knees'."
            },
            "trunk_lean": {
                "name": "Lateral / Excessive Forward Trunk Lean",
                "description": "Trunk tilt relative to vertical during single-leg stance or landing tasks.",
                "target_threshold_deg": 15.0,
                "moderate_risk_deg": 22.0,
                "high_risk_deg": 30.0,
                "primary_injury_risk": "Altered center-of-mass trajectory leading to multi-fold increase in knee abduction moment.",
                "intervention_protocol": "FIFA 11+ Core stability exercises: front planks, side planks, and alternating arm/leg raises."
            },
            "limb_symmetry_index": {
                "name": "Limb Symmetry Index (LSI)",
                "description": "Percentage or angular discrepancy between dominant and non-dominant leg during bilateral or unilateral movements.",
                "target_threshold_pct": 10.0,
                "moderate_risk_pct": 15.0,
                "high_risk_pct": 20.0,
                "primary_injury_risk": "Overcompensation injury on contralateral limb; elevated recurrence risk following previous injury.",
                "intervention_protocol": "FIFA 11+ Unilateral balance, single-leg stance with ball passing, and controlled eccentric loading."
            }
        },
        "licensing": "Public clinical guideline by FIFA Medical Assessment and Research Centre (F-MARC).",
        "reference_link": "https://www.fifamedicalnetwork.com"
    }
}
