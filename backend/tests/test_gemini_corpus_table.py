"""Offline tests for scripts/gemini_corpus_table.py: pure functions over report dicts, no API, no ffmpeg."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import gemini_corpus_table as ct  # noqa: E402


def report(source="a.mp4", view="sagittal", movement="back squat", valgus="not_assessable", quality="good",
           trunk="mild", asym="none", model="gemini-3.5-flash-lite", failed=False):
    analysis = None if failed else {
        "camera_view": view, "movement": movement, "reps_seen": 3, "joints": [],
        "knee_valgus": {"level": valgus, "note": "n"}, "trunk_lean": {"level": trunk, "note": "n"},
        "asymmetry": {"level": asym, "note": "n"}, "quality": quality, "limitations": [], "summary": "s"}
    return {"method": "gemini_video_observation", "confidence": "qualitative", "model": model, "source": source,
            "settings": {}, "chunks": [{"window": None, "analysis": analysis, "error": "x" if failed else None,
                                        "usage": None}], "overall": None, "disclaimer": "d"}


def test_catalog_labels_carry_the_corrected_views():
    """The handover called the landing clip frontal; the repo's own catalog says sagittal. Pin the truth."""
    labels = ct.catalog_labels()
    assert len(labels) >= 14
    assert labels["landing_single_leg_drop_soft_landing.mp4"] == {"movement": "landing", "view": "sagittal"}
    assert labels["cutting_aquabag_punch_cod.mp4"]["view"] == "frontal"


@pytest.mark.parametrize("label,said,expected", [
    ("squatting", "back squat", True), ("landing", "single-leg squat", False), ("jumping", "box jump", True),
    ("throwing", "shot put", True), ("cutting", "180 cut", True), ("running", "jogging", True),
    (None, "squat", None), ("squatting", "", None)])
def test_movement_match_is_lenient_but_not_blind(label, said, expected):
    assert ct.same_movement(label, said) is expected


@pytest.mark.parametrize("label,said,expected", [
    ("sagittal", "sagittal", True), ("sagittal", "oblique", False), ("frontal", "frontal", True),
    ("other", "oblique", True), ("other", "frontal", False), (None, "frontal", None)])
def test_view_match(label, said, expected):
    assert ct.same_view(label, said) is expected


def test_rule_breaks_and_misses_are_flagged():
    sag = ct.make_row(report(view="sagittal", valgus="mild"), {"movement": "squatting", "view": "sagittal"})
    assert sag["sagittal_but_judged_valgus"] is True and sag["frontal_but_not_judged"] is False
    front = ct.make_row(report(view="frontal", valgus="not_assessable"), {"movement": "squatting", "view": "frontal"})
    assert front["frontal_but_not_judged"] is True and front["sagittal_but_judged_valgus"] is False
    ok = ct.make_row(report(view="frontal", valgus="mild"), {"movement": "squatting", "view": "frontal"})
    assert not ok["frontal_but_not_judged"] and ok["movement_ok"] is True and ok["view_ok"] is True
    bad = ct.make_row(report(failed=True), None)
    assert bad["failed"] is True and "view" not in bad


def test_stability_counts_only_clips_run_more_than_once():
    same = [report("a.mp4"), report("a.mp4")]
    assert ct.stability(same) == {"a.mp4": 1.0}
    differ = [report("a.mp4", valgus="none"), report("a.mp4", valgus="marked")]
    assert ct.stability(differ) == {"a.mp4": 0.75}
    assert ct.stability([report("solo.mp4")]) == {}
    assert ct.stability([report("a.mp4"), report("a.mp4", failed=True)]) == {}, "a failed run cannot agree with anything"


def test_summary_numbers_and_rendering():
    labels = {"a.mp4": {"movement": "squatting", "view": "sagittal"}, "b.mp4": {"movement": "landing", "view": "sagittal"},
              "c.mp4": {"movement": "squatting", "view": "frontal"}}
    reports = [report("a.mp4"), report("a.mp4"),
               report("b.mp4", movement="single-leg squat", view="oblique"),
               report("c.mp4", view="frontal", valgus="not_assessable"), report("d.mp4", failed=True),
               report("e.mp4")]  # e has no label: it must not count in the agreement denominators
    rows = [ct.make_row(r, labels.get(r["source"])) for r in reports]
    s = ct.summarize(rows, ct.stability(reports))
    assert s["runs"] == 6 and s["failed_runs"] == 1
    assert s["movement_agrees"] == (3, 4) and s["view_agrees"] == (3, 4)
    assert s["frontal_but_not_judged"] == 1 and s["sagittal_but_judged_valgus"] == 0
    assert s["not_assessable"]["knee_valgus"] == 5 and s["stability_mean"] == 1.0 and s["clips_repeated"] == 1
    text = ct.render(rows, s)
    assert "| b.mp4 | landing/sagittal | single-leg squat (oblique) | NO | NO |" in text
    assert "| d.mp4 | no label | FAILED |" in text
    assert "movement agrees with the catalog (lenient word match): 3/4" in text
    assert "never against a physio" in text


def test_main_end_to_end(tmp_path, monkeypatch, capsys):
    out = tmp_path / "gemini_out"
    out.mkdir()
    for i, r in enumerate([report("a.mp4"), report("a.mp4", valgus="mild"), report("B.MP4", view="frontal", valgus="mild")]):
        (out / f"r{i}.json").write_text(json.dumps(r), encoding="utf-8")
    (out / "not_a_report.json").write_text(json.dumps({"hello": 1}), encoding="utf-8")
    (out / "broken.json").write_text("{nope", encoding="utf-8")
    labels = tmp_path / "labels.json"
    labels.write_text(json.dumps([{"file": "x/a.mp4", "movement": "squatting", "view": "sagittal"},
                                  {"file": "b.mp4", "movement": "squatting", "view": "frontal"}]), encoding="utf-8")
    pose = tmp_path / "pose.json"
    pose.write_text(json.dumps({"items": [{"file": "a.mp4", "quality_grade": "fair"},
                                          {"file": "runs/B.MP4", "quality_grade": "poor"}]}), encoding="utf-8")
    monkeypatch.setattr(ct, "catalog_labels", lambda: {})
    md = tmp_path / "table.md"
    assert ct.main([str(out), "--labels", str(labels), "--pose-report", str(pose), "--md", str(md)]) == 0
    text = capsys.readouterr().out
    assert "runs: 3 (failed: 0)" in text and "| a.mp4 | squatting/sagittal |" in text and "| fair |" in text
    assert "| B.MP4 | squatting/frontal |" in text and "| poor |" in text, "lookup ignores case and folders"
    assert "mean over 1 clips: 75%" in text
    assert md.read_text(encoding="utf-8").strip() == text.strip()


def test_main_rejects_missing_folder_and_empty_folder(tmp_path, capsys):
    assert ct.main([str(tmp_path / "nope")]) == 2
    (tmp_path / "empty").mkdir()
    assert ct.main([str(tmp_path / "empty")]) == 2
    assert "error:" in capsys.readouterr().err
