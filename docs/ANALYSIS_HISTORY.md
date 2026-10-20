# Athlete Analysis History & Baseline Comparison

This document describes how every analysed video is recorded as durable history
for an athlete, and how each new analysis is automatically **cross-checked
against that athlete's own past**.

## The problem this solves

Before this feature:

* Videos were already linked to an athlete (`videos.athlete_id`), but analyses
  were only reachable *transitively* via
  `videos → pose_analyses → biomechanical_analyses`.
* The injury-risk score was **never stored**. `GET /api/v1/risk/{video_id}`
  recomputed it from raw keypoints on every single request. With nothing
  persisted, there was no stable number to trend and nothing to compare against.
* No endpoint or UI presented an athlete's analyses as a timeline at all — the
  athlete profile literally displayed "Coming in Milestone 2/3" placeholders.

## What was added

* **`analysis_snapshots` table** — one durable row per completed analysis,
  holding the risk result, the trended metrics, and the comparison that was
  recorded against the athlete's rolling baseline.
* **`app/services/baseline_service.py`** — metric extraction, snapshot
  recording, baseline computation, and the comparison engine.
* **`GET /api/v1/athletes/{athlete_id}/history`** — the athlete's timeline.
* **`GET /api/v1/videos/{video_id}/comparison`** — one analysis vs. its baseline.
* **Snapshot recording wired into processing** — written automatically when an
  analysis completes.
* **Frontend** — an `Analysis History` timeline on the athlete profile, and a
  `Comparison with History` panel on the video analysis page.

## Data model

`analysis_snapshots` (`backend/app/models/analysis_snapshot.py`):

| Column | Meaning |
| --- | --- |
| `athlete_id` | FK to `athletes.id`. Denormalized (also reachable via `video_id`) so timeline reads are one indexed query. |
| `video_id` | FK to `videos.id`, **unique** — one snapshot per video. |
| `pose_analysis_id` | FK to `pose_analyses.id` (provenance). |
| `activity_type` | Denormalized, because comparisons are only valid within one activity. |
| `sequence_index` | 1-based position in the athlete+activity timeline. |
| `performed_at` | Video creation time (the session date); what history is sorted by. |
| `overall_risk_score`, `risk_level`, `findings_count` | Headline risk result. |
| `metrics` | Trended numbers (`{"risk_score": 42.0, "movement_quality": 78.5, ...}`). |
| `baseline_comparison` | The comparison result, frozen at completion time. |

Full-fidelity pose and biomechanical data stays in `pose_analyses` /
`biomechanical_analyses`; a snapshot only stores what is worth trending.

## Comparison design

### Baseline = rolling average of prior same-activity analyses

The baseline is the mean of the athlete's **most recent `BASELINE_WINDOW` (5)
prior analyses of the same activity type**.

* **Excludes the current analysis.** An analysis never contributes to the
  baseline it is measured against, so the comparison answers the only question
  that matters: *"how does today compare with what came before?"*
* **Scoped by activity.** A squat is only ever compared with squats. Squats and
  sprints use different joints, phase segmentation, and metric ranges; pooling
  them would emit false alarms.
* **Minimum sample.** A baseline needs at least `MIN_BASELINE` (2) prior
  analyses. Until then the status is `insufficient_history`, and the very first
  analysis reports `no_history` — it *establishes* the baseline.

### The comparison is recorded, not recomputed

`baseline_comparison` is stored when the analysis completes. This is
deliberate: it is a historical fact. If it were recomputed on read, a rolling
baseline would be rewritten every time the athlete uploaded another video, and
"how did this session compare at the time?" would silently change.

### Guard rails against noise

A raw delta is meaningless without context: 5° of knee asymmetry is alarming for
a very stable athlete and unremarkable for a naturally variable one. So each
delta is normalized:

```
z = (current - baseline_mean) / spread
```

where `spread` is the baseline's **mean absolute deviation** (robust to
outliers). When an athlete's history is almost perfectly flat the MAD approaches
zero, which would make any delta look infinite — so a **noise floor** of
`max(5% of the mean, 0.5)` is applied.

