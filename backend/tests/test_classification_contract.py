"""The classification stored with a clip is exactly what the web app reads.

T4 built the results card against guessed field names (`detected_movement`, `detected_view`); the backend writes
`movement_type`, `camera_view`, `agrees`, `suggested`, so on real data the card silently rendered nothing and no test
noticed. The real shape is pinned in a file BOTH sides check:
  here          the stored classification must equal frontend/e2e/fixtures/classification_contract.json
  frontend      `node e2e/classification_contract.mjs` runs the page's own `classificationRows` over that same file
Change the shape on purpose: `UPDATE_CONTRACT_FIXTURE=1 pytest tests/test_classification_contract.py`, then update types.ts.
"""

import json
import os
from pathlib import Path

import pytest

from app.modules.pose.processing import analyze_frames
from tests.synth import run_frames, squat_frames
from tests.test_classification import _still, knee_frames

FIXTURE = Path(__file__).resolve().parents[2] / "frontend" / "e2e" / "fixtures" / "classification_contract.json"
READ_BY_THE_UI = ("movement_type", "camera_view", "declared", "agrees", "suggested")
CASES = [  # name, frames, declared (movement, view), identified-from-the-footage (auto upload)
    ("squat_matches", squat_frames(), ("squatting", "sagittal"), False),
    ("run_labelled_squat", run_frames(170, kmax=80, seconds=8), ("squatting", "sagittal"), False),
    ("run_labelled_sprinting", run_frames(170, kmax=80, seconds=8), ("sprinting", "sagittal"), False),
    ("squat_labelled_frontal", squat_frames(), ("squatting", "frontal"), False),
    ("standing_still", knee_frames(_still(6)), ("squatting", "sagittal"), False),
    ("squat_auto", squat_frames(), ("squatting", "sagittal"), True),
]


def _stored(frames, movement, view, auto):
    _, analysis = analyze_frames(frames, movement, view, 30.0, auto=auto)
    return {k: analysis["classification"][k] for k in READ_BY_THE_UI}


def _cases():
    return [{"name": n, "video": {"movement_type": m, "camera_view": v}, "classification": _stored(f, m, v, a)}
            for n, f, (m, v), a in CASES]


def test_the_stored_classification_has_the_keys_the_ui_reads():
    c = _cases()[1]["classification"]
    assert set(c) == set(READ_BY_THE_UI)
    for group in ("declared", "agrees", "suggested"):
        assert set(c[group]) == {"movement_type", "camera_view"}
    assert c["agrees"]["movement_type"] is False and c["suggested"]["movement_type"] == "running"


def test_the_frontend_fixture_is_what_the_backend_stores():
    got = _cases()
    if os.environ.get("UPDATE_CONTRACT_FIXTURE"):
        FIXTURE.write_text(json.dumps(got, indent=2) + "\n", encoding="utf-8")
    if not FIXTURE.exists():
        pytest.skip("frontend/ is not next to backend/ (backend-only checkout)")
    assert json.loads(FIXTURE.read_text(encoding="utf-8")) == got, \
        "the classification shape changed: UPDATE_CONTRACT_FIXTURE=1 pytest tests/test_classification_contract.py, then update frontend/src/lib/types.ts"
