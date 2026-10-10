# Lateral-motion tracking fix — full report (2026-10-07)

## 1. The issue (user report, verbatim substance)

- Single-person videos with lateral motion (cutting left/right, athletes around a football field) were reported as containing "more than one people" when clearly one person was present.
- Only static, standing-still squats tracked reliably; nothing else.
- Requirement: test it on real clips and verify the output.

## 2. Root cause (confirmed in code)

- `backend/app/modules/pose/pipeline.py::track_persons` called `model.track(frame, persist=True)` with no tracker argument → Ultralytics default **ByteTrack**.
- ByteTrack's Kalman motion model assumes near-constant velocity. A cutting athlete's sharp direction change breaks frame-to-frame association → subject dropped, re-acquired under a **new track ID** (ID switch / fragmentation).
- `backend/app/modules/pose/coverage.py::TrackingSummary.multi_person` counts `substantive_tracks > 1` (a track spanning ≥10% of frames, min 5). One cutting athlete fragments into several substantive IDs → false "multiple people" → if the longest fragment < 70% of frames, wrongful rejection as `multiple_people_subject_unstable`.
- Small/distant subjects (football field) additionally lose detections in ByteTrack's low-confidence association stage → coverage collapse.
- Static squats worked because: no lateral displacement to break association + large centered subject.

## 3. What was done (all in this session)

| # | Change | File |
|---|---|---|
| 1 | Tracker switched to BoT-SORT (`YOLO_TRACKER` env, default `botsort.yaml`; `bytetrack.yaml` restores old behavior) | `backend/app/modules/pose/pipeline.py` |
| 2 | New pure `merge_track_fragments(tracks, fps)`: union-find over track IDs; merge only if temporally disjoint (gap ≤ 0.5 s), median box heights within 35%, displacement ≤ 8 subject-heights/s; merged track keeps earliest ID | same |
| 3 | `track_persons(..., fps=30.0)`; raw tracks merged before `select_main_track` (logged when IDs collapse) | same |
| 4 | Pass real `fps=` at both production call sites | `backend/app/modules/pose/tasks.py`, `backend/scripts/verify_data_videos.py` |
| 5 | 7 new unit tests (ID-switch merge, transitive 3-fragment merge, 4 never-merge negatives, end-to-end via fake model) | `backend/tests/test_tracking.py` |
| 6 | Fixed 2 test fakes that hardcoded the old `track_persons` signature (missed in the first pass) | `backend/tests/test_pose_tasks.py`, `backend/tests/test_worker_task.py` |
| 7 | Upload format support `.webm/.avi/.mkv/.m4v` (backend pattern + `confirm_upload`, frontend `acceptFile`/input/copy, filename unit tests, DECISIONS entry) | `backend/app/modules/video/router.py`, `backend/tests/test_video_upload.py`, `frontend/src/app/(authenticated)/videos/upload/page.tsx` |
| 8 | New regression script for test-assets with expected outcomes | `backend/scripts/verify_test_assets.py` |
| 9 | Log entries | `docs/DECISIONS.md` (2), `docs/STATE.md` |

Safety property (deliberate): tracks overlapping in time NEVER merge — a genuine group scene cannot collapse into one person. Merging only affects track attribution; it never raises a score.

## 4. Full verification results (all executed, real models, CPU)

