import cv2
import numpy as np
import logging
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.video import Video, ProcessingStatus
from app.models.pose_analysis import PoseAnalysis
from app.models.biomechanical_analysis import BiomechanicalAnalysis
from app.processing.video_processor import VideoProcessor
from app.pose.mediapipe_pose import MediaPipeBlazePoseEstimator, ensure_pose_model_available
from app.pose.parallel_pose import ParallelPosePool
from app.pose.estimator import Keypoint
from app.processing.smoothing import TemporalSmoother
from app.processing.normalization import SkeletonNormalizer
from app.processing.roi import ROICropper
from app.biomechanics.calculator import BiomechanicsCalculator
from app.tracking.yolo_tracker import YOLOTracker
from app.tracking.base import TrackedObject
from app.visualization.skeleton_renderer import SkeletonRenderer
from app.visualization.smart_framing import SmoothFramer, apply_crop
from app.core.config import settings
from app.core import profiling
from app.services.video_service import VideoService
from app.services.video_annotation_service import VideoAnnotationService
from app.services import progress_service
from app.risk.engine import InjuryRiskEngine
from app.movement.segmentation import MovementSegmenter
from app.movement.change_analysis import MovementChangeAnalyzer

logger = logging.getLogger(__name__)


class VideoProcessingService:
    """
    Main video processing service.
    
    Orchestrates the complete pipeline:
    Video → OpenCV Preprocessing → YOLO11n Detection → ByteTrack Tracking → ROI Crop →
    BlazePose → Coordinate Mapping → Smoothing → Normalization → Biomechanics
    """
    
    def __init__(self):
        # Lightweight components — safe to construct per request
        self.roi_cropper = ROICropper(padding_percent=0.15)
        self.smoother = TemporalSmoother(window_length=5, polyorder=2)
        self.normalizer = SkeletonNormalizer()
        self.biomechanics = BiomechanicsCalculator()
        self.renderer = SkeletonRenderer()
        self.annotation_service = VideoAnnotationService()
        self.movement_segmenter = MovementSegmenter()
        self.movement_change_analyzer = MovementChangeAnalyzer()
        # Heavy ML models are loaded lazily per run (_init_pipeline)
        self.tracker = None
        self.pose_model_name = "MediaPipe BlazePose"
        self.pose_model_version = f"complexity_{settings.POSE_MODEL_COMPLEXITY}"

    def _init_pipeline(self) -> None:
        """
        Load the heavy ML models for a processing run.

        Kept out of __init__ so endpoints that only render or re-encode
        videos don't pay the YOLO + MediaPipe load cost. A fresh tracker
        per run also guarantees ByteTrack state never leaks between videos.

        The pose model file is resolved here (single-threaded) so the parallel
        pose workers never race to download it, and any model-load failure
        surfaces before the analysis loop starts.
        """
        ensure_pose_model_available(settings.POSE_MODEL_COMPLEXITY)
        self.tracker = YOLOTracker()
    
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
        
        writer = None  # annotated-video writer, released on success or error
        pose_pool = None  # parallel MediaPipe instances, shut down in finally
        last_risk = None  # last computed risk dict, used for snapshot recovery
        profiling.set_enabled(settings.POSE_PROFILING)
        profiling.reset()
        run_start = time.perf_counter()
        try:
            # Fresh progress state for this run (drives live client updates)
            progress_service.init_progress(video_id)
            
            # Load heavy models for this run (tracker + pose estimator)
            with profiling.profile("model_load"):
                self._init_pipeline()
                pose_pool = ParallelPosePool(settings.POSE_WORKERS)
            
            # Update status
            VideoService.update_processing_status(video_id, ProcessingStatus.PREPROCESSING, db=db)
            progress_service.set_stage(video_id, "preprocessing")
            
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
                
                # Single-pass annotated video writer: the skeleton overlay is
                # rendered inside the analysis loop below, so the annotated
                # video is produced without re-reading/re-encoding the file
                # in a second pass.
                frame_interval = max(1, int(processor.metadata.fps / settings.POSE_FPS))
                sampled_fps = processor.metadata.fps / frame_interval
                annotated_path = (
                    Path(video.storage_path).parent
                    / f"annotated_{Path(video.storage_path).name}"
                )
                # Downscale the annotated output for 4K sources: encoding 4K
                # dominates runtime, and 720p-1280px is plenty for review
                out_w = processor.metadata.width
                out_h = processor.metadata.height
                if out_w > settings.ANNOTATED_MAX_WIDTH:
                    out_w = settings.ANNOTATED_MAX_WIDTH
                    out_h = max(1, round(processor.metadata.height * out_w / processor.metadata.width))
                writer = cv2.VideoWriter(
                    str(annotated_path),
                    cv2.VideoWriter_fourcc(*"mp4v"),
                    sampled_fps,
                    (out_w, out_h)
                )
                if not writer.isOpened():
                    print(f"Warning: could not open annotated video writer: {annotated_path}")
                    writer = None
                out_size = (out_w, out_h)

                # Follows the athlete so the annotated output frames the whole
                # body instead of showing a small figure in a wide shot. Reset
                # per run so no state leaks between videos.
                framer = None
                if settings.ANNOTATED_FOLLOW_ATHLETE:
                    framer = SmoothFramer(
                        alpha=settings.ANNOTATED_CROP_SMOOTHING,
                        padding=settings.ANNOTATED_CROP_PADDING,
                        min_scale=settings.ANNOTATED_CROP_MIN_SCALE,
                    )
                
                # Total sampled frames (denominator for live progress %)
                total_sampled = max(
                    1,
                    (processor.metadata.frame_count + frame_interval - 1) // frame_interval
                )
                progress_service.set_stage(
                    video_id,
                    "pose_estimation",
                    total_frames=total_sampled,
                    frames_processed=0,
                )
                
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
                
                # Process the video piecemeal: decode + track sequentially
                # (ByteTrack needs frame continuity), estimate pose for each
                # chunk in parallel across MediaPipe instances, then push a
                # live progress update so clients see step-by-step results
                # within seconds of starting.
                frames_iter = processor.sample_frames(target_fps=settings.POSE_FPS)
                chunk_size = max(1, settings.PROGRESS_CHUNK_FRAMES)
                chunks_done = 0
                last_annotated = None
                last_bio = None
                conf_sum = 0.0
                conf_count = 0
                loop_start = time.perf_counter()
                
                while True:
                    # -- Collect the next chunk of sampled frames
                    chunk = []
                    decode_start = time.perf_counter()
                    for _ in range(chunk_size):
                        try:
                            chunk.append(next(frames_iter))
                        except StopIteration:
                            break
                    profiling.record("frame_decode", time.perf_counter() - decode_start)
                    if not chunk:
                        break
                    
                    # -- Phase 1: sequential tracking + ROI crop
                    #    (ByteTrack is stateful, so frames stay ordered here)
                    entries = []
                    for frame_idx, frame in chunk:
                        timestamp = frame_idx / processor.metadata.fps
                        
                        # YOLO11n detection + ByteTrack tracking in a single
                        # inference (a separate detect() pass was redundant)
                        detector_calls += 1
                        with profiling.profile("detect_track"):
                            tracked_objects = self.tracker.update(frame, frame_idx, timestamp)
                        
                        tracking_data.append({
                            "frame": frame_idx,
                            "timestamp": timestamp,
                            "tracked_objects": [obj.to_dict() for obj in tracked_objects]
                        })
                        
                        for obj in tracked_objects:
                            track_id_counts[obj.track_id] = track_id_counts.get(obj.track_id, 0) + 1
                        
                        primary_track_id = (
                            max(track_id_counts, key=track_id_counts.get)
                            if track_id_counts else None
                        )
                        primary_bbox = None
                        for obj in tracked_objects:
                            if obj.track_id == primary_track_id:
                                primary_bbox = obj.bbox
                                break
                        
                        entry = {
                            "frame": frame,
                            "frame_idx": frame_idx,
                            "timestamp": timestamp,
                            "bbox": primary_bbox,
                            "track_id": primary_track_id,
                            "roi": None,
                            "expanded_bbox": None,
                        }
                        if primary_bbox is not None:
                            expanded_bbox = self.roi_cropper.expand_bbox(
                                primary_bbox,
                                processor.metadata.width,
                                processor.metadata.height
                            )
                            with profiling.profile("roi_crop"):
                                entry["roi"] = self._downscale_for_pose(
                                    self.roi_cropper.crop_roi(frame, expanded_bbox)
                                )
                            entry["expanded_bbox"] = expanded_bbox
                            pose_frames += 1
                        entries.append(entry)
                    
                    # -- Phase 2: parallel pose estimation for this chunk
                    #    (contiguous slices keep MediaPipe tracking coherent)
                    pose_inputs = [
                        (e["roi"], e["timestamp"])
                        for e in entries if e["roi"] is not None
                    ]
                    with profiling.profile("pose_estimate"):
                        roi_kps_list = pose_pool.estimate(pose_inputs) if pose_inputs else []
                    kps_iter = iter(roi_kps_list)
                    
                    # -- Phase 3: map coordinates, store, render, write
                    for e in entries:
                        timestamps.append(e["timestamp"])
                        
                        if e["roi"] is None:
                            # No athlete detected in this frame
                            frames_data.append({
                                "frame": e["frame_idx"],
                                "timestamp": e["timestamp"],
                                "keypoints": [],
                                "bbox": None,
                                "track_id": None,
                                "roi_bbox": None
                            })
                            keypoints_sequence.append([])
                            roi_data.append(None)
                            no_detect_frame = e["frame"]
                            if framer is not None:
                                # No athlete: hold the last window so the view
                                # doesn't jerk back to full-frame mid-clip.
                                window = framer.window(
                                    None,
                                    (processor.metadata.width, processor.metadata.height),
                                    out_size,
                                )
                                no_detect_frame = apply_crop(no_detect_frame, window)
                            last_annotated = self._fit_for_output(no_detect_frame, out_size)
                            if writer is not None:
                                writer.write(last_annotated)
                            continue
                        
                        roi_keypoints = next(kps_iter)
                        if roi_keypoints:
                            valid_pose_frames += 1
                        
                        # Map keypoints back to original frame coordinates
                        with profiling.profile("pose_map"):
                            mapped_keypoints = self._map_keypoints_to_original(
                                roi_keypoints,
                                e["expanded_bbox"],
                                e["roi"].shape[1],
                                e["roi"].shape[0]
                            )
                        keypoints_sequence.append(mapped_keypoints)
                        frames_data.append({
                            "frame": e["frame_idx"],
                            "timestamp": e["timestamp"],
                            "keypoints": [kp.to_dict() for kp in mapped_keypoints],
                            "bbox": e["bbox"],
                            "track_id": e["track_id"],
                            "roi_bbox": e["expanded_bbox"]
                        })
                        roi_data.append({
                            "frame": e["frame_idx"],
                            "original_bbox": e["bbox"],
                            "expanded_bbox": e["expanded_bbox"],
                            "roi_width": e["expanded_bbox"][2] - e["expanded_bbox"][0],
                            "roi_height": e["expanded_bbox"][3] - e["expanded_bbox"][1]
                        })
                        
                        for kp in mapped_keypoints:
                            conf_sum += kp.confidence
                            conf_count += 1
                        
                        last_bio = self._frame_biomechanics(mapped_keypoints)
                        # Render skeleton/bbox only; the HUD text is drawn after
                        # cropping so it is never clipped by the follow-crop.
                        with profiling.profile("render_overlay"):
                            annotated_frame = self.renderer.render(
                                e["frame"],
                                mapped_keypoints,
                                bbox=e["bbox"],
                                track_id=e["track_id"],
                                frame_number=e["frame_idx"],
                                timestamp=e["timestamp"],
                                biomechanical_data=last_bio,
                                draw_hud=framer is None
                            )
                        # Crop AFTER rendering: keypoints are in original frame
                        # coordinates, so the overlay must be drawn first and
                        # the follow-crop applied to the finished image.
                        if framer is not None:
                            window = framer.window(
                                e["bbox"],
                                (processor.metadata.width, processor.metadata.height),
                                out_size,
                            )
                            annotated_frame = apply_crop(annotated_frame, window)
                        last_annotated = self._fit_for_output(annotated_frame, out_size)
                        if framer is not None:
                            # HUD on the final, cropped, resized frame.
                            with profiling.profile("hud"):
                                self.renderer.draw_hud(
                                    last_annotated,
                                    e["frame_idx"],
                                    e["timestamp"],
                                    last_bio
                                )
                        if writer is not None:
                            with profiling.profile("video_encode"):
                                writer.write(last_annotated)
                    
                    # -- Phase 4: live progress + preview + partial risk
                    chunks_done += 1
                    processed = len(frames_data)
                    mean_conf = (conf_sum / conf_count) if conf_count else None
                    progress_service.set_progress(
                        video_id,
                        5 + 80.0 * processed / total_sampled,
                        frames_processed=processed,
                        valid_pose_frames=valid_pose_frames,
                        mean_confidence=round(mean_conf, 3) if mean_conf is not None else None,
                        current_angles=last_bio or {},
                    )
                    
                    if last_annotated is not None and (
                        chunks_done == 1
                        or chunks_done % max(1, settings.PREVIEW_EVERY_CHUNKS) == 0
                    ):
                        try:
                            with profiling.profile("preview_write"):
                                cv2.imwrite(
                                    str(progress_service.preview_path(video_id)),
                                    last_annotated
                                )
                        except Exception:
                            pass
                    
                    # Partial explainable risk once enough frames exist
                    if processed >= 60 and chunks_done % 2 == 0:
                        partial_risk = InjuryRiskEngine().evaluate(
                            keypoints_sequence,
                            timestamps,
                            activity=activity,
                            pose_quality=self._calculate_pose_quality(keypoints_sequence),
                        )
                        progress_service.update(
                            video_id, risk=self._summarize_risk(partial_risk)
                        )
                
                # Annotated video (skeleton overlay) is complete
                if writer is not None:
                    writer.release()
                    writer = None
                
                profiling.record("frame_loop", time.perf_counter() - loop_start)
                progress_service.set_stage(video_id, "analyzing")
                
                # Apply temporal smoothing
                with profiling.profile("smoothing"):
                    smoothed_keypoints = self.smoother.smooth_keypoints(keypoints_sequence)
                
                # Normalize skeleton
                with profiling.profile("normalization"):
                    normalized_keypoints = self.normalizer.normalize_sequence(smoothed_keypoints)
                
                # Calculate pose quality metrics
                with profiling.profile("pose_quality"):
                    pose_quality = self._calculate_pose_quality(keypoints_sequence)
                
                # Create pose analysis record
                pose_analysis = PoseAnalysis(
                    video_id=video_id,
                    pose_model=self.pose_model_name,
                    pose_model_version=self.pose_model_version,
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
                with profiling.profile("db_commit"):
                    db.commit()
                db.refresh(pose_analysis)
                
                # Calculate biomechanics
                VideoService.update_processing_status(video_id, ProcessingStatus.ANALYZING, db=db)
                
                with profiling.profile("biomechanics"):
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
                
                segment_start = time.perf_counter()
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
                profiling.record("segmentation", time.perf_counter() - segment_start)
                
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
                
                # Final explainable risk assessment (identical computation
                # to GET /api/v1/risk/{video_id}, so progress == final result)
                with profiling.profile("risk_engine"):
                    final_risk = InjuryRiskEngine().evaluate(
                        keypoints_sequence,
                        timestamps,
                        activity=activity,
                        pose_quality=pose_quality,
                    )
                last_risk = final_risk

                # Record this analysis in the athlete's history. The snapshot
                # captures the risk result plus trended metrics and is compared
                # against the athlete's rolling baseline of prior analyses of
                # the SAME activity type. Failure here must never fail the
                # analysis itself, so it is isolated.
                try:
                    from app.services import baseline_service

                    with profiling.profile("history_snapshot"):
                        baseline_service.record_snapshot(
                            db,
                            video=video,
                            risk_assessment=final_risk,
                            pose_analysis=pose_analysis,
                            biomechanical=biomechanical_analysis,
                        )
                except Exception as history_exc:  # noqa: BLE001 - best effort
                    logger.warning(
                        "History snapshot failed for video %s: %s",
                        video_id,
                        history_exc,
                    )

                # Update video status (the annotated video with the skeleton
                # overlay was already written during the analysis loop above)
                VideoService.update_processing_status(video_id, ProcessingStatus.COMPLETED, db=db)
                progress_service.set_stage(
                    video_id,
                    "completed",
                    risk=self._summarize_risk(final_risk),
                    frames_processed=len(frames_data),
                )
                
                # Performance metrics
                processed_fps = len(frames_data) / processor.metadata.duration if processor.metadata.duration > 0 else 0
                
                # Per-stage timings. Only meaningful when POSE_PROFILING is on;
                # when off this is an empty report and costs nothing. Logged so
                # a developer gets the breakdown without re-running by hand.
                profile_report = profiling.report()
                if settings.POSE_PROFILING:
                    wall = time.perf_counter() - run_start
                    profile_report["wall_seconds"] = round(wall, 3)
                    logger.info(
                        "Video %s profile (wall %.2fs):\n%s",
                        video_id,
                        wall,
                        profiling.format_report(profile_report),
                    )
                
                return {
                    "video_id": video_id,
                    "pose_analysis_id": pose_analysis.id,
                    "biomechanical_analysis_id": biomechanical_analysis.id,
                    "frames_processed": len(frames_data),
                    "pose_quality": pose_quality,
                    "annotated_video_path": str(annotated_path),
                    "risk_summary": self._summarize_risk(final_risk),
                    "performance": {
                        "video_fps": processor.metadata.fps,
                        "processed_fps": processed_fps,
                        "detector_calls": detector_calls,
                        "tracking_ids": len(track_id_counts),
                        "pose_frames": pose_frames,
                        "valid_pose_frames": valid_pose_frames,
                        "mean_pose_confidence": pose_quality.get("mean_confidence", 0.0)
                    },
                    "profile": profile_report,
                }
                
        except Exception as e:
            # Surface the failure to live-progress clients first
            try:
                progress_service.set_stage(video_id, "failed", error=str(e))
            except Exception:
                pass
            # A failed flush poisons the session, so roll back first —
            # otherwise this status update also fails and the video is left
            # stuck on its last in-flight status instead of "failed".
            try:
                db.rollback()
                VideoService.update_processing_status(
                    video_id,
                    ProcessingStatus.FAILED,
                    str(e),
                    db
                )
            except Exception:
                try:
                    db.rollback()
                except Exception:
                    pass

            # Safety net: if the failure happened AFTER the pose analysis was
            # committed (e.g. while finalizing the annotated video), the
            # expensive analysis is already durable and would otherwise vanish
            # from the athlete's history. Recover a snapshot from what was
            # persisted rather than losing it.
            try:
                from app.models.analysis_snapshot import AnalysisSnapshot
                from app.services import baseline_service

                recovered_video = db.query(Video).filter(Video.id == video_id).first()
                recovered_pose = (
                    db.query(PoseAnalysis)
                    .filter(PoseAnalysis.video_id == video_id)
                    .first()
                )
                already = (
                    db.query(AnalysisSnapshot)
                    .filter(AnalysisSnapshot.video_id == video_id)
                    .first()
                )
                if (
                    recovered_video is not None
                    and recovered_pose is not None
                    and already is None
                ):
                    recovered_bio = (
                        db.query(BiomechanicalAnalysis)
                        .filter(
                            BiomechanicalAnalysis.pose_analysis_id == recovered_pose.id
                        )
                        .first()
                    )
                    baseline_service.record_snapshot(
                        db,
                        video=recovered_video,
                        risk_assessment=last_risk,
                        pose_analysis=recovered_pose,
                        biomechanical=recovered_bio,
                    )
                    logger.info(
                        "Recovered history snapshot for partially processed video %s",
                        video_id,
                    )
            except Exception as recovery_exc:  # noqa: BLE001
                logger.warning(
                    "Could not recover snapshot for video %s: %s",
                    video_id,
                    recovery_exc,
                )
            raise
        finally:
            if writer is not None:
                writer.release()
            if pose_pool is not None:
                pose_pool.shutdown()
    
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
    
    def _frame_biomechanics(self, keypoints: List[Keypoint]) -> Optional[Dict]:
        """
        Compute per-frame joint angles for the skeleton overlay HUD.
        
        Args:
            keypoints: Frame keypoints in original-frame coordinates
        
        Returns:
            Dictionary with knee/hip/trunk angles, or None if no keypoints
        """
        if not keypoints:
            return None
        
        left_knee = self.biomechanics.calculate_knee_angle(keypoints, "left")
        right_knee = self.biomechanics.calculate_knee_angle(keypoints, "right")
        left_hip = self.biomechanics.calculate_hip_angle(keypoints, "left")
        right_hip = self.biomechanics.calculate_hip_angle(keypoints, "right")
        trunk_lean = self.biomechanics.calculate_trunk_lean(keypoints)
        
        return {
            "knee_angle": left_knee if left_knee is not None else right_knee,
            "hip_angle": left_hip if left_hip is not None else right_hip,
            "trunk_lean": trunk_lean
        }
    
    @staticmethod
    def _downscale_for_pose(roi: np.ndarray) -> np.ndarray:
        """
        Downscale a cropped ROI before pose estimation.

        MediaPipe resizes its input to ~256px internally anyway, so feeding a
        4K crop only adds color-conversion cost. Keypoint mapping stays
        correct because it is normalized by the ROI's own dimensions.
        """
        if roi is None or roi.size == 0:
            return roi
        h, w = roi.shape[:2]
        longest = max(h, w)
        if longest > settings.POSE_MAX_ROI_DIM:
            scale = settings.POSE_MAX_ROI_DIM / longest
            new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
            roi = cv2.resize(roi, new_size, interpolation=cv2.INTER_AREA)
        return roi

    @staticmethod
    def _fit_for_output(frame: np.ndarray, out_size: tuple) -> np.ndarray:
        """Downscale a rendered frame to the annotated writer's resolution."""
        if frame is None:
            return frame
        h, w = frame.shape[:2]
        if (w, h) != out_size:
            return cv2.resize(frame, out_size, interpolation=cv2.INTER_AREA)
        return frame

    @staticmethod
    def _summarize_risk(risk: Dict) -> Dict:
        """Compact risk summary embedded in live progress updates."""
        return {
            "overall_risk_score": risk.get("overall_risk_score", 0.0),
            "risk_level": risk.get("risk_level", "low"),
            "risk_of": risk.get("risk_of", []),
            "findings_count": len(risk.get("findings", [])),
            "top_findings": [
                f.get("issue", "") for f in risk.get("findings", [])[:4]
            ],
        }
    
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
        all_confidences = [
            kp.confidence for frame in keypoints_sequence for kp in frame
        ]
        
        return {
            "valid_frames": valid_frames,
            "low_confidence_frames": low_confidence_frames,
            "interpolated_frames": 0,  # TODO: implement interpolation
            "mean_confidence": mean_confidence,
            "minimum_confidence": min(all_confidences) if all_confidences else 0.0,
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
