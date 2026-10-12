import cv2
import numpy as np
from typing import Tuple, List, Optional, Generator
from dataclasses import dataclass
from app.core.config import settings


@dataclass
class VideoMetadata:
    """Video metadata extracted from OpenCV."""
    width: int
    height: int
    fps: float
    frame_count: int
    duration: float  # in seconds


class VideoProcessor:
    """
    Video preprocessing service using OpenCV.
    
    Handles:
    - Video validation
    - Metadata extraction
    - Frame sampling
    - Optional preprocessing (denoising, stabilization)
    """
    
    def __init__(self, video_path: str):
        self.video_path = video_path
        self.cap = None
        self.metadata = None
    
    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def open(self) -> None:
        """Open video file and validate."""
        self.cap = cv2.VideoCapture(self.video_path)
        
        if not self.cap.isOpened():
            raise ValueError(f"Failed to open video: {self.video_path}")
        
        # Extract metadata
        self.metadata = self._extract_metadata()
        
        # Validate duration
        if self.metadata.duration > settings.MAX_VIDEO_DURATION:
            self.close()
            raise ValueError(
                f"Video duration {self.metadata.duration}s exceeds maximum "
                f"of {settings.MAX_VIDEO_DURATION}s"
            )
    
    def close(self) -> None:
        """Close video file."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
    
    def _extract_metadata(self) -> VideoMetadata:
        """Extract video metadata."""
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if fps <= 0:
            fps = 30.0  # Default assumption if FPS not available
        
        duration = frame_count / fps if frame_count > 0 else 0.0
        
        return VideoMetadata(
            width=width,
            height=height,
            fps=fps,
            frame_count=frame_count,
            duration=duration
        )
    
    def sample_frames(self, target_fps: Optional[float] = None) -> Generator[Tuple[int, np.ndarray], None, None]:
        """
        Sample frames from video at target FPS.
        
        Args:
            target_fps: Target FPS for sampling. If None, uses settings.POSE_FPS.
        
        Yields:
            Tuple of (frame_index, frame_image)
        """
        if self.cap is None:
            raise RuntimeError("Video not opened. Call open() first.")
        
        if target_fps is None:
            target_fps = settings.POSE_FPS
        
        video_fps = self.metadata.fps
        if video_fps <= 0:
            video_fps = 30.0
        
        # Calculate frame interval
        frame_interval = max(1, int(video_fps / target_fps))
        
        frame_index = 0
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            
            # Sample at target FPS
            if frame_index % frame_interval == 0:
                yield (frame_index, frame)
            
            frame_index += 1
    
    def get_frame_at_index(self, frame_index: int) -> Optional[np.ndarray]:
        """
        Get a specific frame by index.
        
        Args:
            frame_index: Zero-based frame index
        
        Returns:
            Frame image or None if index is invalid
        """
        if self.cap is None:
            raise RuntimeError("Video not opened. Call open() first.")
        
        if frame_index < 0 or frame_index >= self.metadata.frame_count:
            return None
        
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ret, frame = self.cap.read()
        return frame if ret else None
    
    def resize_frame(self, frame: np.ndarray, target_width: Optional[int] = None) -> np.ndarray:
        """
        Resize frame to target width, maintaining aspect ratio.
        
        Args:
            frame: Input frame
            target_width: Target width. If None, uses settings.TARGET_PROCESSING_WIDTH.
        
        Returns:
            Resized frame
        """
        if target_width is None:
            target_width = settings.TARGET_PROCESSING_WIDTH
        
        height, width = frame.shape[:2]
        
        # Calculate new dimensions maintaining aspect ratio
        aspect_ratio = width / height
        new_height = int(target_width / aspect_ratio)
        
        return cv2.resize(frame, (target_width, new_height), interpolation=cv2.INTER_LINEAR)
    
    def preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply preprocessing to frame.
        
        Current preprocessing:
        - Resize to target width
        - Optional: Could add denoising, stabilization here
        
        Args:
            frame: Input frame
        
        Returns:
            Preprocessed frame
        """
        # Resize
        processed = self.resize_frame(frame)
        
        # Could add:
        # - Denoising: cv2.fastNlMeansDenoisingColored()
        # - Histogram equalization
        # - Normalization
        
        return processed
    
    def extract_all_frames(self, target_fps: Optional[float] = None) -> List[Tuple[int, np.ndarray]]:
        """
        Extract all sampled frames into a list.
        
        Warning: This loads all frames into memory. Use sample_frames() generator
        for large videos to avoid memory issues.
        
        Args:
            target_fps: Target FPS for sampling
        
        Returns:
            List of (frame_index, frame_image) tuples
        """
        return list(self.sample_frames(target_fps))
