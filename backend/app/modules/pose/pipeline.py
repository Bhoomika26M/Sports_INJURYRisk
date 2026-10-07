"""Pose estimation pipeline using MediaPipe and YOLOv8-pose.

Supports both MediaPipe APIs:
- Legacy `mp.solutions.pose` (mediapipe==0.10.21 on Python 3.12 Docker image)
- New Tasks `PoseLandmarker` (mediapipe>=0.10.30 on Python 3.13 host, where
  `solutions` was removed). Output format is identical either way.
"""

import contextlib
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

# Tasks-API model variant: lite < full < heavy (accuracy, and cost). The old hard-coded
# default was `lite`, the least accurate; `full` is the default now. Override with
# POSE_LANDMARKER_VARIANT=lite|full|heavy. Legacy API: POSE_MODEL_COMPLEXITY=0|1|2.
POSE_LANDMARKER_VARIANT = os.environ.get("POSE_LANDMARKER_VARIANT", "full")
POSE_MODEL_COMPLEXITY = int(os.environ.get("POSE_MODEL_COMPLEXITY", "1"))
_BACKEND_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..")


def _model_url(variant: str) -> str:
    return (
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
        f"pose_landmarker_{variant}/float16/1/pose_landmarker_{variant}.task"
    )


def _model_path(variant: str) -> str:
    return os.path.abspath(os.environ.get(
        "POSE_LANDMARKER_MODEL_PATH", os.path.join(_BACKEND_ROOT, f"pose_landmarker_{variant}.task")
    ))


def _ensure_landmarker_model() -> str:
    """Path to the requested landmarker bundle, downloading it if needed.

    If the download fails (offline host) fall back to any bundle already on disk rather
    than failing every video.
    """
    path = _model_path(POSE_LANDMARKER_VARIANT)
    if os.path.exists(path):
        return path
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        logger.info(f"Downloading PoseLandmarker '{POSE_LANDMARKER_VARIANT}' bundle to {path}")
        urllib.request.urlretrieve(_model_url(POSE_LANDMARKER_VARIANT), path)
        return path
    except Exception as e:
        for variant in ("heavy", "full", "lite"):
            fallback = _model_path(variant)
            if os.path.exists(fallback):
                logger.warning(f"Could not download '{POSE_LANDMARKER_VARIANT}' model ({e}); using existing '{variant}' bundle")
                return fallback
        raise


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


def extract_visibility(pose_world_landmarks) -> list[float] | None:
    """Per-landmark visibility in [0, 1] (the model's confidence the joint is actually seen),
    or None when the model exposes none. Same accepted shapes as extract_world_landmarks."""
    landmarks = getattr(pose_world_landmarks, "landmark", pose_world_landmarks)
    if isinstance(landmarks, list) and landmarks and hasattr(landmarks[0], "x") is False:
        landmarks = landmarks[0]
    out = []
    for lm in landmarks:
        v = getattr(lm, "visibility", None)
        if v is None:
            return None
        out.append(float(v))
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


# --------------------------------------------------------------------------- #
# Tracker choice + ID-fragment merging
# --------------------------------------------------------------------------- #

#: Which Ultralytics tracker config to run. BoT-SORT is the default because its motion
#: model survives fast direction changes (cutting left/right) far better than ByteTrack's
#: constant-velocity assumption — the failure that fragmented one lateral-moving athlete
#: into several track IDs ("several people" when there was clearly one). Override with
#: YOLO_TRACKER=bytetrack.yaml to get the old behaviour.
YOLO_TRACKER = os.environ.get("YOLO_TRACKER", "botsort.yaml")

#: Max temporal gap (seconds) across which two track fragments may still be the same
#: person. Longer gaps risk merging two DIFFERENT people who entered sequentially.
MAX_FRAGMENT_GAP_S = 0.5
#: Two fragments merge only if their median box heights differ by less than this fraction.
FRAGMENT_SIZE_TOL = 0.35
#: ...and the box-centre jump across the gap is human-plausible: at most this many
#: subject-heights per second (an all-out sprint is ~5-6 heights/s, so this is generous).
MAX_FRAGMENT_SPEED_HEIGHTS_S = 8.0


