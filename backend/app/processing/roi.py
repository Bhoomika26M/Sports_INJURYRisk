import numpy as np
from typing import Tuple
from app.detection.base import Detection


class ROICropper:
    """
    ROI cropping and coordinate mapping.
    
    Handles:
    - Bounding box expansion with padding
    - ROI cropping
    - Coordinate mapping from ROI back to original frame
    """
    
    def __init__(self, padding_percent: float = 0.15):
        """
        Initialize ROI cropper.
        
        Args:
            padding_percent: Percentage to expand bounding box (0.0-1.0)
        """
        self.padding_percent = padding_percent
    
    def expand_bbox(
        self,
        bbox: Tuple[float, float, float, float],
        frame_width: int,
        frame_height: int
    ) -> Tuple[float, float, float, float]:
        """
        Expand bounding box with padding.
        
        Args:
            bbox: Original bounding box (x1, y1, x2, y2)
            frame_width: Frame width
            frame_height: Frame height
        
        Returns:
            Expanded bounding box (x1, y1, x2, y2)
        """
        x1, y1, x2, y2 = bbox
        
        # Calculate dimensions
        width = x2 - x1
        height = y2 - y1
        
        # Calculate padding
        pad_x = width * self.padding_percent
        pad_y = height * self.padding_percent
        
        # Expand
        x1_expanded = max(0, x1 - pad_x)
        y1_expanded = max(0, y1 - pad_y)
        x2_expanded = min(frame_width, x2 + pad_x)
        y2_expanded = min(frame_height, y2 + pad_y)
        
        return (x1_expanded, y1_expanded, x2_expanded, y2_expanded)
    
    def crop_roi(
        self,
        frame: np.ndarray,
        bbox: Tuple[float, float, float, float]
    ) -> np.ndarray:
        """
        Crop ROI from frame.
        
        Args:
            frame: Input frame
            bbox: Bounding box (x1, y1, x2, y2)
        
        Returns:
            Cropped ROI
        """
        x1, y1, x2, y2 = [int(coord) for coord in bbox]
        return frame[y1:y2, x1:x2]
    
    def map_keypoints_to_original(
        self,
        keypoints: list,  # List of (x, y) tuples in ROI coordinates
        roi_bbox: Tuple[float, float, float, float],  # ROI bbox in original frame
        target_size: Tuple[int, int]  # Target size (width, height) that keypoints are relative to
    ) -> list:
        """
        Map keypoints from ROI coordinates back to original frame coordinates.
        
        Args:
            keypoints: List of (x, y) in ROI coordinates (0-1 range or pixel coordinates)
            roi_bbox: ROI bounding box in original frame (x1, y1, x2, y2)
            target_size: Target size that keypoints are relative to
        
        Returns:
            List of (x, y) in original frame coordinates
        """
        x1_roi, y1_roi, x2_roi, y2_roi = roi_bbox
        roi_width = x2_roi - x1_roi
        roi_height = y2_roi - y1_roi
        target_width, target_height = target_size
        
        mapped_keypoints = []
        
        for kp in keypoints:
            if len(kp) == 2:
                x, y = kp
            else:
                # Handle if keypoints have confidence too
                x, y = kp[0], kp[1]
            
            # Check if coordinates are normalized (0-1) or pixel coordinates
            if 0 <= x <= 1 and 0 <= y <= 1:
                # Normalized coordinates - scale to ROI size
                x_scaled = x * target_width
                y_scaled = y * target_height
            else:
                # Pixel coordinates - use as is
                x_scaled = x
                y_scaled = y
            
            # Map to original frame
            x_original = x1_roi + (x_scaled / target_width) * roi_width
            y_original = y1_roi + (y_scaled / target_height) * roi_height
            
            mapped_keypoints.append((x_original, y_original))
        
        return mapped_keypoints
    
    def get_roi_info(
        self,
        original_bbox: Tuple[float, float, float, float],
        expanded_bbox: Tuple[float, float, float, float],
        frame_width: int,
        frame_height: int
    ) -> dict:
        """
        Get ROI information for debugging/storage.
        
        Args:
            original_bbox: Original detection bbox
            expanded_bbox: Expanded bbox after padding
            frame_width: Frame width
            frame_height: Frame height
        
        Returns:
            Dictionary with ROI information
        """
        return {
            "original_bbox": original_bbox,
            "expanded_bbox": expanded_bbox,
            "padding_percent": self.padding_percent,
            "roi_width": expanded_bbox[2] - expanded_bbox[0],
            "roi_height": expanded_bbox[3] - expanded_bbox[1],
            "frame_width": frame_width,
            "frame_height": frame_height
        }
