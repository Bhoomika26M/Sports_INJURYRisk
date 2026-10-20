"""Video upload validation, frame extraction and light motion enhancement."""

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Iterator

import cv2
import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


def validate_video(path: str | Path) -> dict:
    """Open the video and check technical quality.

    Returns a dict with metadata plus `errors` (hard failures: upload is rejected)
    and `warnings` (soft issues: analysis proceeds, accuracy may suffer).
    """
    result: dict = {
        "readable": False,
        "fps": None,
        "width": None,
        "height": None,
        "frame_count": None,
        "duration_s": None,
        "brightness": None,
        "sharpness": None,
        "errors": [],
        "warnings": [],
    }
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        result["errors"].append("File could not be opened as a video.")
        return result

    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        duration = frames / fps if fps > 0 else 0.0

        result.update(
            fps=round(fps, 2),
            width=width,
            height=height,
            frame_count=frames,
            duration_s=round(duration, 2),
        )

        if frames <= 0 or fps <= 0 or width <= 0 or height <= 0:
            result["errors"].append("Video has no readable frames or invalid metadata.")
            return result
        result["readable"] = True

        if width < settings.MIN_VIDEO_WIDTH or height < settings.MIN_VIDEO_HEIGHT:
            result["errors"].append(
                f"Resolution {width}x{height} is below the minimum "
                f"{settings.MIN_VIDEO_WIDTH}x{settings.MIN_VIDEO_HEIGHT}."
            )
        if duration < settings.MIN_VIDEO_SECONDS:
            result["errors"].append(f"Video is shorter than {settings.MIN_VIDEO_SECONDS}s.")
        if duration > settings.MAX_VIDEO_SECONDS:
            result["errors"].append(f"Video is longer than {settings.MAX_VIDEO_SECONDS}s.")
        if fps < settings.MIN_VIDEO_FPS:
            result["warnings"].append(
                f"Low frame rate ({fps:.0f} fps). Fast movements may be under-sampled; "
                "30 fps or higher is recommended."
            )

        # Sample up to 10 frames for brightness and sharpness
        sample_idx = np.linspace(0, max(frames - 1, 0), num=min(10, frames), dtype=int)
        brightness, sharpness = [], []
        for idx in sample_idx:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
            ok, frame = cap.read()
            if not ok:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brightness.append(float(gray.mean()))
            sharpness.append(float(cv2.Laplacian(gray, cv2.CV_64F).var()))
        if brightness:
            result["brightness"] = round(float(np.mean(brightness)), 1)
            result["sharpness"] = round(float(np.mean(sharpness)), 1)
            if result["brightness"] < 40:
                result["warnings"].append("Video is very dark; pose detection may be unreliable.")
            elif result["brightness"] > 220:
                result["warnings"].append("Video is overexposed; pose detection may be unreliable.")
            if result["sharpness"] < 30:
                result["warnings"].append("Video looks blurry; joint localisation may suffer.")
    finally:
        cap.release()
    return result


def transcode_to_mp4(src: str | Path, dst: str | Path) -> bool:
    """Re-encode with FFmpeg when OpenCV cannot decode the original codec."""
    if shutil.which("ffmpeg") is None:
        return False
    cmd = [
        "ffmpeg", "-y", "-i", str(src),
        "-an", "-vcodec", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast",
        str(dst),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=600)
        return Path(dst).exists()
    except (subprocess.SubprocessError, OSError) as exc:
        logger.warning("ffmpeg transcode failed: %s", exc)
        return False


def enhance_frame(frame: np.ndarray) -> np.ndarray:
    """Light denoise + local contrast equalisation to help pose detection."""
    blurred = cv2.GaussianBlur(frame, (3, 3), 0)
    lab = cv2.cvtColor(blurred, cv2.COLOR_BGR2LAB)
    l_chan, a_chan, b_chan = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_chan = clahe.apply(l_chan)
    return cv2.cvtColor(cv2.merge((l_chan, a_chan, b_chan)), cv2.COLOR_LAB2BGR)


def iter_frames(
    path: str | Path, stride: int = 1, enhance: bool = False
) -> Iterator[tuple[int, np.ndarray]]:
    """Yield (frame_index, BGR frame) every `stride` frames."""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {path}")
    idx = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if idx % max(stride, 1) == 0:
                yield idx, enhance_frame(frame) if enhance else frame
            idx += 1
    finally:
        cap.release()