* `|z| >= 1.0` → worth mentioning (`notable`)
* `|z| >= 2.0` → a real change, flagged as improvement/deterioration

The result: stable athletes get sensitive detection, noisy athletes don't get
false alarms.

### Direction semantics

Each metric declares which way is *worse*:

| Metric | Worse direction |
| --- | --- |
| `risk_score`, `findings_count`, `knee_asymmetry`, `trunk_lean_max` | higher |
| `movement_quality`, `symmetry_score`, `mean_pose_confidence` | lower |
| `knee_rom_*`, `hip_rom_*` | **no direction** (informational) |

ROM is reported as a delta but never as a verdict — a range of motion can
legitimately go either way depending on the athlete's training phase, so the
system must not claim it is "better" or "worse".

## Endpoints

### `GET /api/v1/athletes/{athlete_id}/history`

Chronological (oldest → newest) timeline plus per-activity trends.

Query parameters: `activity` (optional filter), `limit` (default 100, max 500).

```json
{
  "athlete_id": 1,
  "athlete_public_id": "ATH000001",
  "total_analyses": 4,
  "trends": [
    {
      "activity_type": "squat",
      "analysis_count": 4,
      "first_risk_score": 10.0,
      "latest_risk_score": 45.0,
      "mean_risk_score": 26.75,
      "risk_change": 35.0,
      "direction": "worsening",
      "latest_performed_at": "..."
    }
  ],
  "entries": [ /* HistoryEntry, oldest first */ ]
}
```

`trends.direction` compares the **first** score with the **latest**, with a ±10%
relative dead band for `stable`.

### `GET /api/v1/videos/{video_id}/comparison`

Returns the recorded `BaselineComparison` for one analysis. `404` if the video
has no completed analysis yet.

```json
{
  "status": "changed",
  "baseline_size": 4,
  "baseline_window": 5,
  "summary": "Change versus baseline - elevated: injury risk score.",
  "deltas": [
    {
      "metric": "risk_score",
      "label": "Injury risk score",
      "current": 65.0,
      "baseline": 20.1,
      "delta": 44.9,
      "percent_change": 223.4,
      "z_score": 44.7,
      "verdict": "deterioration",
      "notable": true,
      "baseline_range": [19.0, 21.0]
    }
  ],
  "flags": [ /* biggest movers only */ ],
  "deteriorations": ["risk_score"],
  "improvements": []
}
```

`status` is one of `no_history`, `insufficient_history`, `stable`, `changed`.

## Access control

Both endpoints enforce the existing athlete-access rules:

* Athletes may read **only their own** history (`403` otherwise) — reusing
  `VideoService.check_athlete_access` so IDOR logic lives in one place.
* Coaches, physiotherapists, sports scientists, and administrators may read any
  athlete's history.
* Unauthenticated requests get `401`.
* The comparison endpoint reuses `VideoService.get_video`, so the same
  object-level checks apply.

## Processing integration

`VideoProcessingService.process_video` calls
`baseline_service.record_snapshot(...)` right after the final risk assessment.

* **Idempotent** — a snapshot already exists for the video, it is returned
  untouched. Reprocessing cannot create duplicates or rewrite a recorded
  comparison.
* **Best-effort** — wrapped in `try/except` with a warning log. A history
  failure must never fail the analysis the user is waiting on.
* **Reads the baseline before inserting**, so the new analysis cannot be part of
  its own baseline.

## Migration

`c1a2b3d4e5f6_add_analysis_snapshots_history_table` (down_revision
`b7d4c1e9a2f3`). Purely additive — creates one new table and its indexes; no
existing table is touched, so it is safe on a populated database. Downgrade
drops the table.

## Notes and limitations

* **Existing analyses have no snapshot.** Videos processed before this feature
  will not appear in history, because their risk was never persisted. Re-running
  processing would create one, but `POST /process` refuses to reprocess a
  completed video by design.
* **Trends are per activity.** There is deliberately no single cross-activity
  "overall risk", since that would mix incomparable measurements.
* **`performed_at` uses the video's upload time**, which is the best available
  proxy for the session date.
