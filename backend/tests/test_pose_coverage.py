"""Pose coverage diagnostics (Defect 6): pure logic, no YOLO / MediaPipe / DB."""

import pytest

from app.modules.pose.coverage import (
    MIN_SUBJECT_HEIGHT_PX,
    assess_coverage,
    summarize_tracking,
)
from app.modules.pose.pipeline import should_skip_frame

H = 1080


def box(h: float, x: float = 100.0):
    return (x, 100.0, x + h * 0.4, 100.0 + h)


def tracking(*, frames=200, main_len=200, main_h=400.0, others=(), tracked=True, max_persons=None):
    """others: iterable of (n_frames, height_px) for the other tracks."""
    tracks = {1: {i: box(main_h) for i in range(main_len)}}
    for k, (n, h) in enumerate(others, start=2):
        tracks[k] = {i: box(h, x=500.0 + 50 * k) for i in range(n)}
    persons = max_persons if max_persons is not None else (1 + len(list(others)))
    return {
        "tracks": tracks if tracked else {}, "main_track_id": 1 if tracked else None, "frames_processed": frames,
        "max_persons": persons, "tracked": tracked, "frame_height": H, "frame_width": 1920,
        "person_counts": [persons] * frames,
    }


# ---- the outcomes ------------------------------------------------------------------------------

def test_clean_single_person_clip_is_ok_with_no_caveat():
    a = assess_coverage(summarize_tracking(tracking()), 0.92)
    assert (a.outcome, a.code, a.caveat) == ("ok", None, None)


def test_multi_person_clip_at_full_coverage_is_ok_but_says_which_track_was_analysed():
    s = summarize_tracking(tracking(others=[(190, 380), (180, 390)]))
    a = assess_coverage(s, 0.9)
    assert a.outcome == "ok" and a.caveat
    assert "3 tracked" in a.caveat and "track 1" in a.caveat and "annotated video" in a.caveat


def test_wide_shot_group_clip_at_49pct_is_rejected_as_subject_too_small_and_names_the_tracks():
    """The real failure: a wide group HIIT clip, 49% detection. The message must say WHY."""
    s = summarize_tracking(tracking(main_len=190, main_h=120.0, others=[(180, 110), (170, 115), (150, 100)]))
    a = assess_coverage(s, 0.49)
    assert a.outcome == "reject" and a.code == "subject_too_small"
    assert "~120 px tall" in a.message and f"{MIN_SUBJECT_HEIGHT_PX} px" in a.message
    assert "4 people were tracked" in a.message and "track 1" in a.message
    assert "zoom" in a.message or "closer" in a.message


def test_unstable_selection_among_several_people_is_distinguished_from_a_small_subject():
    # Subject is large, but only followed in 50% of frames while others cross over / ID-switch.
    s = summarize_tracking(tracking(main_len=100, main_h=420.0, others=[(180, 410), (120, 400)]))
    a = assess_coverage(s, 0.49)
    assert a.outcome == "reject" and a.code == "multiple_people_subject_unstable"
    assert "3 people were tracked" in a.message and "50% of frames" in a.message
    assert "do not substitute another person" in a.message


def test_pose_failure_on_a_large_tracked_single_subject_is_the_generic_quality_error():
    a = assess_coverage(summarize_tracking(tracking(main_h=420.0)), 0.30)
    assert a.outcome == "reject" and a.code == "low_detection_quality"
    assert "lighting" in a.message and "40%" in a.message


def test_partial_coverage_is_accepted_with_an_explicit_caveat_not_silently():
    a = assess_coverage(summarize_tracking(tracking(main_h=420.0)), 0.55)
    assert a.outcome == "partial" and a.code == "partial_coverage" and a.message is None
    assert "55%" in a.caveat and "lower confidence" in a.caveat


def test_partial_coverage_with_other_people_also_names_the_selected_track():
    a = assess_coverage(summarize_tracking(tracking(main_h=420.0, others=[(190, 400)])), 0.6)
    assert a.outcome == "partial" and "track 1" in a.caveat


@pytest.mark.parametrize("rate,expected", [(0.70, "ok"), (0.699, "partial"), (0.40, "partial"), (0.399, "reject")])
def test_floors_are_unchanged_and_exact(rate, expected):
    assert assess_coverage(summarize_tracking(tracking(main_h=420.0)), rate).outcome == expected


def test_a_two_frame_false_positive_is_not_a_second_person():
    s = summarize_tracking(tracking(others=[(2, 300)]))
    assert s.tracks_seen == 2 and s.substantive_tracks == 1 and not s.multi_person
    assert assess_coverage(s, 0.9).caveat is None


def test_untracked_multi_person_footage_cannot_be_attributed_and_is_rejected_below_the_floor():
    s = summarize_tracking(tracking(tracked=False, max_persons=5))
    a = assess_coverage(s, 0.55)
    assert a.outcome == "reject" and a.code == "multiple_people_subject_unstable"
    assert "identity tracking was unavailable" in a.message


def test_untracked_single_person_footage_still_gets_partial_credit():
    assert assess_coverage(summarize_tracking(tracking(tracked=False, max_persons=1)), 0.55).outcome == "partial"


def test_failure_codes_fit_the_error_code_column():
    for s, rate in [(tracking(main_h=100.0), 0.3), (tracking(main_len=90, others=[(180, 400)]), 0.3), (tracking(main_h=400.0), 0.1)]:
        a = assess_coverage(summarize_tracking(s), rate)
        assert a.outcome == "reject" and len(a.code) <= 50


# ---- identity safety: never measure someone else ------------------------------------------------

@pytest.mark.parametrize("box_,subject_boxes,fallback,skip", [
    (None, {0: None}, False, True),     # multi-person, athlete untracked on this frame -> do NOT pose the frame
    (None, {0: None}, True, False),     # single-person: full-frame fallback is safe
    (box(300), {0: box(300)}, False, False),   # athlete tracked -> crop and measure
    (None, None, False, False),         # tracking unavailable -> legacy full-frame behaviour
])
def test_should_skip_frame(box_, subject_boxes, fallback, skip):
    assert should_skip_frame(box_, subject_boxes, fallback) is skip


# ---- stride (slow-motion clips) x coverage gate ----------------------------------------------

def test_slow_motion_stride_does_not_deflate_main_track_coverage():
    """REGRESSION (found while merging the stride logic into the coverage gate). `frames_processed` counts
    frames READ, but at stride 4 (240 fps) the tracker only analyses every 4th frame. Dividing the athlete's
    track by frames READ made a perfectly tracked clip look 25% covered — under the 70% floor, so it was
    REJECTED as unreliable."""
    stride, read = 4, 800
    analysed = read // stride                                    # 200 frames actually analysed
    t = {
        "person_counts": [1] * analysed,
        "tracks": {1: {i: box(400.0) for i in range(analysed)}},  # athlete present in EVERY analysed frame
        "main_track_id": 1, "max_persons": 1, "tracked": True,
        "frames_processed": read, "frame_width": 1080, "frame_height": H,
    }
    s = summarize_tracking(t)
    assert s.main_track_coverage == pytest.approx(1.0)
    assert assess_coverage(s, detection_rate=0.95).outcome == "ok"
