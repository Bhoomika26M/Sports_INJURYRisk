import os
import json
import shutil
import tempfile
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database import get_db
from app.models.analysis import AnalysisRecord
from app.schemas.analysis import VideoAnalysisResponse, AnalysisRecordOut
from app.services.pose_estimator import PoseEstimator
from app.services.biomechanics import BiomechanicalAnalyzer

router = APIRouter(
    prefix="/analysis",
    tags=["Biomechanical Analysis"]
)

# Initialize singletons
_pose_estimator: Optional[PoseEstimator] = None
_biomechanical_analyzer: Optional[BiomechanicalAnalyzer] = None


def get_pose_estimator() -> PoseEstimator:
    global _pose_estimator
    if _pose_estimator is None:
        _pose_estimator = PoseEstimator()
    return _pose_estimator


def get_biomechanical_analyzer() -> BiomechanicalAnalyzer:
    global _biomechanical_analyzer
    if _biomechanical_analyzer is None:
        _biomechanical_analyzer = BiomechanicalAnalyzer()
    return _biomechanical_analyzer


@router.post("/process-video", response_model=VideoAnalysisResponse)
async def process_video_endpoint(
    file: UploadFile = File(...),
    movement_type: str = Form("SQUAT"),
    athlete_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Upload a video file (MP4/MOV) and execute the full Pose Estimation 
    and Biomechanical Movement Quality assessment pipeline.
    """
    if not file.filename.lower().endswith((".mp4", ".mov", ".avi", ".webm", ".mkv")):
        raise HTTPException(
            status_code=400,
            detail="Unsupported video format. Please upload an MP4, MOV, or WEBM video."
        )

    # Save to temporary storage for processing
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_path = tmp_file.name
        shutil.copyfileobj(file.file, tmp_file)

    try:
        estimator = get_pose_estimator()
        analyzer = get_biomechanical_analyzer()

        # Step 1: Extract 33 3D Pose Keypoints across frames
        video_result = estimator.process_video(tmp_path, max_frames=180, stride=2)

        # Step 2: Compute frame-by-frame joint angles & kinematics
        frames_kinematics = []
        sampled_frames = []

        for frame_data in video_result["frames"]:
            if frame_data["detected"] and frame_data["landmarks"]:
                kinematics = analyzer.analyze_frame(frame_data["landmarks"])
                if kinematics:
                    kinematics["frame_index"] = frame_data["frame_index"]
                    kinematics["timestamp"] = frame_data["timestamp"]
                    frames_kinematics.append(kinematics)
                    sampled_frames.append(kinematics)

        # Step 3: Run Movement Quality Assessment
        quality_report = analyzer.assess_movement_quality(frames_kinematics)

        # Step 4: Persist Analysis Record
        metrics = quality_report["metrics_summary"]
        db_record = AnalysisRecord(
            video_name=file.filename,
            movement_type=movement_type.upper(),
            athlete_id=athlete_id,
            overall_score=quality_report["overall_score"],
            grade=quality_report["grade"],
            valgus_stability_score=quality_report["valgus_stability_score"],
            symmetry_score=quality_report["symmetry_score"],
            rom_score=quality_report["rom_score"],
            posture_score=quality_report["posture_score"],
            peak_valgus=metrics.get("peak_valgus_overall", 0.0),
            mean_asymmetry=metrics.get("mean_asymmetry_index", 0.0),
            peak_flexion=metrics.get("peak_flexion_overall", 0.0),
            peak_trunk_lean=metrics.get("peak_trunk_lean", 0.0),
            anomalies=json.dumps(quality_report["anomalies"])
        )
        db.add(db_record)
        db.commit()
        db.refresh(db_record)

        # Sample every 2nd frame for responsive client rendering
        return VideoAnalysisResponse(
            video_name=file.filename,
            movement_type=movement_type.upper(),
            athlete_id=athlete_id,
            total_frames=video_result["total_video_frames"],
            fps=video_result["fps"],
            duration=video_result["duration"],
            quality_report=quality_report,
            sampled_frames=sampled_frames[::2]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis pipeline error: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


@router.post("/synthetic-demo", response_model=VideoAnalysisResponse)
def synthetic_demo_endpoint(
    movement_type: str = Query("SQUAT", description="Movement pattern e.g. SQUAT, JUMP_LANDING"),
    athlete_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Run instant synthetic biomechanical analysis demonstration without needing a physical camera or video file.
    """
    analyzer = get_biomechanical_analyzer()
    demo_result = analyzer.generate_synthetic_biomechanics_demo(movement_type=movement_type.upper())
    
    quality_report = demo_result["quality_report"]
    metrics = quality_report["metrics_summary"]

    # Persist record in database
    db_record = AnalysisRecord(
        video_name=f"Demo_{movement_type.upper()}.mp4",
        movement_type=movement_type.upper(),
        athlete_id=athlete_id,
        overall_score=quality_report["overall_score"],
        grade=quality_report["grade"],
        valgus_stability_score=quality_report["valgus_stability_score"],
        symmetry_score=quality_report["symmetry_score"],
        rom_score=quality_report["rom_score"],
        posture_score=quality_report["posture_score"],
        peak_valgus=metrics.get("peak_valgus_overall", 0.0),
        mean_asymmetry=metrics.get("mean_asymmetry_index", 0.0),
        peak_flexion=metrics.get("peak_flexion_overall", 0.0),
        peak_trunk_lean=metrics.get("peak_trunk_lean", 0.0),
        anomalies=json.dumps(quality_report["anomalies"])
    )
    db.add(db_record)
    db.commit()
    db.refresh(db_record)

    return VideoAnalysisResponse(
        video_name=f"Demo_{movement_type.upper()}.mp4",
        movement_type=movement_type.upper(),
        athlete_id=athlete_id,
        total_frames=demo_result["total_frames"],
        fps=demo_result["fps"],
        duration=demo_result["duration"],
        quality_report=quality_report,
        sampled_frames=demo_result["sampled_frames"]
    )


@router.get("/records", response_model=List[AnalysisRecordOut])
def get_analysis_records(
    athlete_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Retrieve historical movement assessments.
    """
    query = db.query(AnalysisRecord)
    if athlete_id:
        query = query.filter(AnalysisRecord.athlete_id == athlete_id)
    return query.order_by(AnalysisRecord.created_at.desc()).limit(limit).all()
