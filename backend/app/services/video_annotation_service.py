import cv2
import numpy as np
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from app.processing.video_processor import VideoProcessor
from app.visualization.skeleton_renderer import SkeletonRenderer
from app.pose.estimator import Keypoint
from app.biomechanics.calculator import BiomechanicsCalculator


class VideoAnnotationService:
    """
    Service for generating annotated videos with skeleton visualization.
    
    Generates video with:
    - Athlete bounding box
    - Tracker ID
    - Pose landmarks
    - Skeleton connections
    - Frame/timestamp info
    - Biomechanical measurements
    """
    
    def __init__(self):
        self.renderer = SkeletonRenderer()
        self.biomechanics = BiomechanicsCalculator()
    
    def generate_annotated_video(
        self,
        input_video_path: str,
        output_video_path: str,
        keypoints_data: List[Dict],
        tracking_data: Optional[List[Dict]] = None,
        roi_data: Optional[List[Dict]] = None,
        biomechanics_data: Optional[Dict] = None,
        fps: Optional[float] = None
    ) -> Dict:
        """
        Generate annotated video from processed data.
        
        Args:
            input_video_path: Path to original video
            output_video_path: Path for output annotated video
            keypoints_data: List of frame keypoints data
            tracking_data: Optional tracking data (bounding boxes, track IDs)
            roi_data: Optional ROI data
            biomechanics_data: Optional biomechanical measurements
            fps: Target FPS for output (uses original if None)
        
        Returns:
            Dictionary with generation metadata
        """
        # Ensure output directory exists
        output_path = Path(output_video_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Open input video
        with VideoProcessor(input_video_path) as processor:
            if fps is None:
                fps = processor.metadata.fps
            
            # Create video writer - use H.264 codec for better browser compatibility
            fourcc = cv2.VideoWriter_fourcc(*'avc1')  # H.264 codec
            video_writer = cv2.VideoWriter(
                output_video_path,
                fourcc,
                fps,
                (processor.metadata.width, processor.metadata.height)
            )
            
            # Fallback to mp4v if avc1 is not supported
            if not video_writer.isOpened():
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                video_writer = cv2.VideoWriter(
                    output_video_path,
                    fourcc,
                    fps,
                    (processor.metadata.width, processor.metadata.height)
                )
            
            if not video_writer.isOpened():
                raise RuntimeError(f"Failed to create video writer for {output_video_path}")
            
            # Create index for keypoints_data by frame number
            keypoints_by_frame = {item["frame"]: item for item in keypoints_data}
            
            # Create index for tracking data by frame number
            tracking_by_frame = {}
            if tracking_data:
                tracking_by_frame = {item["frame"]: item for item in tracking_data}
            
            # Create index for ROI data by frame number
            roi_by_frame = {}
            if roi_data:
                roi_by_frame = {item["frame"]: item for item in roi_data}
            
            # Process frames
            frames_annotated = 0
            frames_with_pose = 0
            
            for frame_idx, frame in processor.sample_frames(target_fps=fps):
                # Get keypoints for this frame
                frame_data = keypoints_by_frame.get(frame_idx)
                
                if frame_data is None:
                    # No keypoints data for this frame, write original
                    video_writer.write(frame)
                    frames_annotated += 1
                    continue
                
                # Convert keypoints dict back to Keypoint objects
                keypoints = [
                    Keypoint(
                        x=kp["x"],
                        y=kp["y"],
                        confidence=kp["confidence"],
                        name=kp["name"]
                    )
                    for kp in frame_data["keypoints"]
                ]
                
                if keypoints:
                    frames_with_pose += 1
                
                # Get tracking data
                bbox = None
                track_id = None
                if frame_idx in tracking_by_frame:
                    track_info = tracking_by_frame[frame_idx]
                    if track_info["tracked_objects"]:
                        # Use the first tracked object (primary athlete)
                        obj = track_info["tracked_objects"][0]
                        bbox = tuple(obj["bbox"])
                        track_id = obj["track_id"]
                
                # Get biomechanical data for this frame
                frame_biomechanics = None
                if biomechanics_data:
                    frame_biomechanics = self._get_frame_biomechanics(
                        biomechanics_data,
                        frame_idx,
                        keypoints
                    )
                
                # Render annotations
                annotated_frame = self.renderer.render(
                    frame,
                    keypoints,
                    bbox=bbox,
                    track_id=track_id,
                    frame_number=frame_idx,
                    timestamp=frame_data.get("timestamp"),
                    biomechanical_data=frame_biomechanics
                )
                
                # Write frame
                video_writer.write(annotated_frame)
                frames_annotated += 1
            
            # Release writer
            video_writer.release()
        
        return {
            "output_path": output_video_path,
            "frames_annotated": frames_annotated,
            "frames_with_pose": frames_with_pose,
            "fps": fps,
            "resolution": (processor.metadata.width, processor.metadata.height)
        }
    
    def _get_frame_biomechanics(
        self,
        biomechanics_data: Dict,
        frame_idx: int,
        keypoints: List[Keypoint]
    ) -> Dict:
        """
        Get biomechanical measurements for a specific frame.
        
        Args:
            biomechanics_data: Full biomechanics data
            frame_idx: Frame index
            keypoints: Frame keypoints
        
        Returns:
            Dictionary with frame-specific biomechanical measurements
        """
        frame_data = {}
        
        # Calculate joint angles for this frame
        if keypoints:
            left_knee_angle = self.biomechanics.calculate_knee_angle(keypoints, "left")
            right_knee_angle = self.biomechanics.calculate_knee_angle(keypoints, "right")
            left_hip_angle = self.biomechanics.calculate_hip_angle(keypoints, "left")
            right_hip_angle = self.biomechanics.calculate_hip_angle(keypoints, "right")
            trunk_lean = self.biomechanics.calculate_trunk_lean(keypoints)
            
            frame_data = {
                "knee_angle": left_knee_angle if left_knee_angle is not None else right_knee_angle,
                "hip_angle": left_hip_angle if left_hip_angle is not None else right_hip_angle,
                "trunk_lean": trunk_lean
            }
        
        return frame_data
    
    def extract_sample_frames(
        self,
        input_video_path: str,
        output_dir: str,
        keypoints_data: List[Dict],
        tracking_data: Optional[List[Dict]] = None,
        num_samples: int = 10
    ) -> List[str]:
        """
        Extract sample annotated frames as images.
        
        Args:
            input_video_path: Path to original video
            output_dir: Directory for output images
            keypoints_data: List of frame keypoints data
            tracking_data: Optional tracking data
            num_samples: Number of sample frames to extract
        
        Returns:
            List of output image paths
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        with VideoProcessor(input_video_path) as processor:
            # Calculate sample interval
            total_frames = processor.metadata.frame_count
            interval = max(1, total_frames // num_samples)
            
            # Create indexes
            keypoints_by_frame = {item["frame"]: item for item in keypoints_data}
            tracking_by_frame = {}
            if tracking_data:
                tracking_by_frame = {item["frame"]: item for item in tracking_data}
            
            output_paths = []
            
            for frame_idx, frame in processor.sample_frames(target_fps=processor.metadata.fps):
                if frame_idx % interval != 0:
                    continue
                
                # Get keypoints
                frame_data = keypoints_by_frame.get(frame_idx)
                if frame_data is None:
                    continue
                
                keypoints = [
                    Keypoint(
                        x=kp["x"],
                        y=kp["y"],
                        confidence=kp["confidence"],
                        name=kp["name"]
                    )
                    for kp in frame_data["keypoints"]
                ]
                
                # Get tracking data
                bbox = None
                track_id = None
                if frame_idx in tracking_by_frame:
                    track_info = tracking_by_frame[frame_idx]
                    if track_info["tracked_objects"]:
                        obj = track_info["tracked_objects"][0]
                        bbox = tuple(obj["bbox"])
                        track_id = obj["track_id"]
                
                # Render
                annotated = self.renderer.render(
                    frame,
                    keypoints,
                    bbox=bbox,
                    track_id=track_id,
                    frame_number=frame_idx,
                    timestamp=frame_data.get("timestamp")
                )
                
                # Save
                output_file = output_path / f"frame_{frame_idx:04d}.jpg"
                cv2.imwrite(str(output_file), annotated)
                output_paths.append(str(output_file))
                
                if len(output_paths) >= num_samples:
                    break
        
        return output_paths
