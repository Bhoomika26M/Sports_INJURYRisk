"""
Demo Script for Sports Injury Risk Detection Pipeline

This script executes the complete Milestone 2 pipeline:
Video → OpenCV → YOLO11n → ByteTrack → ROI → BlazePose →
Coordinate Mapping → Smoothing → Normalization → Movement Segmentation →
Biomechanics → Movement Quality → Report

Usage:
    python scripts/run_demo.py --input sample_video.mp4 --activity squat --output outputs/demo
"""

import argparse
import json
import sys
from pathlib import Path
import time
import numpy as np

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.processing.video_processor import VideoProcessor
from app.detection.yolo11 import YOLO11Detector
from app.tracking.yolo_tracker import YOLOTracker
from app.processing.roi import ROICropper
from app.pose.mediapipe_pose import MediaPipeBlazePoseEstimator
from app.processing.smoothing import TemporalSmoother
from app.processing.normalization import SkeletonNormalizer
from app.biomechanics.calculator import BiomechanicsCalculator
from app.movement.segmentation import MovementSegmenter
from app.movement.change_analysis import MovementChangeAnalyzer
from app.visualization.skeleton_renderer import SkeletonRenderer
from app.services.video_annotation_service import VideoAnnotationService
from app.reports.html_generator import HTMLReportGenerator
from app.pose.estimator import Keypoint


