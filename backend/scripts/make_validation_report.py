"""Regenerate docs/REAL_DATA_VALIDATION.md from the two JSON reports written by real_clip_validation.py.

    python scripts/make_validation_report.py docs/real-data   # reads report_production_floor.json + report_demo_floor8.json
"""
import json
import os
import sys

d = sys.argv[1] if len(sys.argv) > 1 else "docs/real-data"
P = json.load(open(os.path.join(d, "report_production_floor.json")))["items"]
D = {x["file"]: x for x in json.load(open(os.path.join(d, "report_demo_floor8.json")))["items"]}
manifest = json.load(open(os.path.join(d, "manifest.json")))


def pf(x):
    s = x.get("score")
    if s is None:
        return "—"
    if "insufficient_baseline" in s:
        b = s["insufficient_baseline"]["coverage"]["videos"]
        return f"202 — {b['have']}/{b['need']} videos"
    if "overall" in s:
        return f"{s['overall']:.1f} {s['category']}"
    return "cannot score (front/rear view)" if "NoValidated" in str(s) else str(s)[:30]


def df(x):
    s = D[x["file"]].get("score") or {}
    return f"{s['overall']:.1f} {s['category']}" if "overall" in s else "—"


rows = []
for x in P:
    pipe = x["status"] if x["status"] == "completed" else f"REFUSED `{x['error_code']}`"
    det = "—" if x["detection_rate"] is None else f"{x['detection_rate']*100:.0f}%"
    rows.append(f"| `{x['file'].split('__', 1)[1][:46]}` | {x['movement']} | {x['view']} | {pipe} | {det} | "
                f"{x['persons'] if x['persons'] is not None else '—'} | {'yes' if x['caveat'] else '—'} | "
                f"{x['quality_grade'] or '—'} | {pf(x)} | {df(x)} |")
n = len(P)
comp = sum(x["status"] == "completed" for x in P)
cav = [x["file"].split("__", 1)[1].replace(".mp4", "")[:40] for x in P if x["status"] == "completed" and x["caveat"]]
sp = sum(1 for x in P if x.get("score") and "overall" in x["score"])
sd = sum(1 for x in D.values() if (x.get("score") or {}).get("overall") is not None)
squat_have = sorted({x["score"]["insufficient_baseline"]["coverage"]["videos"]["have"]
                     for x in P if x.get("score") and "insufficient_baseline" in x["score"]})

