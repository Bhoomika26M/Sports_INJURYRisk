"""Offline self-check for scripts/process_corpus.py: the catalog labels are ones the API accepts, no recording can be
counted twice, and the verdict / baseline-count logic behaves. (The HTTP flow is checked against the live API, not here.)"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import process_corpus as pc  # noqa: E402

from app.seed import MOVEMENT_TYPES  # noqa: E402

VIEWS = {m["code"]: set(m["camera_views"]) for m in MOVEMENT_TYPES}


def test_every_label_is_one_the_api_accepts():
    clips = pc.plan()
    assert len(clips) == 14 and len({c["name"] for c in clips}) == 14
    for c in clips:
        assert c["view"] in VIEWS[c["movement"]], c["name"]


def test_a_recording_cannot_count_twice():
    by_name = {c["name"]: c for c in pc.plan()}
    for twin, original in pc.TWINS.items():
        assert by_name[twin]["twin"] and by_name[twin]["athlete"] == by_name[original]["athlete"]
    assert sum(c["twin"] for c in by_name.values()) == len(pc.TWINS)
    # every other clip is its own source recording
    assert len({c["athlete"] for c in by_name.values()}) == len(by_name) - len(pc.TWINS)


def test_verdict():
    passing = {"expect": "pass", "reject_code": None}
    rejecting = {"expect": "reject", "reject_code": "multiple_people_subject_unstable"}
    assert pc.verdict(passing, {"status": "completed"})
    assert not pc.verdict(passing, {"status": "failed", "error_code": "low_detection_quality"})
    assert not pc.verdict(passing, {"status": "refused"})
    assert pc.verdict(rejecting, {"status": "failed", "error_code": "multiple_people_subject_unstable"})
    assert not pc.verdict(rejecting, {"status": "failed", "error_code": "low_detection_quality"})
    assert not pc.verdict(rejecting, {"status": "completed"})


def test_baseline_counts():
    feat = lambda n, a: {"sample_size": n, "athletes": a}  # noqa: E731
    assert pc.baseline_counts({"videos": 0, "features": []}) == (0, 0, True)
    assert pc.baseline_counts({"videos": 4, "features": [feat(4, 3), feat(2, 2)]}) == (4, 3, True)
    # no feature present in every video: the athlete figure is only a floor
    assert pc.baseline_counts({"videos": 4, "features": [feat(3, 3), feat(2, 2)]}) == (4, 3, False)


def _cls(movement, view, conf, agree_m=None, agree_v=None):
    return {"movement_type": movement, "camera_view": view, "confidence": conf,
            "agrees": {"movement_type": agree_m, "camera_view": agree_v}}


def test_auto_detect_outcome_is_judged_against_the_known_label():
    clip = {"name": "x.mp4", "movement": "running", "view": "sagittal"}
    assert pc.auto_outcome(clip, _cls("running", "sagittal", 0.9)) == "right"
    assert pc.auto_outcome(clip, _cls("squatting", "sagittal", 0.9)) == "WRONG"      # sure and wrong: the bad case
    assert pc.auto_outcome(clip, _cls("running", "sagittal", 0.69)) == "declined"    # under WARN_MIN_CONF: the user chooses
    assert pc.auto_outcome(clip, _cls("unknown", "sagittal", 0.9)) == "declined"
    assert pc.auto_outcome(clip, None) == "declined"


def test_classification_line_reads_the_backends_own_verdict():
    clip = {"name": "x.mp4", "movement": "squatting", "view": "sagittal"}
    line = pc.classification_line(clip, _cls("running", "sagittal", 0.95, agree_m=False, agree_v=True))
    assert "running/sagittal" in line and "DIFFERS" in line and "agrees" in line and line.rstrip().endswith("WRONG")
    assert "reprocess" in pc.classification_line(clip, None)