def run_demo(input_video: str, activity: str, output_dir: str):
    """
    Run the complete demo pipeline.
    
    Args:
        input_video: Path to input video
        activity: Activity type (squat, jump, running)
        output_dir: Output directory for results
    """
    print("=" * 60)
    print("Sports Injury Risk Detection - Milestone 2 Demo")
    print("=" * 60)
    print(f"Input: {input_video}")
    print(f"Activity: {activity}")
    print(f"Output: {output_dir}")
    print()
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    (output_path / "frames").mkdir(exist_ok=True)
    (output_path / "metrics").mkdir(exist_ok=True)
    
    # Initialize components
    print("Initializing pipeline components...")
    detector = YOLO11Detector()
    tracker = YOLOTracker()
    roi_cropper = ROICropper(padding_percent=0.15)
    pose_estimator = MediaPipeBlazePoseEstimator()
    smoother = TemporalSmoother(window_length=5, polyorder=2)
    normalizer = SkeletonNormalizer()
    biomechanics = BiomechanicsCalculator()
    movement_segmenter = MovementSegmenter()
    movement_change_analyzer = MovementChangeAnalyzer()
    skeleton_renderer = SkeletonRenderer()
    annotation_service = VideoAnnotationService()
    report_generator = HTMLReportGenerator()
    
    print("✓ Components initialized")
    print()
    
    # Open video
    print("Opening video...")
    video_path = Path(input_video)
    if not video_path.exists():
        print(f"ERROR: Video not found: {input_video}")
        return
    
    with VideoProcessor(str(video_path)) as processor:
        print(f"✓ Video opened: {processor.metadata.width}x{processor.metadata.height} @ {processor.metadata.fps:.2f} FPS")
        print(f"  Duration: {processor.metadata.duration:.2f}s, Frames: {processor.metadata.frame_count}")
        print()
        
        # Process video
        print("Processing video through pipeline...")
        print("  Step 1: YOLO11n detection → ByteTrack tracking")
        print("  Step 2: ROI cropping with padding")
        print("  Step 3: BlazePose pose estimation")
        print("  Step 4: Coordinate mapping to original frame")
        print("  Step 5: Temporal smoothing")
        print("  Step 6: Skeleton normalization")
        print("  Step 7: Movement segmentation")
        print("  Step 8: Biomechanical calculations")
        print("  Step 9: Movement quality scoring")
        print("  Step 10: Movement-change analysis")
        print()
        
        start_time = time.time()
        
        # Collect data
        frames_data = []
        keypoints_sequence = []
        timestamps = []
        tracking_data = []
        roi_data = []
        
        # Performance metrics
        detector_calls = 0
        pose_frames = 0
        valid_pose_frames = 0
        
        # Track primary athlete
        track_id_counts = {}
        
        for frame_idx, frame in processor.sample_frames(target_fps=30):
            timestamp = frame_idx / processor.metadata.fps
            timestamps.append(timestamp)
            
            # 1. YOLO11n detection
            detector_calls += 1
            detections = detector.detect(frame)
            
            # 2. ByteTrack tracking
            tracked_objects = tracker.update(frame, frame_idx, timestamp)
            
            # Store tracking data
            frame_tracking = [obj.to_dict() for obj in tracked_objects]
            tracking_data.append({
                "frame": frame_idx,
                "timestamp": timestamp,
                "tracked_objects": frame_tracking
            })
            
            # Count track IDs
            for obj in tracked_objects:
                track_id_counts[obj.track_id] = track_id_counts.get(obj.track_id, 0) + 1
            
            # Select primary athlete
            primary_track_id = None
            if track_id_counts:
                primary_track_id = max(track_id_counts, key=track_id_counts.get)
            
            # Get primary bounding box
            primary_bbox = None
            for obj in tracked_objects:
                if obj.track_id == primary_track_id:
                    primary_bbox = obj.bbox
                    break
            
            if primary_bbox is None:
                frames_data.append({
                    "frame": frame_idx,
                    "timestamp": timestamp,
                    "keypoints": [],
                    "bbox": None,
                    "track_id": None,
                    "roi_bbox": None
                })
                keypoints_sequence.append([])
                roi_data.append(None)
                continue
            
            # 3. Expand bbox with padding
            expanded_bbox = roi_cropper.expand_bbox(
                primary_bbox,
                processor.metadata.width,
                processor.metadata.height
            )
            
            # 4. Crop ROI
            roi_frame = roi_cropper.crop_roi(frame, expanded_bbox)
            
            roi_data.append({
                "frame": frame_idx,
                "original_bbox": primary_bbox,
                "expanded_bbox": expanded_bbox,
                "roi_width": expanded_bbox[2] - expanded_bbox[0],
                "roi_height": expanded_bbox[3] - expanded_bbox[1]
            })
            
            # 5. BlazePose on ROI
            pose_frames += 1
            roi_keypoints = pose_estimator.estimate(roi_frame)
            
            if roi_keypoints:
                valid_pose_frames += 1
            
            # 6. Map keypoints back to original frame
            mapped_keypoints = _map_keypoints_to_original(
                roi_keypoints,
                expanded_bbox,
                roi_frame.shape[1],
                roi_frame.shape[0]
            )
            
            keypoints_sequence.append(mapped_keypoints)
            
            frames_data.append({
                "frame": frame_idx,
                "timestamp": timestamp,
                "keypoints": [kp.to_dict() for kp in mapped_keypoints],
                "bbox": primary_bbox,
                "track_id": primary_track_id,
                "roi_bbox": expanded_bbox
            })
        
        print(f"✓ Processed {len(frames_data)} frames")
        print()
        
        # 7. Temporal smoothing
        print("Applying temporal smoothing...")
        smoothed_keypoints = smoother.smooth_keypoints(keypoints_sequence)
        print("✓ Smoothing complete")
        print()
        
        # 8. Normalization
        print("Normalizing skeleton...")
        normalized_keypoints = normalizer.normalize_sequence(smoothed_keypoints)
        print("✓ Normalization complete")
        print()
        
        # Calculate pose quality
        pose_quality = _calculate_pose_quality(keypoints_sequence)
        
        # 9. Biomechanics
        print("Calculating biomechanics...")
        biomechanics_results = _calculate_biomechanics(
            normalized_keypoints,
            timestamps,
            pose_quality
        )
        print("✓ Biomechanics complete")
        print()
        
        # 10. Movement segmentation
        print(f"Segmenting {activity} movements...")
        if activity == "squat":
            movement_windows = movement_segmenter.segment_squat(normalized_keypoints, timestamps)
        elif activity == "jump":
            movement_windows = movement_segmenter.segment_jump_landing(normalized_keypoints, timestamps)
        elif activity == "running":
            movement_windows = movement_segmenter.segment_running(normalized_keypoints, timestamps)
        else:
            movement_windows = []
        
        print(f"✓ Detected {len(movement_windows)} movement windows")
        print()
        
        # 11. Movement-change analysis
        print("Analyzing movement changes (early vs late)...")
        if len(movement_windows) >= 3:
            movement_change_analysis = movement_change_analyzer.analyze_movement_change(
                movement_windows,
                normalized_keypoints,
                timestamps
            )
            print("✓ Movement-change analysis complete")
        else:
            movement_change_analysis = {
                "status": "insufficient_data",
                "message": f"Need at least 3 repetitions, got {len(movement_windows)}"
            }
            print("⚠ Insufficient data for movement-change analysis")
        print()
        
        processing_time = time.time() - start_time
        print(f"Total processing time: {processing_time:.2f}s")
        print(f"Processing FPS: {len(frames_data) / processing_time:.2f}")
        print()
        
        # Save results
        print("Saving results...")
        
        # Save analysis.json
        analysis_data = {
            "video": {
                "filename": video_path.name,
                "duration": processor.metadata.duration,
                "fps": processor.metadata.fps,
                "width": processor.metadata.width,
                "height": processor.metadata.height,
                "activity": activity
            },
            "pose_analysis": {
                "pose_model": pose_estimator.get_model_name(),
                "pose_model_version": pose_estimator.get_model_version(),
                "total_frames": processor.metadata.frame_count,
                "processed_frames": len(frames_data),
                "pose_quality": pose_quality,
                "keypoints_data": frames_data,
                "tracking_data": tracking_data,
                "roi_data": roi_data,
                "movement_change_analysis": movement_change_analysis
            },
            "biomechanical_analysis": biomechanics_results,
            "movement_windows": movement_windows
        }
        
        with open(output_path / "analysis.json", 'w') as f:
            json.dump(analysis_data, f, indent=2)
        print("✓ Saved analysis.json")
        
        # Save biomechanics.json
        with open(output_path / "biomechanics.json", 'w') as f:
            json.dump(biomechanics_results, f, indent=2)
        print("✓ Saved biomechanics.json")
        
        # Save movement_windows.json
        with open(output_path / "movement_windows.json", 'w') as f:
            json.dump(movement_windows, f, indent=2)
        print("✓ Saved movement_windows.json")
        
        # Save performance.json
        performance_data = {
            "processing_time": processing_time,
            "processed_fps": len(frames_data) / processing_time,
            "video_fps": processor.metadata.fps,
            "detector_calls": detector_calls,
            "tracking_ids": len(track_id_counts),
            "pose_frames": pose_frames,
            "valid_pose_frames": valid_pose_frames,
            "mean_pose_confidence": pose_quality.get("mean_confidence", 0.0)
        }
        
        with open(output_path / "performance.json", 'w') as f:
            json.dump(performance_data, f, indent=2)
        print("✓ Saved performance.json")
        
        # Generate annotated video
        print("Generating annotated video...")
        annotated_result = annotation_service.generate_annotated_video(
            input_video_path=str(video_path),
            output_video_path=str(output_path / "annotated_video.mp4"),
            keypoints_data=frames_data,
            tracking_data=tracking_data,
            roi_data=roi_data,
            biomechanics_data=biomechanics_results,
            fps=processor.metadata.fps
        )
        print(f"✓ Generated annotated video: {annotated_result['frames_annotated']} frames")
        
        # Extract sample frames
        print("Extracting sample frames...")
        sample_frames = annotation_service.extract_sample_frames(
            input_video_path=str(video_path),
            output_dir=str(output_path / "frames"),
            keypoints_data=frames_data,
            tracking_data=tracking_data,
            num_samples=10
        )
        print(f"✓ Extracted {len(sample_frames)} sample frames")
        
        # Generate HTML report
        print("Generating HTML report...")
        report_path = report_generator.generate(
            video_data=analysis_data["video"],
            pose_analysis=analysis_data["pose_analysis"],
            biomechanics=biomechanics_results,
            movement_windows=movement_windows,
            output_path=str(output_path / "report.html")
        )
        print(f"✓ Generated HTML report: {report_path}")
        
        print()
        print("=" * 60)
        print("Demo Complete!")
        print("=" * 60)
        print(f"Output directory: {output_dir}")
        print(f"  - annotated_video.mp4")
        print(f"  - analysis.json")
        print(f"  - biomechanics.json")
        print(f"  - movement_windows.json")
        print(f"  - performance.json")
        print(f"  - report.html")
        print(f"  - frames/ (sample annotated frames)")
        print()
        print("Open report.html in a browser to view the full analysis.")


