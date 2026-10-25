import os
import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

# Video signatures for secure magic bytes inspection
VIDEO_SIGNATURES = {
    ".mp4": [b"ftyp", b"moov", b"mdat"],
    ".mov": [b"ftypqt", b"moov", b"wide", b"mdat"],
    ".avi": [b"RIFF"],
    ".webm": [b"\x1a\x45\xdf\xa3"]
}

def verify_magic_bytes(header_bytes: bytes, ext: str) -> bool:
    """
    Verify magic bytes of uploaded video file.
    Permissive to avoid false rejections of valid streaming formats.
    """
    ext = ext.lower()
    sigs = VIDEO_SIGNATURES.get(ext)
    if not sigs:
        return True # Unknown format, fallback to OpenCV check
    for sig in sigs:
        if sig in header_bytes[:64]:
            return True
    return False

def extract_video_metadata(file_path: str):
    """
    Extract video metadata using OpenCV.
    Returns (fps, width, height, duration_sec)
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Video file not found: {file_path}")
        
    cap = cv2.VideoCapture(file_path)
    if not cap.isOpened():
        raise ValueError("Could not open video file (may be corrupt, empty, or unsupported codec)")
        
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    cap.release()
    
    if width <= 0 or height <= 0:
        raise ValueError("Video has invalid spatial resolution (width or height is 0)")
        
    duration_sec = 0.0
    if fps > 0 and frame_count > 0:
        duration_sec = frame_count / fps
        
    return fps, width, height, duration_sec

def validate_video_suitability(file_path: str, min_duration: float = 0.5, max_duration: float = 60.0):
    """
    Validates duration, resolution, and decodability for pose estimation suitability.
    Returns (fps, width, height, duration_sec, frame_count)
    Raises ValueError with actionable error message if unsuitable.
    """
    fps, width, height, duration_sec = extract_video_metadata(file_path)
    
    if duration_sec < min_duration:
        raise ValueError(f"Video duration is too short ({duration_sec:.1f}s). Movement analysis requires at least {min_duration}s of continuous movement.")
        
    if duration_sec > max_duration:
        raise ValueError(f"Video duration exceeds limit ({duration_sec:.1f}s > {max_duration}s). Please trim video to focus on the key movement trial.")
        
    if width < 160 or height < 160:
        raise ValueError(f"Video resolution ({width}x{height}) is too low for accurate landmark pose estimation (minimum 160x160 required).")
        
    cap = cv2.VideoCapture(file_path)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    ret, sample_frame = cap.read()
    cap.release()
    
    if not ret or sample_frame is None:
        raise ValueError("Unable to decode video frames. File may be truncated or encoded in an unsupported codec.")
        
    return fps, width, height, duration_sec, frame_count

def enhance_frame_contrast(frame_rgb: np.ndarray) -> np.ndarray:
    """
    Adaptive histogram equalization (CLAHE) to enhance visibility in low-light sports trials.
    Operates on the L-channel of LAB color space to preserve natural chrominance.
    """
    try:
        lab = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        
        # Check average luminance; if already well-balanced, don't over-process
        mean_l = np.mean(l_channel)
        if 40 < mean_l < 200:
            # Good contrast, light enhancement
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            cl = clahe.apply(l_channel)
            merged = cv2.merge((cl, a_channel, b_channel))
            return cv2.cvtColor(merged, cv2.COLOR_LAB2RGB)
        elif mean_l <= 40:
            # Very dark, stronger enhancement
            clahe = cv2.createCLAHE(clipLimit=3.5, tileGridSize=(8, 8))
            cl = clahe.apply(l_channel)
            merged = cv2.merge((cl, a_channel, b_channel))
            return cv2.cvtColor(merged, cv2.COLOR_LAB2RGB)
        return frame_rgb
    except Exception as e:
        logger.warning(f"Frame contrast enhancement skipped: {e}")
        return frame_rgb

def compute_target_dimensions(width: int, height: int, max_dim: int = 1280) -> tuple:
    """
    Calculates downscaled dimensions keeping aspect ratio if larger than max_dim.
    Standardizes large 4K / 2K sports footage to optimize MediaPipe processing throughput.
    """
    if max(width, height) <= max_dim:
        return width, height
    scale = max_dim / float(max(width, height))
    new_w = int(width * scale)
    new_h = int(height * scale)
    # Ensure dimensions are even numbers for H.264 encoders
    new_w = new_w if new_w % 2 == 0 else new_w - 1
    new_h = new_h if new_h % 2 == 0 else new_h - 1
    return new_w, new_h