def _fragment_stats(frames: dict[int, tuple]) -> dict:
    idx = sorted(frames)
    boxes = [frames[i] for i in idx]
    heights = sorted(b[3] - b[1] for b in boxes)

    def center(b):
        return ((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0)

    return {
        "first": idx[0],
        "last": idx[-1],
        "height": heights[len(heights) // 2],
        "first_center": center(boxes[0]),
        "last_center": center(boxes[-1]),
    }


def merge_track_fragments(tracks: dict[int, dict[int, tuple]], fps: float,
                           *, max_gap_s: float = MAX_FRAGMENT_GAP_S) -> dict[int, dict[int, tuple]]:
    """Merge track fragments of the SAME person split by tracker ID switches.

    Losing the subject on a sharp cut and re-acquiring it under a new ID is the normal
    failure mode of online trackers on lateral sport motion. Without merging, one athlete
    cutting left/right reads as several substantive tracks: a false "multiple people"
    diagnosis and a deflated main-track coverage (each fragment is short).

    Two fragments merge when ALL hold:
    * they are temporally DISJOINT (no shared frames) with a gap <= ``max_gap_s`` —
      two people visible simultaneously can never merge, so a genuine group scene is
      never collapsed into one person;
    * their median box heights are similar (same person, not a bystander);
    * the box-centre jump across the gap is human-plausible
      (<= MAX_FRAGMENT_SPEED_HEIGHTS_S subject-heights/s — no teleports).
    Merging is transitive (union-find). The merged track keeps the earliest
    fragment's ID. Pure function — unit-tested with synthetic track scripts.
    """
    ids = list(tracks)
    if len(ids) < 2:
        return tracks
    stats = {tid: _fragment_stats(tracks[tid]) for tid in ids}
    parent = {tid: tid for tid in ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        # the merged track keeps the earliest-starting fragment's ID
        if (stats[ra]["first"], ra) <= (stats[rb]["first"], rb):
            parent[rb] = ra
        else:
            parent[ra] = rb

    fps = fps if fps and fps > 0 else 30.0
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            sa, sb = stats[a], stats[b]
            if sa["first"] <= sb["last"] and sb["first"] <= sa["last"]:
                continue  # overlapping in time: different people, never merge
            if sa["last"] < sb["first"]:
                se, sl = sa, sb
            elif sb["last"] < sa["first"]:
                se, sl = sb, sa
            else:
                continue
            gap_s = (sl["first"] - se["last"]) / fps
            if gap_s <= 0 or gap_s > max_gap_s:
                continue
            h_ref = max(se["height"], sl["height"], 1e-6)
            if abs(se["height"] - sl["height"]) / h_ref > FRAGMENT_SIZE_TOL:
                continue
            dx = sl["first_center"][0] - se["last_center"][0]
            dy = sl["first_center"][1] - se["last_center"][1]
            if (dx * dx + dy * dy) ** 0.5 > MAX_FRAGMENT_SPEED_HEIGHTS_S * h_ref * gap_s:
                continue
            union(a, b)

    merged: dict[int, dict[int, tuple]] = {}
    for tid in ids:
        merged.setdefault(find(tid), {}).update(tracks[tid])
    return merged


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


def track_persons(video_path: str, model=None, stride: int = 1, fps: float = 30.0) -> dict:
    """Track every person across the video with persistent YOLO IDs.

    Returns {
        "person_counts": [n_persons per processed frame],
        "tracks": {track_id: {frame_idx: (x1, y1, x2, y2)}} — ID-switch fragments of the
                   same person are MERGED (see merge_track_fragments), so one lateral-moving
                   athlete reads as one track, not several;
        "main_track_id": int | None (see select_main_track),
        "max_persons": int,
        "frames_processed": int,
        "frame_width"/"frame_height": int | None (pixels),
        "tracked": bool (False when the model has no .track or IDs came back empty,
                         meaning per-frame identity is unavailable),
    }
    Frames are processed sequentially (stride=1) so tracker IDs stay consistent.
    `fps` is the clip's frame rate, used only to express the fragment-merge gap in seconds.
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
                        result = model.track(frame, persist=True, verbose=False, tracker=YOLO_TRACKER)[0]
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

    if saw_ids and len(tracks) > 1:
        n_before = len(tracks)
        tracks = merge_track_fragments(tracks, fps)
        if len(tracks) != n_before:
            logger.info(
                f"Merged {n_before} raw track IDs into {len(tracks)} subject(s) "
                f"(ID-switch fragments of the same person)"
            )
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


# --------------------------------------------------------------------------- #
# Video probing, stride, lighting
# --------------------------------------------------------------------------- #

MAX_ANALYSIS_FPS = 60.0


def compute_stride(fps: float) -> int:
    """Process every Nth frame so slow-motion footage (120/240 fps) stays within the
    worker's time budget. <= 60 fps is always processed frame-for-frame."""
    if not fps or fps <= MAX_ANALYSIS_FPS:
        return 1
    return int(np.ceil(fps / MAX_ANALYSIS_FPS))


def probe_video(video_path: str) -> dict:
    cap = cv2.VideoCapture(video_path)
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        fps = float(fps) if fps and np.isfinite(fps) and fps > 0 else 30.0
        return {
            "fps": fps,
            "frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        }
    finally:
        cap.release()


def _luma_stats(frame_bgr) -> tuple[float, float]:
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    p5, p95 = np.percentile(gray, [5, 95])
    return float(gray.mean()), float(p95 - p5)


def scan_lighting(video_path: str, n_samples: int = 12) -> dict:
    """Sample frames across the clip and report brightness/contrast (+ whether to enhance)."""
    from app.modules.pose.analysis import assess_lighting

    cap = cv2.VideoCapture(video_path)
    samples = []
    try:
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total <= 0:
            return assess_lighting([])
        for pos in np.linspace(0, max(total - 1, 0), num=min(n_samples, total), dtype=int):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(pos))
            ok, frame = cap.read()
            if ok:
                samples.append(_luma_stats(frame))
    finally:
        cap.release()
    return assess_lighting(samples)


GAMMA_TARGET_LUMA = 110.0
GAMMA_MIN = 0.45  # never lift harder than this: beyond it noise is amplified more than signal


def enhance_low_light(rgb):
    """Brighten and flatten dim footage so the pose model sees what it was trained on.

    1. Adaptive gamma on the lightness channel, ONLY when the frame is genuinely dark
       (mean L < 70), steering its mean toward ~110 (gamma floored at 0.45).
    2. CLAHE on lightness to restore local contrast without shifting colour.

    Applied only when scan_lighting() flags the clip as low-light, so well-lit footage is
    processed exactly as before.
    """
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    mean_l = float(l.mean())
    if 1.0 < mean_l < 70.0:
        gamma = float(np.clip(np.log(GAMMA_TARGET_LUMA / 255.0) / np.log(mean_l / 255.0), GAMMA_MIN, 1.0))
        lut = (255.0 * (np.arange(256) / 255.0) ** gamma).astype(np.uint8)
        l = cv2.LUT(l, lut)
    l = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(l)
    return cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2RGB)


# --------------------------------------------------------------------------- #
# Detectors (legacy solutions API / Tasks API) behind one interface
# --------------------------------------------------------------------------- #

class _Detection:
    __slots__ = ("world", "visibility", "norm")

    def __init__(self, world, visibility, norm):
        self.world, self.visibility, self.norm = world, visibility, norm


@contextlib.contextmanager
def _legacy_detector():
    with mp_pose.Pose(static_image_mode=False, model_complexity=POSE_MODEL_COMPLEXITY) as pose:
        def detect(rgb, _timestamp_ms):
            result = pose.process(rgb)
            if not result.pose_world_landmarks:
                return None
            norm = result.pose_landmarks.landmark if result.pose_landmarks else None
            return _Detection(
                extract_world_landmarks(result.pose_world_landmarks),
                extract_visibility(result.pose_world_landmarks),
                norm,
            )
        yield detect, f"mediapipe-legacy-complexity{POSE_MODEL_COMPLEXITY}"


@contextlib.contextmanager
def _tasks_detector():
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
    with vision.PoseLandmarker.create_from_options(options) as landmarker:
        def detect(rgb, timestamp_ms):
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = landmarker.detect_for_video(mp_image, timestamp_ms)
            if not result.pose_world_landmarks:
                return None
            norm = result.pose_landmarks[0] if result.pose_landmarks else None
            return _Detection(
                extract_world_landmarks(result.pose_world_landmarks),
                extract_visibility(result.pose_world_landmarks),
                norm,
            )
        yield detect, f"mediapipe-tasks-{os.path.basename(model_path)}"


# --------------------------------------------------------------------------- #
# The single frame loop
# --------------------------------------------------------------------------- #

def _run_pass(cap, detect, fps, total_frames, annotate_output_path, progress_callback,
              subject_boxes, stride, enhance, diagnostics, full_frame_fallback=True):
    """Read every frame, run `detect` on every `stride`-th one.

    Robustness rules (each one was a real way to lose a whole video before):
    * timestamps are derived from frame index and fps and forced strictly increasing —
      cap.get(POS_MSEC) can be 0/duplicated on phone or variable-frame-rate clips, and the
      Tasks VIDEO mode raises on non-increasing timestamps;
    * a detector exception on one frame costs that frame, not the video;
    * with several people in frame and the athlete untracked on a frame, that frame is SKIPPED
      (``full_frame_fallback=False``) rather than measuring whichever other person pose finds —
      so the detection rate means "frames where the selected athlete was measured";
    * the annotated-video writer is sized from the first decoded frame — for portrait phone
      clips CAP_PROP_FRAME_WIDTH/HEIGHT can disagree with the auto-rotated frames.
    """
    writer = None
    frame_results = []
    last_ts = -1
    processed = errors = 0
    frame_idx = -1
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame_idx += 1
            if frame_idx % stride:
                continue
            processed += 1
            full_h, full_w = frame.shape[:2]
            if annotate_output_path and writer is None:
                writer = cv2.VideoWriter(
                    annotate_output_path, cv2.VideoWriter_fourcc(*"mp4v"), max(fps / stride, 1.0), (full_w, full_h)
                )

            timestamp_ms = max(last_ts + 1, int(round(frame_idx * 1000.0 / fps)))
            last_ts = timestamp_ms

            box = subject_boxes.get(frame_idx) if subject_boxes else None
            if box is not None:
                crop, ox, oy = crop_to_box(frame, box)
            else:
                crop, ox, oy = frame, 0, 0
            ch, cw = crop.shape[:2]
            rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            if enhance:
                rgb = enhance_low_light(rgb)

            try:
                det = None if should_skip_frame(box, subject_boxes, full_frame_fallback) else detect(rgb, timestamp_ms)
            except Exception as e:  # noqa: BLE001 — isolate per-frame failures
                errors += 1
                if errors <= 3:
                    logger.warning(f"Pose detection failed on frame {frame_idx}: {e}")
                det = None

            if det is not None:
                frame_results.append({
                    "frame_number": frame_idx,
                    "timestamp_ms": timestamp_ms,
                    "world_landmarks": det.world,
                    "visibility": det.visibility,
                })
                if writer is not None and det.norm is not None:
                    _draw_mapped_landmarks(frame, det.norm, ox, oy, cw, ch)
            if writer is not None:
                if box is not None:
                    x1, y1, x2, y2 = (int(v) for v in box)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                writer.write(frame)

            if progress_callback and total_frames > 0 and frame_idx % max(1, total_frames // 10) == 0:
                progress_callback(int(100 * frame_idx / total_frames))
    finally:
        if writer is not None:
            writer.release()

    diagnostics.update({
        "frames_read": frame_idx + 1,
        "frames_processed": processed,
        "frame_errors": errors,
        "stride": stride,
    })
    detection_rate = len(frame_results) / processed if processed else 0.0
    return frame_results, detection_rate


def run_mediapipe_full_pass(video_path: str, annotate_output_path: str | None = None, progress_callback=None,
                            subject_boxes: dict[int, tuple | None] | None = None,
                            diagnostics: dict | None = None, stride: int | None = None,
                            full_frame_fallback: bool = True):
    """Run MediaPipe pose over the video; returns (frame_results, detection_rate).

    Each frame result: {frame_number, timestamp_ms, world_landmarks, visibility}.
    `subject_boxes`: optional {frame_idx: box | None} for the tracked main athlete — frames
    with a box are cropped to the subject before pose, so multi-person videos analyze one
    consistent person. `stride` must match the stride used for tracking (default: derived
    from the clip's fps). `diagnostics` (optional dict) is filled with frame counts, stride,
    lighting and model info for the quality report.
    `full_frame_fallback`: when tracking is active and the athlete's box is missing on a frame, run
    full-frame pose anyway (True, safe for single-person clips) or skip the frame (False, required for
    multi-person clips so another person is never measured as the athlete).
    """
    diagnostics = diagnostics if diagnostics is not None else {}
    info = probe_video(video_path)
    fps = info["fps"]
    stride = stride or compute_stride(fps)

    lighting = scan_lighting(video_path)
    enhance = bool(lighting.get("low_light"))
    diagnostics.update({"lighting": lighting, "contrast_enhanced": enhance, "fps": fps})

    cap = cv2.VideoCapture(video_path)
    try:
        if _HAS_LEGACY_POSE:
            ctx = _legacy_detector()
        else:
            logger.info("mp.solutions.pose unavailable, using Tasks PoseLandmarker")
            ctx = _tasks_detector()
        with ctx as (detect, model_name):
            diagnostics["model"] = model_name
            return _run_pass(cap, detect, fps, info["frames"], annotate_output_path,
                             progress_callback, subject_boxes, stride, enhance, diagnostics,
                             full_frame_fallback)
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