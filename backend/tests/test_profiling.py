"""Tests for the pipeline stage profiler.

The profiler's contract when disabled is as important as when enabled: it must
add no measurable work to the hot loop, which means it must not even read the
clock. These tests cover both modes.
"""

import time

from app.core import profiling


def setup_function(_):
    profiling.set_enabled(False)
    profiling.reset()


def teardown_function(_):
    profiling.set_enabled(False)
    profiling.reset()


# --------------------------------------------------------------------------- #
# Disabled mode
# --------------------------------------------------------------------------- #

def test_disabled_records_nothing():
    profiling.set_enabled(False)
    with profiling.profile("detect"):
        time.sleep(0.005)
    assert profiling.report()["stages"] == []


def test_disabled_record_helper_is_noop():
    profiling.set_enabled(False)
    profiling.record("detect", 1.23)
    assert profiling.report()["stages"] == []


def test_toggle_roundtrip():
    profiling.set_enabled(True)
    assert profiling.is_enabled() is True
    profiling.set_enabled(False)
    assert profiling.is_enabled() is False


# --------------------------------------------------------------------------- #
# Enabled mode
# --------------------------------------------------------------------------- #

def test_accumulates_total_and_calls():
    profiling.set_enabled(True)
    for _ in range(3):
        with profiling.profile("pose"):
            time.sleep(0.002)

    report = profiling.report()
    pose = next(s for s in report["stages"] if s["stage"] == "pose")
    assert pose["calls"] == 3
    assert pose["seconds"] > 0
    assert pose["mean_ms"] > 0


def test_stages_are_sorted_by_cost():
    profiling.set_enabled(True)
    with profiling.profile("cheap"):
        time.sleep(0.001)
    with profiling.profile("expensive"):
        time.sleep(0.01)

    stages = [s["stage"] for s in profiling.report()["stages"]]
    assert stages[0] == "expensive"
    assert profiling.report()["bottleneck"] == "expensive"


def test_exception_still_records_the_stage():
    """A stage that raises must not lose its timing."""
    profiling.set_enabled(True)
    try:
        with profiling.profile("broken"):
            raise ValueError("boom")
    except ValueError:
        pass
    assert any(s["stage"] == "broken" for s in profiling.report()["stages"])


def test_nested_stages_excluded_from_total():
    """Nested spans are already inside their parent; counting both double counts."""
    profiling.set_enabled(True)
    with profiling.profile("render"):
        with profiling.profile("hud"):
            time.sleep(0.002)

    report = profiling.report()
    hud = next(s for s in report["stages"] if s["stage"] == "hud")
    assert hud["nested"] is True
    # Total is the top-level render only, not render + hud.
    render = next(s for s in report["stages"] if s["stage"] == "render")
    assert report["total_measured_seconds"] == render["seconds"]


def test_share_percentages_only_on_top_level():
    profiling.set_enabled(True)
    with profiling.profile("a"):
        time.sleep(0.002)
    with profiling.profile("preview_write"):
        time.sleep(0.001)

    report = profiling.report()
    shares = {s["stage"]: s["share_pct"] for s in report["stages"]}
    assert shares["a"] is not None
    assert shares["preview_write"] is None


def test_reset_clears_previous_run():
    profiling.set_enabled(True)
    with profiling.profile("detect"):
        time.sleep(0.001)
    profiling.reset()
    assert profiling.report()["stages"] == []


def test_record_helper_uses_calls_argument():
    profiling.set_enabled(True)
    profiling.record("frame_loop", 0.5, calls=10)
    stage = profiling.report()["stages"][0]
    assert stage["calls"] == 10
    assert stage["seconds"] == 0.5


def test_record_helper_ignores_negative():
    profiling.set_enabled(True)
    profiling.record("weird", -5.0)
    assert profiling.report()["stages"][0]["seconds"] == 0.0


def test_format_report_is_readable():
    profiling.set_enabled(True)
    with profiling.profile("pose"):
        time.sleep(0.001)
    text = profiling.format_report()
    assert "pose" in text
    assert "processing profile" in text
    assert "share" in text


def test_format_report_empty_is_safe():
    profiling.set_enabled(False)
    assert "no timings recorded" in profiling.format_report()