md = f"""# Real-data validation

The merged engine run on **real footage**, end to end, with the real models (YOLOv8n-pose tracking, MediaPipe pose),
the real worker code path and the real risk engine. Nothing in this report is synthetic.

> **What this does and does not show.** It shows the pipeline runs on messy real video, refuses junk, and that the
> scoring engine behaves sensibly (and it exposed three real defects, all fixed). It does **not** show that the angles are
> accurate (no ground truth) or that any score predicts injury (no injury labels). See *Limits*.

## Corpus

{n} clips from public GitHub repositories, each capped at 45 s and downscaled to ≤1280 px so CPU pose estimation finishes.
**The clips are not in this repo**: licences are unknown and some are stock footage. `real-data/manifest.json` lists every file,
its labelled camera view and its source; `scripts/real_clip_validation.py` reproduces the run. Camera views were labelled by eye
from three frames per clip, not from file names (a file called `bodyweight_squat.mp4` is a clinic logo card and a coaching intro).

Deliberately **excluded** so the corpus stays honest: a second copy of `ErayBD squat_2` (in `MichistaLin/mediapipe-Fitness-counter`) and of
`imustitanveer squats` (in `ayazmhmd/pose-estimation-using-yolov8`) — same footage, would inflate the baseline; three 224×224 clips in
`aminuabdusalam/AI-FitnessTrainer/Archives/SmallFrameVideos` — **CGI avatars**, not people; front-facing and non-squat clips (walking, deadlift, push-up, lunge).

## Results — {comp} completed, {n - comp} refused by the quality gates

Production floors: **10 videos from ≥3 athletes**. "Demo floor" = 8 videos (athlete floor unchanged), shown only so real scores can be
inspected; it is not the product default. Every score here is **provisional** (fewer than 30 baseline videos).

| clip | movement | view | pipeline | athlete tracked | people seen | caveat | video quality | score @ production floor | score @ demo floor 8 |
|---|---|---|---|---|---|---|---|---|---|
""" + "\n".join(rows) + f"""

Scored at the production floor: **{sp}** · at the demo floor: **{sd}**.

## Findings

1. **The gates refuse junk.** All {n - comp} refused clips are unusable for athlete analysis (a lecture, a slide deck, a clinic intro with 7 people,
   a stock edit with cuts) except one: `squat_proper_form` looks like a single woman but was tracked in 66% of frames, just under the 70% floor
   — a second person registered somewhere. Not investigated; possible over-rejection.
2. **Multi-person clips complete but are caveated and kept out of baselines.** {len(cav)} completed clips carry a coverage caveat
   (`{'`, `'.join(cav)}`). They can still be scored but never feed the population.
3. **Defect 1 — occlusion drove a "high" score.** `jordanmargolis` (5 s, side-on) had its far leg visible in 13.5% of frames. Three left-leg angles
   from those few frames sat far outside the population and it scored **63.6 "high"**. Features from a leg below the 60% visibility floor are now
   excluded from the comparison (engine 2.1). Same clip: **0.0 "low"**.
4. **Defect 2 — the score depended on database row order.** Found when one test passed alone and failed in a full run. The baseline arrives from a
   `GROUP BY` with no `ORDER BY`; the forest and its cross-fit folds depend on row order, so a perfectly normal video could score 0 or 100 depending only on
   how Postgres returned the rows (2 of 8 simulated populations flipped). The engine now sorts the baseline canonically (engine 2.2); shuffling no longer changes anything.
5. **Defect 3 — small baselines are noisy, so scores are now labelled.** With the 10-video floor, ~10% of *perfectly normal* simulated videos score as strongly
   anomalous (~2% at 30 videos; 8 normal simulated videos at n=10 gave 2 deterministic false 100s). The response now carries `baseline.provisional` for fewer than 30
   baseline videos and the results page says so. **Recommendation: set `MIN_BASELINE_VIDEOS=30` for anything beyond a demo.**
6. **A moderate score here means "unlike this population", not "bad technique".** The barbell back squats (`itertius`, `Pradnya1208`) score moderate against a
   baseline that is mostly bodyweight/goblet squats. Squat variant and exact camera angle are not baseline dimensions.
7. **Only squatting has a baseline.** Running and jumping have no other usable videos. Front/rear views correctly return "cannot score": sagittal angles cannot be measured from the front.
8. **The squat baseline is one clip short of the production floor.** Clips inside the population see {', '.join(map(str, squat_have))} *other* usable videos against 10 needed, so most
   return HTTP 202 "baseline building" by design. One more clean, side-on, single-person squat from a new person closes it (and 20 more would make scores trustworthy).

## Limits (read before quoting any of this)

- **No ground truth.** "Completed" means it passed the gates and produced metrics, not that the angles are right.
- **No injury labels.** Scores flag movement that differs from a reference population; they do not estimate injury probability.
- **Clips are not athletes.** One athlete record per source (`ErayBD` = three clearly different women → three athletes; one couple clip = one athlete although two people). Athlete counts are a best guess.
- {n} clips, one movement with a usable baseline, mostly demo footage: enough to find bugs, not enough to claim accuracy.
"""
open(os.path.join(os.path.dirname(os.path.normpath(d)), "REAL_DATA_VALIDATION.md"), "w").write(md)
print("wrote REAL_DATA_VALIDATION.md:", n, "clips,", comp, "completed,", sp, "/", sd, "scored")
