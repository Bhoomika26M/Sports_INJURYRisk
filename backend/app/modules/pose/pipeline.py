"""Pose estimation pipeline using MediaPipe and YOLOv8-pose.

Supports both MediaPipe APIs:
- Legacy `mp.solutions.pose` (mediapipe==0.10.21 on Python 3.12 Docker image)
- New Tasks `PoseLandmarker` (mediapipe>=0.10.30 on Python 3.13 host, where
  `solutions` was removed). Output format is identical either way.
"""

import logging
import os
import urllib.request

import cv2
import numpy as np
import mediapipe as mp
from ultralytics import YOLO

logger = logging.getLogger(__name__)

_HAS_LEGACY_POSE = hasattr(mp, "solutions") and hasattr(getattr(mp, "solutions", None), "pose")
if _HAS_LEGACY_POSE:
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
else:
    mp_pose = None
    mp_drawing = None

POSE_LANDMARKER_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
)
POSE_LANDMARKER_MODEL_PATH = os.environ.get(
    "POSE_LANDMARKER_MODEL_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "pose_landmarker_lite.task"),
)


def _ensure_landmarker_model() -> str:
    path = os.path.abspath(POSE_LANDMARKER_MODEL_PATH)
    if os.path.exists(path):
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    logger.info(f"Downloading PoseLandmarker bundle to {path}")
    urllib.request.urlretrieve(POSE_LANDMARKER_MODEL_URL, path)
    return path


def extract_world_landmarks(pose_world_landmarks) -> dict:
    """Extract world landmarks into {str(index): [x, y, z]}.

    Accepts legacy `pose_world_landmarks.landmark` as well as Tasks
    `pose_world_landmarks` list (one entry per detected pose).
    """
    out = {}
    landmarks = getattr(pose_world_landmarks, "landmark", pose_world_landmarks)
    # Tasks API returns a list of poses; take the first pose.
    if isinstance(landmarks, list) and landmarks and hasattr(landmarks[0], "x") is False:
        # list of poses -> first pose is itself a list of landmarks
        landmarks = landmarks[0]
    for i, lm in enumerate(landmarks):
        out[str(i)] = [float(lm.x), float(lm.y), float(lm.z)]
    return out


def _extract_boxes_and_ids(result) -> list[tuple[int | None, tuple[float, float, float, float]]]:
    """Pull [(track_id | None, (x1, y1, x2, y2)), ...] out of one YOLO result.

    `track_id` is None when the model ran in plain detect mode (no tracker).
    Never raises on empty/missing boxes — returns [].
    """
    boxes = getattr(result, "boxes", None)
    if boxes is None:
        return []
    xyxy = getattr(boxes, "xyxy", None)
    if xyxy is None or len(xyxy) == 0:
        return []
    ids = getattr(boxes, "id", None)
    out = []
    for i, b in enumerate(xyxy):
        tid = None
        if ids is not None and len(ids) > i and ids[i] is not None:
            try:
                tid = int(ids[i])
            except (TypeError, ValueError):
                tid = None
        try:
            x1, y1, x2, y2 = (float(v) for v in b)
        except (TypeError, ValueError):
            continue
        out.append((tid, (x1, y1, x2, y2)))
    return out


