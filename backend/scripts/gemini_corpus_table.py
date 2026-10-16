"""Tabulate gemini_video.py reports against the repo's own clip labels. No API calls, no network, no app imports.

Run the clips first (PowerShell), twice each so stability can be measured, WITHOUT --movement (a hint would bias the
movement check) and with ONE pinned model (otherwise the table compares models, not clips):

    $m = "gemini-3.5-flash-lite"
    foreach ($f in Get-ChildItem data\\*.mp4, test-assets\\sample-clips\\*, test-assets\\internet-clips\\*) {
        1..2 | ForEach-Object { python backend/scripts/gemini_video.py $f.FullName --model $m --out "gemini_out\\$($f.BaseName).run$_.json" } }

then:

    python backend/scripts/gemini_corpus_table.py [gemini_out] [--labels more.json] [--pose-report report.json] [--md out.md]

Labels come from verify_data_videos.EXPECTED_CATALOG + verify_test_assets.TEST_ASSETS (the repo's 14 clips) plus any
--labels JSON ([{"file", "movement", "view"}]). --pose-report takes a docs/real-data/report_*.json-style file and shows
the pose pipeline's quality grade beside Gemini's. Each report is read at its first analysed window (run the corpus
without --chunk-seconds). What this measures: label agreement, whether the view rules held,
how often a flag is "not_assessable", and whether repeat runs agree. It does not measure whether a valgus call is
right: that needs a physio's labels.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

# label movement -> words that count as "the model said the same thing" (lenient on purpose; both strings are shown)
ALIASES = {"squatting": ("squat",), "landing": ("land", "drop"), "running": ("run", "jog"), "sprinting": ("sprint",),
           "jumping": ("jump", "hop"), "throwing": ("throw", "shot put", "javelin", "discus"),
           "cutting": ("cut", "change of direction", "side step", "sidestep")}
FLAGS = ("knee_valgus", "trunk_lean", "asymmetry")


def load_reports(folder) -> list[dict]:
    out = []
    for p in sorted(Path(folder).glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if isinstance(d, dict) and d.get("method") == "gemini_video_observation":
            out.append(d)
    return out


def catalog_labels() -> dict[str, dict]:
    here = Path(__file__).resolve().parent
    sys.path[:0] = [str(here), str(here.parent)]
    import verify_data_videos as dv  # noqa: E402 - the repo's own catalogs; imported lazily so tests can avoid them
    import verify_test_assets as ta  # noqa: E402
    return {Path(x["file"]).name.lower(): {"movement": x["movement"], "view": x["view"]}
            for x in list(dv.EXPECTED_CATALOG) + list(ta.TEST_ASSETS)}


def json_labels(path) -> dict[str, dict]:
    return {Path(x["file"]).name.lower(): {"movement": x["movement"], "view": x["view"]}
            for x in json.loads(Path(path).read_text(encoding="utf-8"))}


def pose_grades(path) -> dict[str, str]:
    items = json.loads(Path(path).read_text(encoding="utf-8")).get("items", [])
    return {Path(i["file"]).name.lower(): str(i.get("quality_grade")) for i in items if i.get("file")}


def same_movement(label: str | None, said: str | None) -> bool | None:
    if not label or not said:
        return None
    return any(w in said.lower() for w in ALIASES.get(label, (label[:4],)))


def same_view(label: str | None, said: str | None) -> bool | None:
    if not label or not said:
        return None
    return said in ("oblique", "unclear") if label == "other" else said == label


def first_ok(rep: dict) -> dict | None:
    return next((c["analysis"] for c in rep["chunks"] if c.get("analysis")), None)


def make_row(rep: dict, label: dict | None, grade: str | None = None) -> dict:
    a = first_ok(rep)
    row = {"clip": rep["source"], "model": rep.get("model"), "label": label, "pose_grade": grade, "failed": a is None}
    if a:
        valgus = a["knee_valgus"]["level"]
        row |= {"movement": a["movement"], "view": a["camera_view"], "quality": a["quality"], "valgus": valgus,
                "trunk_lean": a["trunk_lean"]["level"], "asymmetry": a["asymmetry"]["level"],
                "movement_ok": same_movement(label and label["movement"], a["movement"]),
                "view_ok": same_view(label and label["view"], a["camera_view"]),
                "sagittal_but_judged_valgus": a["camera_view"] == "sagittal" and valgus != "not_assessable",
                "frontal_but_not_judged": bool(label) and label["view"] == "frontal" and valgus == "not_assessable"}
    return row


def stability(reports: list[dict]) -> dict[str, float]:
    """Per clip with 2+ runs: share of (quality, valgus, trunk_lean, asymmetry) that every run agrees on."""
    by_clip: dict[str, list[dict]] = {}
    for r in reports:
        if (a := first_ok(r)):
            by_clip.setdefault(r["source"], []).append(a)
    out = {}
    for clip, runs in by_clip.items():
        if len(runs) < 2:
            continue
        vals = [[x["quality"], x["knee_valgus"]["level"], x["trunk_lean"]["level"], x["asymmetry"]["level"]]
                for x in runs]
        out[clip] = sum(len({v[i] for v in vals}) == 1 for i in range(4)) / 4
    return out


def summarize(rows: list[dict], stab: dict[str, float]) -> dict:
    ok = [r for r in rows if not r["failed"]]
    count = lambda key: (sum(1 for r in ok if r.get(key) is True), sum(1 for r in ok if r.get(key) is not None))  # noqa: E731
    return {"runs": len(rows), "failed_runs": len(rows) - len(ok),
            "movement_agrees": count("movement_ok"), "view_agrees": count("view_ok"),
            "sagittal_but_judged_valgus": sum(1 for r in ok if r["sagittal_but_judged_valgus"]),
            "frontal_but_not_judged": sum(1 for r in ok if r["frontal_but_not_judged"]),
            "not_assessable": {k: sum(1 for r in ok if r[{"knee_valgus": "valgus"}.get(k, k)] == "not_assessable")
                               for k in FLAGS},
            "models": dict(Counter(r["model"] for r in ok)),
            "stability_mean": (sum(stab.values()) / len(stab)) if stab else None, "clips_repeated": len(stab)}


def render(rows: list[dict], s: dict) -> str:
    def lab(r):
        return f"{r['label']['movement']}/{r['label']['view']}" if r["label"] else "no label"

    def mark(v):
        return {True: "yes", False: "NO", None: "-"}[v]
    lines = ["| clip | label | gemini says | move | view | quality | valgus | trunk | asym | pose | model |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if r["failed"]:
            lines.append(f"| {r['clip']} | {lab(r)} | FAILED | | | | | | | {r['pose_grade'] or ''} | |")
            continue
        lines.append(f"| {r['clip']} | {lab(r)} | {r['movement']} ({r['view']}) | {mark(r['movement_ok'])} | "
                     f"{mark(r['view_ok'])} | {r['quality']} | {r['valgus']} | {r['trunk_lean']} | {r['asymmetry']} | "
                     f"{r['pose_grade'] or ''} | {r['model']} |")
    m, v = s["movement_agrees"], s["view_agrees"]
    na = s["not_assessable"]
    lines += ["", f"runs: {s['runs']} (failed: {s['failed_runs']})",
              f"movement agrees with the catalog (lenient word match): {m[0]}/{m[1]}",
              f"camera view agrees with the catalog: {v[0]}/{v[1]}",
              f"RULE BROKEN, valgus judged from a view the model itself called sagittal: {s['sagittal_but_judged_valgus']}",
              f"frontal clips where valgus was not judged: {s['frontal_but_not_judged']}",
              f"not_assessable counts: valgus {na['knee_valgus']}, trunk_lean {na['trunk_lean']}, "
              f"asymmetry {na['asymmetry']}",
              f"models used: {s['models']}"]
    if s["stability_mean"] is not None:
        lines.append(f"repeat-run agreement on quality+3 flags, mean over {s['clips_repeated']} clips: "
                     f"{s['stability_mean']:.0%}")
    else:
        lines.append("repeat-run agreement: not measured (run each clip at least twice)")
    lines.append("\nThese are an AI model's visual opinions, checked only against clip labels, never against a physio.")
    return "\n".join(lines)


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("folder", nargs="?", default="gemini_out")
    ap.add_argument("--labels", action="append", default=[], help="extra labels JSON (repeatable)")
    ap.add_argument("--pose-report", help="report_*.json-style file with items[].file / quality_grade")
    ap.add_argument("--md", help="also write the table to this file")
    a = ap.parse_args(argv)
    if not Path(a.folder).is_dir():
        print(f"error: no such folder: {a.folder}", file=sys.stderr)
        return 2
    reports = load_reports(a.folder)
    if not reports:
        print(f"error: no gemini_video.py reports in {a.folder}", file=sys.stderr)
        return 2
    try:
        labels = catalog_labels()
    except ImportError as e:
        print(f"warning: repo catalogs not importable ({e}); only --labels files are used", file=sys.stderr)
        labels = {}
    for p in a.labels:
        labels |= json_labels(p)
    grades = pose_grades(a.pose_report) if a.pose_report else {}
    rows = [make_row(r, labels.get(r["source"].lower()), grades.get(r["source"].lower())) for r in reports]
    text = render(rows, summarize(rows, stability(reports)))
    print(text)
    if a.md:
        Path(a.md).write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