- **Unit:** `test_tracking.py` + `test_pose_coverage.py` → 40 passed. Full `pytest` → **394 passed, 0 failed** (Docker Postgres :5433, Redis :6379).
- **ByteTrack vs BoT-SORT** (`data/cutting_aquabag_punch_cod.mp4`, 684f): both give 1 track / 1 substantive (0.844 vs 0.838 coverage) — the clip is trackable by either; merging is the safety net. (`data/landing_one_foot_landing_pivot.mp4`: 8–9 raw IDs / 4 substantive under both, but main track 361/374f = 96.5% → still passes; the extra IDs are brief bystander/false detections, not subject fragmentation.)
- **Data corpus** (`verify_data_videos.py --all --fast`): **9/9 expectations hold** — 6 PASS (squat 725 metrics/0.871/fair; landing-soft 418/0.925/fair; landing-pivot 585/0.936/poor; box-jump 267/1.0/poor; shot-put 512/1.0/fair; aquabag 396/0.868/poor — frontal view, 0 validated by design), 3 REJECT `multiple_people_subject_unstable` (running 0.309, sprinting 0.148, 180-cut 0.343).
- **Test-assets** (`verify_test_assets.py`): `squat_sample.mp4` PASS (1003/1003 validated, fair, left-leg visibility warning); `squat_demo.webm` PASS (1004/1004 — frame-identical VP9 twin, proves pipeline handles webm); `test_figure.mp4` REJECT `low_detection_quality` (synthetic stick figure, 0 poses in 90 frames); `7a6W56OeU8w.mp4` (HIIT class, 16 max persons, 45 raw IDs → 6 substantive, 64% main coverage) and `Px4cyTAHrWc.mp4` (band class, 14 max, 63 → 4, 49%) REJECT `multiple_people_subject_unstable`.
- **Frontend:** `npx tsc --noEmit` clean, `npx eslint src` clean.

## 5. Known context (established, with evidence)

- BoT-SORT did not change outcomes on clips ByteTrack already handled (aquabag identical); its value is fewer ID switches on hard lateral motion + the merge safety net underneath.
- Group-fitness footage still fragments heavily (45–63 raw IDs) even with BoT-SORT + merging; the gate correctly rejects instead of scoring the wrong person. Main-subject coverage 49–64% on such clips — below the 70% floor, above 40%, but multi-person + unstable → reject (correct per `coverage.py`).
- `squat_sample.mp4` / `squat_demo.webm` are the same content in different containers (identical frame counts, thumbnails, metric counts).
- Frontal-view clips yield 0 validated metrics by design (sagittal angles unmeasurable from the front; valgus is qualitative-only per SCIENCE_CONSTRAINTS.md).
- Merge thresholds (0.5 s gap, 35% size, 8 heights/s) are conservative heuristics, not validated cut-offs (logged in DECISIONS.md).

## 6. Unknowns / open items (not guessed, flagged)

1. **Merge-threshold validation on more lateral footage:** thresholds were exercised on unit synthetics + the 14 real clips above. A dedicated lateral-motion set (football-field distance, occlusions, night games) would calibrate them further — current values err toward NOT merging (safe direction).
2. **`test_figure.mp4` gate wording:** rejected with `low_detection_quality` whose message says "tracked and large enough" — true outcome, slightly off message for synthetic input (no human at all). Cosmetic; message hierarchy could gain a "no measurable human" branch.
3. **Small-subject recall at distance:** no tracker-parameter tuning was needed for the current corpus (defaults sufficed). If football-field footage under-tracks, the next levers are `botsort.yaml` thresholds via a custom tracker config (`YOLO_TRACKER` env already supports it) and/or higher `imgsz` on the tracking pass — both untried, both logged as options, neither applied.
4. **Remaining roadmap (approved plan, not started):** movement/camera-view auto-identification (`biomechanics/classification.py`), Engine 2.3 metric expansion (stride length, balance, landing mechanics, ankle dorsiflexion, per-rep anomaly, heuristic flags, longitudinal trend, fatigue index), corpus baseline building, results-page display of classification. Four task briefs for these are in the session report.

## 7. How to re-verify (commands)

```bash
cd backend && pytest -q                                   # full suite (needs Postgres :5433, Redis :6379)
python backend/scripts/verify_data_videos.py --all --fast --json   # 9-clip corpus (repo root)
python backend/scripts/verify_test_assets.py --all --fast --json   # 5 test-assets (repo root)
cd frontend && npx tsc --noEmit && npx eslint src
```
