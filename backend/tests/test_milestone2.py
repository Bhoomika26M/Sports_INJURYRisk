import pytest
import numpy as np
from app.services.biomechanics import (
    calculate_angle_2d,
    calculate_knee_valgus,
    calculate_trunk_lean,
    calculate_asymmetry_index,
    BiomechanicalAnalyzer
)
from app.services.pose_estimator import PoseEstimator
from app.database import SessionLocal
from app.models.analysis import AnalysisRecord
from app.routes.analysis import synthetic_demo_endpoint


def test_calculate_angle_2d_right_angle():
    # Points forming a 90 degree angle at vertex (0, 0)
    p1 = {"x": 1.0, "y": 0.0}
    vertex = {"x": 0.0, "y": 0.0}
    p3 = {"x": 0.0, "y": 1.0}
    
    angle = calculate_angle_2d(p1, vertex, p3)
    assert abs(angle - 90.0) < 0.1


def test_calculate_angle_2d_straight_line():
    # 180 degree straight line
    p1 = {"x": 0.0, "y": 0.0}
    vertex = {"x": 0.0, "y": 1.0}
    p3 = {"x": 0.0, "y": 2.0}
    
    angle = calculate_angle_2d(p1, vertex, p3)
    assert abs(angle - 180.0) < 0.1


def test_knee_valgus_calculation():
    # Straight leg: hip (0.5, 0.2), knee (0.5, 0.5), ankle (0.5, 0.8)
    hip = {"x": 0.5, "y": 0.2}
    knee = {"x": 0.5, "y": 0.5}
    ankle = {"x": 0.5, "y": 0.8}
    valgus_straight = calculate_knee_valgus(hip, knee, ankle, is_left=True)
    assert valgus_straight == 0.0

    # Knee collapsed inward
    knee_valgus = {"x": 0.45, "y": 0.5}
    valgus_angle = calculate_knee_valgus(hip, knee_valgus, ankle, is_left=True)
    assert valgus_angle > 0.0


def test_bilateral_asymmetry_index():
    # Perfect symmetry
    asi_zero = calculate_asymmetry_index(80.0, 80.0)
    assert asi_zero == 0.0

    # 10% asymmetry
    asi = calculate_asymmetry_index(90.0, 80.0)
    # diff = 10, mean = 85, asi = 10 / 85 * 100 = 11.76
    assert abs(asi - 11.76) < 0.1


def test_movement_quality_assessment():
    analyzer = BiomechanicalAnalyzer()
    demo = analyzer.generate_synthetic_biomechanics_demo("SQUAT")
    
    report = demo["quality_report"]
    assert 0 <= report["overall_score"] <= 100
    assert report["grade"] in ["EXCELLENT", "GOOD", "MODERATE_RISK", "HIGH_RISK"]
    assert report["valgus_stability_score"] >= 0
    assert report["symmetry_score"] >= 0
    assert len(report["anomalies"]) > 0


def test_pose_estimator_init_and_frame_inference():
    estimator = PoseEstimator()
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    landmarks = estimator.extract_landmarks(dummy_frame)
    # On a black dummy image, no person should be detected (returns None)
    assert landmarks is None
    estimator.close()


def test_synthetic_demo_database_storage():
    db = SessionLocal()
    demo_res = synthetic_demo_endpoint(movement_type="JUMP_LANDING", athlete_id="ATH001", db=db)
    
    assert demo_res.movement_type == "JUMP_LANDING"
    assert demo_res.athlete_id == "ATH001"
    
    # Verify in DB
    record = db.query(AnalysisRecord).filter(
        AnalysisRecord.athlete_id == "ATH001",
        AnalysisRecord.movement_type == "JUMP_LANDING"
    ).order_by(AnalysisRecord.id.desc()).first()
    
    assert record is not None
    assert record.overall_score == demo_res.quality_report.overall_score
    db.close()