def _map_keypoints_to_original(
    roi_keypoints: list,
    roi_bbox: tuple,
    roi_width: int,
    roi_height: int
) -> list:
    """Map keypoints from ROI to original frame coordinates."""
    x1_roi, y1_roi, x2_roi, y2_roi = roi_bbox
    roi_actual_width = x2_roi - x1_roi
    roi_actual_height = y2_roi - y1_roi
    
    mapped_keypoints = []
    
    for kp in roi_keypoints:
        scale_x = roi_actual_width / roi_width
        scale_y = roi_actual_height / roi_height
        
        x_original = x1_roi + kp.x * scale_x
        y_original = y1_roi + kp.y * scale_y
        
        mapped_kp = Keypoint(
            x=x_original,
            y=y_original,
            confidence=kp.confidence,
            name=kp.name
        )
        mapped_keypoints.append(mapped_kp)
    
    return mapped_keypoints


def _calculate_pose_quality(keypoints_sequence: list) -> dict:
    """Calculate pose quality metrics."""
    total_frames = len(keypoints_sequence)
    valid_frames = 0
    total_confidence = 0.0
    confidence_count = 0
    
    for frame_keypoints in keypoints_sequence:
        frame_valid = True
        
        for kp in frame_keypoints:
            total_confidence += kp.confidence
            confidence_count += 1
            
            if kp.confidence < 0.3:
                frame_valid = False
        
        if frame_valid:
            valid_frames += 1
    
    mean_confidence = total_confidence / confidence_count if confidence_count > 0 else 0.0
    
    return {
        "valid_frames": valid_frames,
        "low_confidence_frames": total_frames - valid_frames,
        "mean_confidence": mean_confidence,
        "quality_percentage": (valid_frames / total_frames * 100) if total_frames > 0 else 0.0
    }


