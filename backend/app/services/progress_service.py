"""Live processing progress state, persisted as JSON next to the video.

The background analysis worker writes updates here after every stage and
after every processed chunk; the frontend polls GET /videos/{id}/progress
(plus /preview-frame) for a step-by-step live view of the analysis.
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from app.core.config import settings

# Stage -> (percent when stage starts, human label)
STAGES = {
    "preprocessing": (0, "Opening video and extracting metadata"),
    "pose_estimation": (5, "Tracking athlete and estimating 33-point pose"),
    "analyzing": (85, "Computing biomechanics and injury risk"),
    "completed": (100, "Analysis complete"),
    "failed": (0, "Processing failed"),
}


def progress_path(video_id: int) -> Path:
    return Path(settings.VIDEO_UPLOAD_DIR) / f"progress_{video_id}.json"


def preview_path(video_id: int) -> Path:
    return Path(settings.VIDEO_UPLOAD_DIR) / f"preview_{video_id}.jpg"


def init_progress(video_id: int) -> Dict:
    """Create/reset progress state for a new run."""
    state = {
        "video_id": video_id,
        "status": "preprocessing",
        "stage": "preprocessing",
        "stage_label": STAGES["preprocessing"][1],
        "percent": 0,
        "frames_processed": 0,
        "total_frames": None,
        "valid_pose_frames": 0,
        "mean_confidence": None,
        "current_angles": {},
        "risk": None,
        "updated_at": datetime.utcnow().isoformat(),
        "error": None,
    }
    _write(video_id, state)
    # Clean stale preview from a previous run
    try:
        if preview_path(video_id).exists():
            preview_path(video_id).unlink()
    except OSError:
        pass
    return state


def update(video_id: int, **fields) -> Optional[Dict]:
    """Merge fields into the progress state (atomic replace)."""
    state = read(video_id)
    if state is None:
        state = {"video_id": video_id}
    state.update(fields)
    if "stage" in fields and fields["stage"] in STAGES and "stage_label" not in fields:
        state["stage_label"] = STAGES[fields["stage"]][1]
        state["percent"] = max(state.get("percent", 0), STAGES[fields["stage"]][0])
    state["updated_at"] = datetime.utcnow().isoformat()
    _write(video_id, state)
    return state


def set_stage(video_id: int, stage: str, **fields) -> Optional[Dict]:
    if stage not in STAGES:
        return None
    return update(
        video_id,
        stage=stage,
        stage_label=STAGES[stage][1],
        percent=STAGES[stage][0],
        status=stage,
        **fields,
    )


def set_progress(video_id: int, percent: float, **fields) -> Optional[Dict]:
    return update(video_id, percent=round(float(percent), 1), **fields)


def read(video_id: int) -> Optional[Dict]:
    path = progress_path(video_id)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def clear(video_id: int) -> None:
    try:
        path = progress_path(video_id)
        if path.exists():
            path.unlink()
    except OSError:
        pass


def _write(video_id: int, state: Dict) -> None:
    """Atomic write so readers never see a half-written file."""
    path = progress_path(video_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd, tmp = tempfile.mkstemp(
            dir=str(path.parent), prefix=f".progress_{video_id}_", suffix=".tmp"
        )
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, default=float)
        os.replace(tmp, path)
    except OSError:
        # Fallback: non-atomic write
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, default=float)
