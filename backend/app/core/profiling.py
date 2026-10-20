"""Lightweight stage profiling for the video-processing pipeline.

Why
---
"Make the analysis faster" is only actionable once we know where the time
actually goes. Eyeballing the pipeline suggests plausible culprits (YOLO
detection, MediaPipe pose, JPEG preview encoding, the annotated-video writer),
but guesses are not evidence - and an optimization that targets the wrong stage
wastes effort and can regress quality.

This module provides a minimal, dependency-free timer that:

* groups work into named **stages** (``detect``, ``pose``, ``render``, ...);
* accumulates total time and call count per stage;
* is a **no-op when disabled**, so it can stay in the hot loop permanently
  without measurably changing the thing it measures.

Design notes
------------
* ``perf_counter`` is used (monotonic, high resolution).
* ``profile`` is a context manager, so it reads cleanly around a block and
  releases on exception (a failed stage still shows up in the report).
* Enabled state is a plain module-level flag set from settings at run start,
  rather than threading a profiler object through every helper method. That
  keeps the instrumentation to a few lines per stage.
* The report is deliberately human-readable *and* machine-readable, so it can
  be logged for a developer and also returned through the API for tooling.

Cost when disabled: one attribute lookup (``if _enabled``) per stage boundary -
unmeasurable next to a YOLO or MediaPipe inference.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Dict, List, Optional

# Stage name -> accumulated seconds
_totals: Dict[str, float] = {}
# Stage name -> number of completed invocations
_counts: Dict[str, int] = {}
# Insertion order, so the report reads in pipeline order, not by cost.
_order: List[str] = []
_enabled = False

# Stages that are *nested* inside longer stages. Reporting wall-clock totals for
# both a parent and its children would double count, so the report separates
# them and makes the relationship explicit.
NESTED_STAGES = {"preview_write", "hud", "progress_update", "partial_risk"}


def set_enabled(enabled: bool) -> None:
    """Turn profiling on/off. Called once per run from the pipeline."""
    global _enabled
    _enabled = bool(enabled)


def is_enabled() -> bool:
    return _enabled


def reset() -> None:
    """Clear accumulated timings. Called at the start of each run."""
    _totals.clear()
    _counts.clear()
    _order.clear()


def record(stage: str, seconds: float, calls: int = 1) -> None:
    """Attribute a manually measured duration to ``stage``.

    For spans that are awkward to wrap in a context manager (e.g. an entire
    loop that would otherwise need reindenting). No-op when disabled.
    """
    if not _enabled:
        return
    if stage not in _totals:
        _totals[stage] = 0.0
        _counts[stage] = 0
        _order.append(stage)
    _totals[stage] += max(0.0, seconds)
    _counts[stage] += calls


@contextmanager
def profile(stage: str):
    """Time a block, attributing it to ``stage``.

    When profiling is disabled this is a bare ``yield`` with no clock reads.
    """
    if not _enabled:
        yield
        return
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        if stage not in _totals:
            _totals[stage] = 0.0
            _counts[stage] = 0
            _order.append(stage)
        _totals[stage] += elapsed
        _counts[stage] += 1


def report() -> Dict[str, object]:
    """Return the accumulated timings as a serializable dict.

    ``stages`` is ordered by pipeline appearance. ``total_measured_seconds``
    sums only the top-level stages (nested ones are already included in their
    parent), giving an honest picture of attributed time.
    """
    stages = [
        {
            "stage": name,
            "seconds": round(_totals[name], 4),
            "calls": _counts[name],
            "mean_ms": round((_totals[name] / _counts[name]) * 1000, 3)
            if _counts[name]
            else 0.0,
            "nested": name in NESTED_STAGES,
        }
        for name in _order
    ]
    top_level = [s for s in stages if not s["nested"]]
    total = sum(s["seconds"] for s in top_level)
    # Share of top-level measured time, so the dominant stage is obvious.
    for s in stages:
        s["share_pct"] = (
            round(100.0 * s["seconds"] / total, 1) if total and not s["nested"] else None
        )
    stages.sort(key=lambda s: s["seconds"], reverse=True)
    return {
        "total_measured_seconds": round(total, 4),
        "stages": stages,
        "bottleneck": stages[0]["stage"] if stages else None,
    }


def format_report(report_dict: Optional[Dict[str, object]] = None) -> str:
    """Render a report as a small aligned table for logs/stdout."""
    data = report_dict if report_dict is not None else report()
    stages = data.get("stages", [])
    if not stages:
        return "processing profile: no timings recorded (profiling disabled?)"
    lines = [
        "processing profile - total measured "
        f"{data.get('total_measured_seconds', 0.0):.3f}s",
        f"  {'stage':<18}{'seconds':>10}{'calls':>8}{'mean ms':>10}  share",
    ]
    for s in stages:
        share = "-" if s["share_pct"] is None else f"{s['share_pct']:>5.1f}%"
        flag = "  (nested)" if s["nested"] else ""
        lines.append(
            f"  {s['stage']:<18}{s['seconds']:>10.3f}{s['calls']:>8}"
            f"{s['mean_ms']:>10.2f}  {share}{flag}"
        )
    return "\n".join(lines)