def select_main_track(tracks: dict[int, dict[int, tuple]]) -> int | None:
    """Pick the main athlete's track id from per-track per-frame boxes.

    `tracks`: {track_id: {frame_idx: box}}. Most frames present wins;
    ties break toward the largest median box area (closest/most prominent
    person). Returns None when there are no tracks.
    """
    if not tracks:
        return None

    def _score(item: tuple[int, dict]) -> tuple[int, float]:
        _tid, frames = item
        areas = sorted((b[2] - b[0]) * (b[3] - b[1]) for b in frames.values())
        median_area = areas[len(areas) // 2] if areas else 0.0
        return (len(frames), median_area)

    return max(tracks.items(), key=_score)[0]


def should_skip_frame(box, subject_boxes, full_frame_fallback: bool) -> bool:
    """True when pose must NOT be attempted on this frame.

    Tracking is active (``subject_boxes`` given) but the selected athlete is absent from this frame and the
    video has several people: a full-frame pose pass would measure whichever OTHER person it finds and silently
    mix identities into the athlete's metrics. Single-person videos keep the full-frame fallback (nobody else
    to mix up), as do untracked videos (``subject_boxes`` is None).
    """
    return box is None and subject_boxes is not None and not full_frame_fallback


def _reset_tracker_state(model) -> None:
    """Best-effort reset of the YOLO tracker's persistent state.

    `model.track(persist=True)` keeps ID state on the shared worker model
    across videos — without a reset, a new video can inherit ghost IDs from
    the previous one. Ultralytics exposes no stable public reset API, so try
    the known paths defensively and log what happened.
    """
    try:
        predictor = getattr(model, "predictor", None)
        trackers = getattr(predictor, "trackers", None) if predictor is not None else None
        if trackers:
            for tracker in trackers:
                reset = getattr(tracker, "reset", None)
                if callable(reset):
                    reset()
            logger.info("YOLO tracker state reset for new video")
            return
        logger.info("YOLO tracker has no prior state to reset (fresh predictor)")
    except Exception as e:
        logger.warning(f"YOLO tracker reset failed, IDs may carry over: {e}")


def track_persons(video_path: str, model=None, stride: int = 1) -> dict:
    """Track every person across the video with persistent YOLO IDs.

    Returns {
        "person_counts": [n_persons per processed frame],
        "tracks": {track_id: {frame_idx: (x1, y1, x2, y2)}},
        "main_track_id": int | None (see select_main_track),
        "max_persons": int,
        "frames_processed": int,
        "frame_width"/"frame_height": int | None (pixels),
        "tracked": bool (False when the model has no .track or IDs came back empty,
                         meaning per-frame identity is unavailable),
    }
    Frames are processed sequentially (stride=1) so tracker IDs stay consistent.
    """
    if model is None:
        model = YOLO("yolov8n-pose.pt")
    _reset_tracker_state(model)
    use_track = callable(getattr(model, "track", None))

    cap = cv2.VideoCapture(video_path)
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or None
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or None
    tracks: dict[int, dict[int, tuple]] = {}
    person_counts: list[int] = []
    saw_ids = False
    frame_idx = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if frame_idx % stride == 0:
                try:
                    if use_track:
                        result = model.track(frame, persist=True, verbose=False)[0]
                    else:
                        result = model(frame, verbose=False)[0]
                except Exception as e:
                    logger.warning(f"YOLO inference failed on frame {frame_idx}, counting 0: {e}")
                    person_counts.append(0)
                    frame_idx += 1
                    continue
                dets = _extract_boxes_and_ids(result)
                person_counts.append(len(dets))
                for tid, box in dets:
                    if tid is None:
                        continue
                    saw_ids = True
                    tracks.setdefault(tid, {})[frame_idx] = box
            frame_idx += 1
    finally:
        cap.release()

    main_track_id = select_main_track(tracks) if saw_ids else None
    if not saw_ids:
        tracks = {}
        logger.warning("YOLO returned no track IDs — running untracked full-frame pose")
    return {
        "person_counts": person_counts,
        "tracks": tracks,
        "main_track_id": main_track_id,
        "max_persons": max(person_counts, default=0),
        "frames_processed": frame_idx,
        "tracked": saw_ids,
        "frame_width": frame_width,
        "frame_height": frame_height,
    }


def crop_to_box(frame, box: tuple[float, float, float, float], pad_ratio: float = 0.15,
                min_size: int = 64) -> tuple:
    """Crop `frame` to `box` plus padding, clamped to frame bounds.

    Returns (crop, origin_x, origin_y) where origin is the crop's top-left
    corner in original-frame pixels. Falls back to the full frame when the
    box is degenerate or the padded crop would be too small to pose on.
    """
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = box
    bw, bh = x2 - x1, y2 - y1
    if bw <= 0 or bh <= 0:
        return frame, 0, 0
    px, py = bw * pad_ratio, bh * pad_ratio
    cx1 = max(0, int(x1 - px))
    cy1 = max(0, int(y1 - py))
    cx2 = min(w, int(x2 + px))
    cy2 = min(h, int(y2 + py))
    if cx2 - cx1 < min_size or cy2 - cy1 < min_size:
        return frame, 0, 0
    return frame[cy1:cy2, cx1:cx2], cx1, cy1


def map_crop_norm_to_full(nx: float, ny: float, origin_x: int, origin_y: int,
                          crop_w: int, crop_h: int, full_w: int, full_h: int) -> tuple[float, float]:
    """Map a landmark normalized in crop space to normalized full-frame space."""
    if crop_w <= 0 or crop_h <= 0 or full_w <= 0 or full_h <= 0:
        return (nx, ny)
    return ((origin_x + nx * crop_w) / full_w, (origin_y + ny * crop_h) / full_h)


def _draw_mapped_landmarks(frame, norm_landmarks, origin_x, origin_y, crop_w, crop_h):
    """Draw circles for crop-space normalized landmarks mapped to full-frame coords."""
    full_h, full_w = frame.shape[:2]
    for lm in norm_landmarks:
        fx, fy = map_crop_norm_to_full(lm.x, lm.y, origin_x, origin_y, crop_w, crop_h, full_w, full_h)
        cv2.circle(frame, (int(fx * full_w), int(fy * full_h)), 3, (0, 255, 0), -1)


def _run_mediapipe_legacy(cap, fps, total_frames, width, height, annotate_output_path, progress_callback, subject_boxes=None, full_frame_fallback=True):
    writer = None
    if annotate_output_path:
        writer = cv2.VideoWriter(annotate_output_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    frame_results = []
    with mp_pose.Pose(static_image_mode=False, model_complexity=1) as pose:
        frame_idx = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            timestamp_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC))
            box = subject_boxes.get(frame_idx) if subject_boxes else None
            if box is not None:
                crop, ox, oy = crop_to_box(frame, box)
                ch, cw = crop.shape[:2]
                rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            else:
                crop, ox, oy, ch, cw = None, 0, 0, height, width
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            skip = should_skip_frame(box, subject_boxes, full_frame_fallback)
            result = None if skip else pose.process(rgb)
            if result is not None and result.pose_world_landmarks:
                frame_results.append({
                    "frame_number": frame_idx,
                    "timestamp_ms": timestamp_ms,
                    "world_landmarks": extract_world_landmarks(result.pose_world_landmarks),
                })
                if writer is not None and result.pose_landmarks:
                    if box is not None:
                        _draw_mapped_landmarks(frame, result.pose_landmarks.landmark, ox, oy, cw, ch)
                    else:
                        mp_drawing.draw_landmarks(
                            frame, result.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                            mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                        )
            if box is not None:
                x1, y1, x2, y2 = (int(v) for v in box)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            if writer is not None:
                writer.write(frame)
            if progress_callback and total_frames > 0:
                if frame_idx % max(1, total_frames // 10) == 0:
                    progress_callback(int(100 * frame_idx / total_frames))
            frame_idx += 1
    if writer is not None:
        writer.release()
    detection_rate = len(frame_results) / frame_idx if frame_idx > 0 else 0.0
    return frame_results, detection_rate


def _run_mediapipe_tasks(cap, fps, total_frames, width, height, annotate_output_path, progress_callback, subject_boxes=None, full_frame_fallback=True):
    from mediapipe.tasks.python import vision
    from mediapipe.tasks.python.core.base_options import BaseOptions
    from mediapipe.tasks.python.vision.core.vision_task_running_mode import VisionTaskRunningMode

    model_path = _ensure_landmarker_model()
    options = vision.PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model_path),
        running_mode=VisionTaskRunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    writer = None
    if annotate_output_path:
        writer = cv2.VideoWriter(annotate_output_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    frame_results = []
    with vision.PoseLandmarker.create_from_options(options) as landmarker:
        frame_idx = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            timestamp_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC))
            box = subject_boxes.get(frame_idx) if subject_boxes else None
            if box is not None:
                crop, ox, oy = crop_to_box(frame, box)
                ch, cw = crop.shape[:2]
                rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            else:
                crop, ox, oy, ch, cw = None, 0, 0, height, width
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            skip = should_skip_frame(box, subject_boxes, full_frame_fallback)
            result = None
            if not skip:
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                result = landmarker.detect_for_video(mp_image, timestamp_ms)
            if result is not None and result.pose_world_landmarks:
                frame_results.append({
                    "frame_number": frame_idx,
                    "timestamp_ms": timestamp_ms,
                    "world_landmarks": extract_world_landmarks(result.pose_world_landmarks),
                })
                if writer is not None and result.pose_landmarks:
                    if box is not None:
                        _draw_mapped_landmarks(frame, result.pose_landmarks[0], ox, oy, cw, ch)
                    else:
                        for lm in result.pose_landmarks[0]:
                            x = int(lm.x * width)
                            y = int(lm.y * height)
                            cv2.circle(frame, (x, y), 3, (0, 255, 0), -1)
            if box is not None:
                x1, y1, x2, y2 = (int(v) for v in box)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            if writer is not None:
                writer.write(frame)
            if progress_callback and total_frames > 0:
                if frame_idx % max(1, total_frames // 10) == 0:
                    progress_callback(int(100 * frame_idx / total_frames))
            frame_idx += 1
    if writer is not None:
        writer.release()
    detection_rate = len(frame_results) / frame_idx if frame_idx > 0 else 0.0
    return frame_results, detection_rate


def run_mediapipe_full_pass(video_path: str, annotate_output_path: str | None = None, progress_callback=None,
                            subject_boxes: dict[int, tuple | None] | None = None,
                            full_frame_fallback: bool = True):
    """
    Run MediaPipe pose over all frames.
    Extract world landmarks, and optionally burn the skeleton into an output video.
    Calls progress_callback(pct) periodically if provided.
    `subject_boxes`: optional {frame_idx: box | None} for the tracked main
    athlete — frames with a box are cropped to the subject before pose, so
    multi-person videos analyze one consistent person. None = full-frame
    behavior (legacy, single-person clips).
    `full_frame_fallback`: when tracking is active and the athlete's box is missing on a frame, run full-frame
    pose anyway (True, safe for single-person clips) or skip the frame (False, required for multi-person clips
    so another person is never measured as the athlete). The detection rate then means "frames where the
    selected athlete was measured".
    """
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    try:
        if _HAS_LEGACY_POSE:
            return _run_mediapipe_legacy(cap, fps, total_frames, width, height, annotate_output_path, progress_callback, subject_boxes, full_frame_fallback)
        logger.info("mp.solutions.pose unavailable, using Tasks PoseLandmarker")
        return _run_mediapipe_tasks(cap, fps, total_frames, width, height, annotate_output_path, progress_callback, subject_boxes, full_frame_fallback)
    finally:
        cap.release()


def extract_thumbnail(video_path: str, output_path: str) -> None:
    """Extract a frame from the middle of the video to use as a thumbnail."""
    cap = cv2.VideoCapture(video_path)
    midpoint = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) // 2
    cap.set(cv2.CAP_PROP_POS_FRAMES, midpoint)
    ok, frame = cap.read()
    if ok:
        cv2.imwrite(output_path, frame)
    cap.release()