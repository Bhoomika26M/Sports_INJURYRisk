import numpy as np
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.video import Video, ProcessingStatus
from app.models.pose_analysis import PoseAnalysis
from app.models.biomechanical_analysis import BiomechanicalAnalysis
from app.processing.video_processor import VideoProcessor
from app.pose.mediapipe_pose import MediaPipeBlazePoseEstimator
from app.pose.estimator import Keypoint
from app.processing.smoothing import TemporalSmoother
from app.processing.normalization import SkeletonNormalizer
from app.processing.roi import ROICropper
from app.biomechanics.calculator import BiomechanicsCalculator
from app.detection.yolo11 import YOLO11Detector
from app.tracking.yolo_tracker import YOLOTracker
from app.tracking.base import TrackedObject
from app.core.config import settings
from app.services.video_service import VideoService
from app.services.video_annotation_service import VideoAnnotationService
from app.movement.segmentation import MovementSegmenter
from app.movement.change_analysis import MovementChangeAnalyzer


class VideoProcessingService:
    """
    Main video processing service.
    
    Orchestrates the complete pipeline:
    Video → OpenCV Preprocessing → YOLO11n Detection → ByteTrack Tracking → ROI Crop →
    BlazePose → Coordinate Mapping → Smoothing → Normalization → Biomechanics
    """
    
    def __init__(self):
        self.detector = YOLO11Detector()
        self.tracker = YOLOTracker()
        self.roi_cropper = ROICropper(padding_percent=0.15)
        self.pose_estimator = MediaPipeBlazePoseEstimator()
        self.smoother = TemporalSmoother(window_length=5, polyorder=2)
        self.normalizer = SkeletonNormalizer()
        self.biomechanics = BiomechanicsCalculator()
        self.annotation_service = VideoAnnotationService()
        self.movement_segmenter = MovementSegmenter()
        self.movement_change_analyzer = MovementChangeAnalyzer()
    
    def process_video(self, video_id: int, db: Session, activity: str = "squat") -> Dict:
        """
        Process a video through the complete pipeline.
        
        Pipeline:
        Video → OpenCV → YOLO11n → ByteTrack → ROI → BlazePose →
        Coordinate Mapping → Smoothing → Normalization → Biomechanics
        
        Args:
            video_id: Video ID
            db: Database session
            activity: Activity type (squat, jump, running)
        
        Returns:
            Processing results summary
        """
        # Get video
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise ValueError(f"Video {video_id} not found")
        
        try:
            # Update status
            VideoService.update_processing_status(video_id, ProcessingStatus.PREPROCESSING, db=db)
            
            # Open and preprocess video
            with VideoProcessor(video.storage_path) as processor:
                # Update video metadata
                video.width = processor.metadata.width
                video.height = processor.metadata.height
                video.fps = processor.metadata.fps
                video.duration = processor.metadata.duration
                db.commit()
                
                # Start detection and tracking
                VideoService.update_processing_status(video_id, ProcessingStatus.POSE_ESTIMATION, db=db)
                
                frames_data = []
                keypoints_sequence = []
                timestamps = []
                tracking_data = []
                roi_data = []
                
                # Performance metrics
                detector_calls = 0
                pose_frames = 0
                valid_pose_frames = 0
                
                # Track the primary athlete (most frequent track ID)
                track_id_counts = {}
                
                for frame_idx, frame in processor.sample_frames(target_fps=settings.POSE_FPS):
                    timestamp = frame_idx / processor.metadata.fps
                    timestamps.append(timestamp)
                    
                    # 1. YOLO11n detection
                    detector_calls += 1
                    detections = self.detector.detect(frame)
                    
                    # 2. ByteTrack tracking
                    tracked_objects = self.tracker.update(frame, frame_idx, timestamp)
                    
                    # Store tracking data
                    frame_tracking = [obj.to_dict() for obj in tracked_objects]
                    tracking_data.append({
                        "frame": frame_idx,
                        "timestamp": timestamp,
                        "tracked_objects": frame_tracking
                    })
                    
                    # Count track IDs to find primary athlete
                    for obj in tracked_objects:
                        track_id_counts[obj.track_id] = track_id_counts.get(obj.track_id, 0) + 1
                    
                    # Select primary athlete (most frequent track ID)
                    primary_track_id = None
                    if track_id_counts:
                        primary_track_id = max(track_id_counts, key=track_id_counts.get)
                    
                    # 3. Get primary athlete's bounding box
                    primary_bbox = None
                    for obj in tracked_objects:
                        if obj.track_id == primary_track_id:
                            primary_bbox = obj.bbox
                            break
                    
                    if primary_bbox is None:
                        # No athlete detected, store empty frame data
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
                    
                    # 4. Expand bbox with padding
                    expanded_bbox = self.roi_cropper.expand_bbox(
                        primary_bbox,
                        processor.metadata.width,
                        processor.metadata.height
                    )
                    
                    # 5. Crop ROI
                    roi_frame = self.roi_cropper.crop_roi(frame, expanded_bbox)
                    
                    # Store ROI info
                    roi_data.append({
                        "frame": frame_idx,
                        "original_bbox": primary_bbox,
                        "expanded_bbox": expanded_bbox,
                        "roi_width": expanded_bbox[2] - expanded_bbox[0],
                        "roi_height": expanded_bbox[3] - expanded_bbox[1]
                    })
                    
                    # 6. BlazePose on ROI
                    pose_frames += 1
                    roi_keypoints = self.pose_estimator.estimate(roi_frame)
                    
                    if roi_keypoints:
                        valid_pose_frames += 1
                    
                    # 7. Map keypoints back to original frame coordinates
                    mapped_keypoints = self._map_keypoints_to_original(
                        roi_keypoints,
                        expanded_bbox,
                        roi_frame.shape[1],
                        roi_frame.shape[0]
                    )
                    
                    keypoints_sequence.append(mapped_keypoints)
                    
                    # Store frame data
                    frames_data.append({
                        "frame": frame_idx,
                        "timestamp": timestamp,
                        "keypoints": [kp.to_dict() for kp in mapped_keypoints],
                        "bbox": primary_bbox,
                        "track_id": primary_track_id,
                        "roi_bbox": expanded_bbox
                    })
                
                # Apply temporal smoothing
                smoothed_keypoints = self.smoother.smooth_keypoints(keypoints_sequence)
                
                # Normalize skeleton
                normalized_keypoints = self.normalizer.normalize_sequence(smoothed_keypoints)
                
                # Calculate pose quality metrics
                pose_quality = self._calculate_pose_quality(keypoints_sequence)
                
                # Create pose analysis record
                pose_analysis = PoseAnalysis(
                    video_id=video_id,
                    pose_model=self.pose_estimator.get_model_name(),
                    pose_model_version=self.pose_estimator.get_model_version(),
                    analysis_version="1.0",
                    total_frames=processor.metadata.frame_count,
                    processed_frames=len(frames_data),
                    frame_sample_rate=settings.POSE_FPS,
                    pose_quality=pose_quality,
                    keypoints_data=frames_data,
                    tracking_data=tracking_data,
                    roi_data=roi_data,
                    normalized_skeleton=[
                        [kp.to_dict() for kp in frame]
                        for frame in normalized_keypoints
                    ]
                )
                db.add(pose_analysis)
                db.commit()
                db.refresh(pose_analysis)
                
                # Calculate biomechanics
                VideoService.update_processing_status(video_id, ProcessingStatus.ANALYZING, db=db)
                
                biomechanics_results = self._calculate_biomechanics(
                    normalized_keypoints,
                    timestamps,
                    pose_quality
                )
                
                # Create biomechanical analysis record
                biomechanical_analysis = BiomechanicalAnalysis(
                    pose_analysis_id=pose_analysis.id,
                    **biomechanics_results
                )
                db.add(biomechanical_analysis)
                db.commit()
                
                # Segment movement windows
                from app.models.movement_window import MovementWindow
                
                movement_windows = []
                if activity == "squat":
                    movement_windows = self.movement_segmenter.segment_squat(
                        normalized_keypoints,
                        timestamps
                    )
                elif activity == "jump":
                    movement_windows = self.movement_segmenter.segment_jump_landing(
                        normalized_keypoints,
                        timestamps
                    )
                elif activity == "running":
                    movement_windows = self.movement_segmenter.segment_running(
                        normalized_keypoints,
                        timestamps
                    )
                
                # Save movement windows to database
                for window_data in movement_windows:
                    # Extract metrics separately
                    metrics = window_data.pop("metrics", {})
                    
                    movement_window = MovementWindow(
                        pose_analysis_id=pose_analysis.id,
                        metrics=metrics,
                        **window_data
                    )
                    db.add(movement_window)
                db.commit()
                
                # Perform movement-change analysis if we have enough repetitions
                movement_change_analysis = None
                if len(movement_windows) >= 3:
                    movement_change_analysis = self.movement_change_analyzer.analyze_movement_change(
                        movement_windows,
                        normalized_keypoints,
                        timestamps
                    )
                    
                    # Store movement change analysis in pose analysis
                    pose_analysis.movement_change_analysis = movement_change_analysis
                    db.commit()
                
                # Update video status
                VideoService.update_processing_status(video_id, ProcessingStatus.COMPLETED, db=db)
                
                # Performance metrics
                processed_fps = len(frames_data) / processor.metadata.duration if processor.metadata.duration > 0 else 0
                
                return {
                    "video_id": video_id,
                    "pose_analysis_id": pose_analysis.id,
                    "biomechanical_analysis_id": biomechanical_analysis.id,
                    "frames_processed": len(frames_data),
                    "pose_quality": pose_quality,
                    "performance": {
                        "video_fps": processor.metadata.fps,
                        "processed_fps": processed_fps,
                        "detector_calls": detector_calls,
                        "tracking_ids": len(track_id_counts),
                        "pose_frames": pose_frames,
                        "valid_pose_frames": valid_pose_frames,
                        "mean_pose_confidence": pose_quality.get("mean_confidence", 0.0)
                    }
                }
                
        except Exception as e:
            VideoService.update_processing_status(
                video_id,
                ProcessingStatus.FAILED,
                str(e),
                db
            )
            raise
    
    def generate_annotated_video(
        self,
        video_id: int,
        db: Session,
        output_path: Optional[str] = None
    ) -> Dict:
        """
        Generate annotated video from processed analysis.
        
        Args:
            video_id: Video ID
            db: Database session
            output_path: Optional output path (auto-generated if None)
        
        Returns:
            Dictionary with generation metadata
        """
        from app.models.pose_analysis import PoseAnalysis
        from app.models.biomechanical_analysis import BiomechanicalAnalysis
        
        # Get video
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise ValueError(f"Video {video_id} not found")
        
        # Get pose analysis
        pose_analysis = db.query(PoseAnalysis).filter(
            PoseAnalysis.video_id == video_id
        ).first()
        if not pose_analysis:
            raise ValueError(f"No pose analysis found for video {video_id}")
        
        # Get biomechanical analysis
        biomechanical_analysis = db.query(BiomechanicalAnalysis).filter(
            BiomechanicalAnalysis.pose_analysis_id == pose_analysis.id
        ).first()
        
        # Generate output path if not provided
        if output_path is None:
            video_dir = Path(video.storage_path).parent
            output_path = str(video_dir / f"annotated_{Path(video.storage_path).name}")
        
        # Generate annotated video
        result = self.annotation_service.generate_annotated_video(
            input_video_path=video.storage_path,
            output_video_path=output_path,
            keypoints_data=pose_analysis.keypoints_data,
            tracking_data=pose_analysis.tracking_data,
            roi_data=pose_analysis.roi_data,
            biomechanics_data=biomechanical_analysis.to_dict() if biomechanical_analysis else None,
            fps=video.fps
        )
        
        return result
    
    def _map_keypoints_to_original(
        self,
        roi_keypoints: List[Keypoint],
        roi_bbox: Tuple[float, float, float, float],
        roi_width: int,
        roi_height: int
    ) -> List[Keypoint]:
        """
        Map keypoints from ROI coordinates back to original frame coordinates.
        
        Args:
            roi_keypoints: Keypoints detected in ROI (already in pixel coordinates from BlazePose)
            roi_bbox: ROI bounding box in original frame (x1, y1, x2, y2)
            roi_width: Width of ROI in pixels
            roi_height: Height of ROI in pixels
        
        Returns:
            Keypoints mapped to original frame coordinates
        """
        x1_roi, y1_roi, x2_roi, y2_roi = roi_bbox
        roi_actual_width = x2_roi - x1_roi
        roi_actual_height = y2_roi - y1_roi
        
        mapped_keypoints = []
        
        for kp in roi_keypoints:
            # BlazePose returns pixel coordinates relative to the input frame (ROI)
            # We need to map these back to the original frame
            
            # Calculate scaling factors
            scale_x = roi_actual_width / roi_width
            scale_y = roi_actual_height / roi_height
            
            # Map to original frame
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
    
    def _calculate_pose_quality(self, keypoints_sequence: List[List[Keypoint]]) -> Dict:
        """
        Calculate pose quality metrics.
        
        Args:
            keypoints_sequence: Sequence of keypoints across frames
        
        Returns:
            Quality metrics dictionary
        """
        total_frames = len(keypoints_sequence)
        valid_frames = 0
        low_confidence_frames = 0
        total_confidence = 0.0
        confidence_count = 0
        
        confidence_threshold = settings.POSE_CONFIDENCE_THRESHOLD
        
        for frame_keypoints in keypoints_sequence:
            frame_valid = True
            frame_confidence_sum = 0.0
            frame_confidence_count = 0
            
            for kp in frame_keypoints:
                total_confidence += kp.confidence
                confidence_count += 1
                frame_confidence_sum += kp.confidence
                frame_confidence_count += 1
                
                if kp.confidence < confidence_threshold:
                    frame_valid = False
            
            if frame_valid:
                valid_frames += 1
            else:
                low_confidence_frames += 1
        
        mean_confidence = total_confidence / confidence_count if confidence_count > 0 else 0.0
        
        return {
            "valid_frames": valid_frames,
            "low_confidence_frames": low_confidence_frames,
            "interpolated_frames": 0,  # TODO: implement interpolation
            "mean_confidence": mean_confidence,
            "minimum_confidence": min([kp.confidence for frame in keypoints_sequence for kp in frame]),
            "quality_percentage": (valid_frames / total_frames * 100) if total_frames > 0 else 0.0
        }
    
    def _calculate_biomechanics(
        self,
        keypoints_sequence: List[List[Keypoint]],
        timestamps: List[float],
        pose_quality: Dict
    ) -> Dict:
        """
        Calculate biomechanical features from normalized keypoints.
        
        Args:
            keypoints_sequence: Normalized keypoints sequence
            timestamps: Frame timestamps
        
        Returns:
            Biomechanics results dictionary
        """
        results = {}
        
        # Calculate joint angles across frames
        left_knee_angles = []
        right_knee_angles = []
        left_hip_angles = []
        right_hip_angles = []
        trunk_lean_angles = []
        
        for frame_keypoints in keypoints_sequence:
            left_knee_angles.append(
                self.biomechanics.calculate_knee_angle(frame_keypoints, "left")
            )
            right_knee_angles.append(
                self.biomechanics.calculate_knee_angle(frame_keypoints, "right")
            )
            left_hip_angles.append(
                self.biomechanics.calculate_hip_angle(frame_keypoints, "left")
            )
            right_hip_angles.append(
                self.biomechanics.calculate_hip_angle(frame_keypoints, "right")
            )
            trunk_lean_angles.append(
                self.biomechanics.calculate_trunk_lean(frame_keypoints)
            )
        
        # Calculate ROM
        results["joint_angles"] = {
            "knee_left": self.biomechanics.calculate_rom(left_knee_angles),
            "knee_right": self.biomechanics.calculate_rom(right_knee_angles),
            "hip_left": self.biomechanics.calculate_rom(left_hip_angles),
            "hip_right": self.biomechanics.calculate_rom(right_hip_angles)
        }
        
        # Calculate symmetry
        results["symmetry"] = {
            "knee_asymmetry": self.biomechanics.calculate_asymmetry(
                left_knee_angles, right_knee_angles
            ),
            "hip_asymmetry": self.biomechanics.calculate_asymmetry(
                left_hip_angles, right_hip_angles
            )
        }
        
        # Calculate trunk lean
        valid_trunk_lean = [a for a in trunk_lean_angles if a is not None]
        if valid_trunk_lean:
            results["trunk_lean"] = {
                "mean": float(np.mean(valid_trunk_lean)),
                "max": float(np.max(valid_trunk_lean)),
                "min": float(np.min(valid_trunk_lean)),
                "std": float(np.std(valid_trunk_lean))
            }
        else:
            results["trunk_lean"] = None
        
        # Calculate velocity and acceleration
        if len(left_knee_angles) > 1:
            knee_velocity = self.biomechanics.calculate_velocity(left_knee_angles, timestamps)
            knee_acceleration = self.biomechanics.calculate_acceleration(knee_velocity, timestamps)
            
            valid_velocity = [v for v in knee_velocity if v is not None]
            if valid_velocity:
                results["velocity"] = {
                    "knee_mean": float(np.mean(valid_velocity)),
                    "knee_max": float(np.max(valid_velocity))
                }
            else:
                results["velocity"] = None
            
            valid_acceleration = [a for a in knee_acceleration if a is not None]
            if valid_acceleration:
                results["acceleration"] = {
                    "knee_mean": float(np.mean(valid_acceleration)),
                    "knee_max": float(np.max(valid_acceleration))
                }
            else:
                results["acceleration"] = None
        else:
            results["velocity"] = None
            results["acceleration"] = None
        
        # Calculate real movement quality score
        results["movement_quality"] = self._calculate_movement_quality(
            left_knee_angles,
            right_knee_angles,
            trunk_lean_angles,
            pose_quality
        )
        
        return results
    
    def _calculate_movement_quality(
        self,
        left_knee_angles: List[Optional[float]],
        right_knee_angles: List[Optional[float]],
        trunk_lean_angles: List[Optional[float]],
        pose_quality: Dict
    ) -> Dict:
        """
        Calculate movement quality score from actual measurements.
        
        Uses configurable weights:
        - pose confidence: 15%
        - symmetry: 20%
        - alignment (trunk lean): 20%
        - stability (consistency): 15%
        - ROM: 15%
        - smoothness: 15%
        
        Args:
            left_knee_angles: Left knee angle sequence
            right_knee_angles: Right knee angle sequence
            trunk_lean_angles: Trunk lean angle sequence
            pose_quality: Pose quality metrics
        
        Returns:
            Movement quality score and components
        """
        # Configuration weights
        weights = {
            "confidence": 0.15,
            "symmetry": 0.20,
            "alignment": 0.20,
            "stability": 0.15,
            "rom": 0.15,
            "smoothness": 0.15
        }
        
        component_scores = {}
        
        # 1. Confidence score (0-100)
        confidence_score = pose_quality.get("quality_percentage", 0.0)
        component_scores["confidence"] = confidence_score
        
        # 2. Symmetry score (0-100)
        valid_left = [a for a in left_knee_angles if a is not None]
        valid_right = [a for a in right_knee_angles if a is not None]
        
        if valid_left and valid_right:
            min_len = min(len(valid_left), len(valid_right))
            differences = [abs(valid_left[i] - valid_right[i]) for i in range(min_len)]
            max_asymmetry = max(differences) if differences else 0
            # Score: lower asymmetry = higher score
            symmetry_score = max(0, 100 - max_asymmetry * 2)  # Arbitrary scaling
            component_scores["symmetry"] = symmetry_score
        else:
            component_scores["symmetry"] = 50.0  # Neutral if can't calculate
        
        # 3. Alignment score (0-100) based on trunk lean
        valid_trunk = [a for a in trunk_lean_angles if a is not None]
        if valid_trunk:
            max_lean = max([abs(a) for a in valid_trunk])
            # Score: lower trunk lean = higher score
            alignment_score = max(0, 100 - max_lean * 5)  # Arbitrary scaling
            component_scores["alignment"] = alignment_score
        else:
            component_scores["alignment"] = 50.0
        
        # 4. Stability score (0-100) based on variance
        if valid_left:
            std_dev = np.std(valid_left)
            # Score: lower variance = higher score
            stability_score = max(0, 100 - std_dev * 2)
            component_scores["stability"] = stability_score
        else:
            component_scores["stability"] = 50.0
        
        # 5. ROM score (0-100) - assumes appropriate ROM is good
        if valid_left:
            rom = max(valid_left) - min(valid_left)
            # For squat, ROM around 90-120 degrees is good
            if 80 <= rom <= 130:
                rom_score = 100
            else:
                rom_score = max(0, 100 - abs(rom - 105) * 2)
            component_scores["rom"] = rom_score
        else:
            component_scores["rom"] = 50.0
        
        # 6. Smoothness score (0-100) - simplified
        # Calculate variance of successive differences
        if len(valid_left) > 1:
            diffs = [abs(valid_left[i+1] - valid_left[i]) for i in range(len(valid_left)-1)]
            smoothness_score = max(0, 100 - np.std(diffs) * 5)
            component_scores["smoothness"] = smoothness_score
        else:
            component_scores["smoothness"] = 50.0
        
        # Calculate weighted overall score
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
            "components": {
                "confidence": float(component_scores["confidence"]),
                "symmetry": float(component_scores["symmetry"]),
                "alignment": float(component_scores["alignment"]),
                "stability": float(component_scores["stability"]),
                "rom": float(component_scores["rom"]),
                "smoothness": float(component_scores["smoothness"])
            },
            "weights": weights,
            "raw_measurements": {
                "mean_left_knee": float(np.mean(valid_left)) if valid_left else None,
                "mean_right_knee": float(np.mean(valid_right)) if valid_right else None,
                "max_trunk_lean": float(max([abs(a) for a in valid_trunk])) if valid_trunk else None
            }
        }