def _calculate_biomechanics(keypoints_sequence: list, timestamps: list, pose_quality: dict) -> dict:
    """Calculate biomechanical features."""
    biomechanics = BiomechanicsCalculator()
    
    left_knee_angles = []
    right_knee_angles = []
    trunk_lean_angles = []
    
    for frame_keypoints in keypoints_sequence:
        left_knee_angles.append(biomechanics.calculate_knee_angle(frame_keypoints, "left"))
        right_knee_angles.append(biomechanics.calculate_knee_angle(frame_keypoints, "right"))
        trunk_lean_angles.append(biomechanics.calculate_trunk_lean(frame_keypoints))
    
    # Calculate ROM
    joint_angles = {
        "knee_left": biomechanics.calculate_rom(left_knee_angles),
        "knee_right": biomechanics.calculate_rom(right_knee_angles)
    }
    
    # Calculate symmetry
    symmetry = {
        "knee_asymmetry": biomechanics.calculate_asymmetry(left_knee_angles, right_knee_angles)
    }
    
    # Calculate trunk lean
    valid_trunk_lean = [a for a in trunk_lean_angles if a is not None]
    trunk_lean = None
    if valid_trunk_lean:
        trunk_lean = {
            "mean": float(np.mean(valid_trunk_lean)),
            "max": float(np.max(valid_trunk_lean)),
            "min": float(np.min(valid_trunk_lean))
        }
    
    # Calculate movement quality
    movement_quality = _calculate_movement_quality(
        left_knee_angles,
        right_knee_angles,
        trunk_lean_angles,
        pose_quality
    )
    
    return {
        "joint_angles": joint_angles,
        "symmetry": symmetry,
        "trunk_lean": trunk_lean,
        "movement_quality": movement_quality
    }


