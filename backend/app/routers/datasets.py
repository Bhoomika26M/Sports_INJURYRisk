from fastapi import APIRouter
from typing import List, Dict, Any

router = APIRouter(prefix="/datasets", tags=["Sports Biomechanics Datasets"])

BENCHMARK_DATASETS = [
    {
        "id": "human36m",
        "name": "Human3.6M Dataset",
        "category": "3D Human Pose Estimation",
        "purpose": "Human pose estimation, joint tracking, movement analysis",
        "keypoints": 32,
        "sample_activities": ["Walking", "Jogging", "Sitting", "Posing", "Directions", "Greeting"],
        "normative_valgus_mean": "4.2 deg (+- 2.1 deg)",
        "relevance": "Gold standard for 3D markerless joint coordinate ground truth validation."
    },
    {
        "id": "sports_pose",
        "name": "SportsPose Dataset",
        "category": "Sports-Specific Biomechanics",
        "purpose": "Sports-specific movement analysis, athlete posture assessment",
        "keypoints": 24,
        "sample_activities": ["Side-cutting", "Drop Jump Landing", "Sprint Deceleration", "Tennis Serve"],
        "normative_valgus_mean": "5.6 deg (+- 3.4 deg)",
        "relevance": "Biomechanical dataset benchmark for dynamic knee valgus and anterior cruciate ligament risk detection."
    },
    {
        "id": "mpii",
        "name": "MPII Human Pose Dataset",
        "category": "Body Keypoint Detection",
        "purpose": "Body keypoint detection, activity recognition",
        "keypoints": 16,
        "sample_activities": ["Athletic running", "High jump", "Gymnastics", "Football kicking"],
        "normative_valgus_mean": "4.8 deg (+- 2.5 deg)",
        "relevance": "Standard computer vision benchmark for articulation in sports."
    },
    {
        "id": "coco_keypoints",
        "name": "COCO Keypoints Dataset",
        "category": "In-the-Wild Pose Training",
        "purpose": "Pose estimation training, human motion analysis",
        "keypoints": 17,
        "sample_activities": ["Dynamic sports", "Team drills", "Outdoor athletics"],
        "normative_valgus_mean": "5.1 deg (+- 3.0 deg)",
        "relevance": "Foundation model pretraining dataset for multi-person and occluded sports tracking."
    },
    {
        "id": "fifa_injury",
        "name": "FIFA Injury Surveillance Dataset (Reference)",
        "category": "Epidemiology & Injury Risk Modeling",
        "purpose": "Injury trend analysis, risk factor modeling",
        "keypoints": 0,
        "sample_activities": ["Match play", "High-speed deceleration", "Non-contact pressing", "Fixture congestion"],
        "normative_valgus_mean": "Threshold > 15 deg valgus associated with 4.5x higher non-contact ACL incidence",
        "relevance": "Epidemiological validation linking high ACWR (> 1.4) and biomechanical asymmetries (> 15%) to match-day soft-tissue injuries."
    }
]

NORMATIVE_RANGES = {
    "knee_valgus_deg": {
        "healthy_range": "< 8.0 deg",
        "mild_risk": "8.0 - 12.0 deg",
        "high_risk": "12.0 - 15.0 deg",
        "critical_rupture_risk": "> 15.0 deg",
        "clinical_significance": "Excessive dynamic valgus induces knee abduction torque and ACL strain."
    },
    "trunk_lateral_lean_deg": {
        "healthy_range": "< 5.0 deg",
        "mild_risk": "5.0 - 8.0 deg",
        "high_risk": "> 8.0 deg",
        "clinical_significance": "Trunk displacement laterally increases lever arm and ground reaction force through lateral knee compartment."
    },
    "bilateral_asymmetry_pct": {
        "healthy_range": "< 8.0 %",
        "borderline": "8.0 - 15.0 %",
        "pathological": "> 15.0 %",
        "clinical_significance": "Limb asymmetry above 15% during eccentric landing predicts prospective hamstring or ACL strain."
    },
    "acwr_ratio": {
        "under_trained": "< 0.80",
        "sweet_spot": "0.80 - 1.30",
        "danger_zone": "> 1.50",
        "clinical_significance": "Acute-to-Chronic Workload Ratio spikes heighten soft tissue fatigue susceptibility."
    }
}

@router.get("")
def get_datasets():
    return {
        "total_datasets": len(BENCHMARK_DATASETS),
        "datasets": BENCHMARK_DATASETS,
        "normative_benchmarks": NORMATIVE_RANGES
    }