def _calculate_movement_quality(
    left_knee_angles: list,
    right_knee_angles: list,
    trunk_lean_angles: list,
    pose_quality: dict
) -> dict:
    """Calculate movement quality score."""
    weights = {
        "confidence": 0.15,
        "symmetry": 0.20,
        "alignment": 0.20,
        "stability": 0.15,
        "rom": 0.15,
        "smoothness": 0.15
    }
    
    component_scores = {}
    
    # Confidence
    component_scores["confidence"] = pose_quality.get("quality_percentage", 0.0)
    
    # Symmetry
    valid_left = [a for a in left_knee_angles if a is not None]
    valid_right = [a for a in right_knee_angles if a is not None]
    
    if valid_left and valid_right:
        min_len = min(len(valid_left), len(valid_right))
        differences = [abs(valid_left[i] - valid_right[i]) for i in range(min_len)]
        max_asymmetry = max(differences) if differences else 0
        component_scores["symmetry"] = max(0, 100 - max_asymmetry * 2)
    else:
        component_scores["symmetry"] = 50.0
    
    # Alignment (trunk lean)
    valid_trunk = [a for a in trunk_lean_angles if a is not None]
    if valid_trunk:
        max_lean = max([abs(a) for a in valid_trunk])
        component_scores["alignment"] = max(0, 100 - max_lean * 5)
    else:
        component_scores["alignment"] = 50.0
    
    # Stability
    if valid_left:
        std_dev = np.std(valid_left)
        component_scores["stability"] = max(0, 100 - std_dev * 2)
    else:
        component_scores["stability"] = 50.0
    
    # ROM
    if valid_left:
        rom = max(valid_left) - min(valid_left)
        if 80 <= rom <= 130:
            component_scores["rom"] = 100
        else:
            component_scores["rom"] = max(0, 100 - abs(rom - 105) * 2)
    else:
        component_scores["rom"] = 50.0
    
    # Smoothness
    if len(valid_left) > 1:
        diffs = [abs(valid_left[i+1] - valid_left[i]) for i in range(len(valid_left)-1)]
        component_scores["smoothness"] = max(0, 100 - np.std(diffs) * 5)
    else:
        component_scores["smoothness"] = 50.0
    
    # Calculate weighted score
    overall_score = (
        component_scores["confidence"] * weights["confidence"] +
        component_scores["symmetry"] * weights["symmetry"] +
        component_scores["alignment"] * weights["alignment"] +
        component_scores["stability"] * weights["stability"] +
        component_scores["rom"] * weights["rom"] +
        component_scores["smoothness"] * weights["smoothness"]
    )
    
    return {
        "score": float(overall_score),
        "components": {k: float(v) for k, v in component_scores.items()},
        "weights": weights,
        "raw_measurements": {
            "mean_left_knee": float(np.mean(valid_left)) if valid_left else None,
            "mean_right_knee": float(np.mean(valid_right)) if valid_right else None,
            "max_trunk_lean": float(max([abs(a) for a in valid_trunk])) if valid_trunk else None
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Run Milestone 2 demo pipeline")
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to input video"
    )
    parser.add_argument(
        "--activity",
        type=str,
        required=True,
        choices=["squat", "jump", "running"],
        help="Activity type"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="outputs/demo",
        help="Output directory"
    )
    
    args = parser.parse_args()
    
    run_demo(args.input, args.activity, args.output)


if __name__ == "__main__":
    main()
