# Integration pass: Tasks 1–4 → golden

Tasks 1–4 were built in isolation. Each one passed its own tests. Merged, the backend was fine (517 passed) but the pieces did not connect. This pass fixes the seams.

**Bottom line:** apply `integration_fix_changed_files.zip` last. The result is 540 backend tests passing, frontend type-check and lint clean, the production build compiling (Google Fonts mocked), and the one cross-language contract that was silently broken pinned by a test on each side. What is *not* verified is listed in §6. Read it.

| # | What was wrong | Proof it was wrong | Fix |
|---|---|---|---|
| D1 | T4's results card read fields T1 never writes | the card rendered for **0 of 6** real classifications | page reads T1's real shape; one pure helper; contract test both sides |
| D2 | "Auto-detect" upload option was a dead end (backend rejected `auto`) | `INVALID_MOVEMENT_TYPE` / 422 | backend resolves `auto/auto` from the footage, fail-closed |
| D3 | `.webm` `.mkv` **and `.avi` `.m4v`** uploads failed | new HTTP-level test fails for 4 of 6 formats on the merge | one extension list for both gates; duration fallback |
| D4 | stride / overstride read 12–22% low | measured on closed-form running | amplitude read from a track without the despike pass |
| D5 | ankle dorsiflexion tagged `validated` against its own evidence | ICC 0.43–0.48 vs. the project's science rules | `qualitative` |
| D6 | T3 said the pipeline "does not measure" foot position | T2 now records `overstride_indicator` | wording fixed, tied to the metric name by a test |
| D7 | all four tasks edit `docs/DECISIONS.md` | unzipping in order keeps only the last | merged file shipped (8 entries) |
| D8 | T1's biggest caveat (thresholds untested on real clips) had no tool | — | `process_corpus.py` prints classifier-vs-label table |

---

## 1. Apply

From the repo root, in this order. `-o` overwrites without asking.

```bash
unzip -o T1_auto_identification_changed_files.zip
unzip -o engine_2_3_changed_files.zip
unzip -o task3_changed_files.zip
unzip -o task4_changed_files.zip
unzip -o integration_fix_changed_files.zip     # LAST
```

Order matters twice. `docs/DECISIONS.md` is edited by all four task zips, so each overwrites the previous one; the last zip carries the merged file with every entry. And 16 of the files in the last zip are full-file versions built *on top of* the four tasks, so applying it earlier would silently undo them.

On Windows: extract in the same order and choose "replace".

## 2. Verify

```bash
# backend: Postgres + Redis up (test_upload_formats needs ffmpeg or it skips)
cd backend && pytest                                  # 540 passed

# frontend
cd frontend
npx tsc --noEmit && npx eslint src --max-warnings=0
npm run build                                          # needs Google Fonts reachable
node e2e/classification_contract.mjs                   # 6/6, no browser, Node >= 22.18

# with the stack up (backend + worker + db + redis): the numbers that matter (§6)
python backend/scripts/process_corpus.py
cd backend && python scripts/reprocess_metrics.py --dry-run && python scripts/reprocess_metrics.py
```

What I ran, in a clean tree (base + the four zips + this one): everything above except `npm run build` against real Google Fonts (built with `next build --webpack` and Next's font mock, because the sandbox cannot reach them) and the stack-dependent items. `ultralytics` was stubbed, so no real YOLO weights ran.

## 3. What changed, and why

### D1. The results card could never show anything

T4 had no classifier to read, so it guessed: `detected_movement` / `detected_view`. T1 writes `movement_type`, `camera_view`, `declared`, `agrees`, `suggested`. On real output the card returned `null`, so there was no error, no console message and no failing test (T4's e2e script injected its own made-up JSON).

- `frontend/src/lib/types.ts` — `VideoClassification` is T1's real shape.
- `frontend/src/lib/format.ts` — `classificationRows()`: one pure function that turns the stored classification into the two rows the card shows.
- `.../videos/[id]/results/page.tsx` — the card uses it.
- It trusts the backend's `agrees` / `suggested`. T4 compared labels in the browser with `===`; T1 deliberately warns only on a *confident, different-group* mismatch, so `===` would have raised a false warning every time a sprint was labelled running. Same-group differences now show a muted "Suggested instead of the label" badge, as T1 intended.
- A classifier under half-sure shows "Couldn't tell", not a guess.

**The contract is now pinned on both sides.** `backend/tests/test_classification_contract.py` runs six real clips through `analyze_frames` and requires the stored classification to equal `frontend/e2e/fixtures/classification_contract.json`. `frontend/e2e/classification_contract.mjs` runs the page's own helper over the same file. If either side's shape drifts, one of them fails. To change the shape on purpose: `UPDATE_CONTRACT_FIXTURE=1 pytest tests/test_classification_contract.py`, then update `types.ts`.

`e2e/part4_classification.mjs` now injects the real shape (plus two new cases: a same-group suggestion and an auto upload). **I could not run it** (needs Chrome and the live stack); it is syntax-checked only.

### D2. Auto-detect: a real feature now, fail-closed

T4 added an "Auto-detect" option that sends `movement_type: "auto"` and `camera_view: "auto"`. Nothing in the backend accepted that. I built the backend half rather than delete the option, with one design rule: **a wrong automatic label silently puts a clip in the wrong baseline, and T1's thresholds are synthetic-only, so when in doubt it refuses.**

| step | behaviour |
|---|---|
| `POST /videos/upload-url` | `auto` is accepted only for **both** fields (else 422). Stored as `auto/auto`. No migration: `videos.camera_view` has no CHECK in `0001`–`0005`. |
| worker, before anything is stored | `identify_labels()`: both verdicts known **and** `confidence >= 0.7` (`WARN_MIN_CONF`). |
| accepted | real labels are written to the video; `analysis.classification.declared` stays `auto`, `agrees` is null; the page says "Identified from the footage". `reprocess` keeps that. |
| declined | video fails with `movement_not_identified`; nothing stored; the UI tells the user to choose. |
| jumping / landing / cutting | T1 caps them at 0.6, so they **always** decline. That is correct: jump-vs-landing cannot be told apart yet. |
| a declared label | **never replaced** (T1's rule; there is a test that a run uploaded as a squat keeps its label and gets a warning). |

Files: `video/schemas.py`, `video/router.py`, `pose/tasks.py`, `pose/processing.py`, `pose/reprocess.py`, `biomechanics/classification.py` (the `AUTO` constant), `tests/test_auto_labels.py`, upload page copy. I also removed T4's "this server can't auto-detect" fallback: it would have mislabelled any unrelated 400/422 on an auto upload.

**Do not trust it blind.** On synthetic clips the classifier reports confidence 1.0; real clips will be lower, so expect many declines. Run `process_corpus.py` and read the last two lines of its new table: *"Auto-detect would label N right, M WRONG, decline K."* WRONG must be 0. If it is not, delete the `Auto-detect` radio in `videos/upload/page.tsx` and raise the gate.

### D3. Four formats were broken, not two

T4 found `.webm` and `.mkv`. The new test (`tests/test_upload_formats.py`) drives the whole path (upload-url → storage PUT → confirm-upload) with a real ffmpeg clip per format. On the merge it fails for **webm, avi, mkv and m4v**; mp4 and mov pass.

1. `STORAGE_KEY_PATTERN` in `main.py` still allowed `mp4|mov` only → the PUT answered 400. The 2026-10-07 format change had missed this storage-key gate.
2. ffprobe reports no per-stream duration for WebM / Matroska → `confirm_upload` rejected them. It now falls back to the container duration.

One `VIDEO_EXTENSIONS` constant in `video/router.py` now feeds both gates so they cannot drift again. Correction to the 2026-10-07 STATE entry: "`squat_demo.webm` PASS — upload API now accepts it" was true of the pose pipeline only.

### D4. Stride length and overstride were biased low (▲ changes numbers)

T2 measured it and left it. I re-measured and traced it: the Hampel despike in `clean_track` clips the extremes of fast cyclic motion.

| cadence (spm) | 150 | 170 | 200 | 230 |
|---|---|---|---|---|
| stride bias, before (no noise) | −11.9% | −11.9% | −11.9% | −21.5% |
| stride bias, before (2 cm noise) | −8.5% | −10.2% | −13.6% | −21.7% |
| stride bias, **after** (no noise) | −0.2% | −0.7% | −1.7% | −1.2% |
| stride bias, **after** (3 cm noise) | +1.1% | +0.7% | −0.1% | −0.7% |

**I did not change the shared despike.** Shrinking its window fixes the bias but weakens glitch rejection, and I measured the trade with a 0.4 m injected glitch: a 3-frame half-window rejects glitches up to 3 frames, 2 rejects 2, 1 rejects 1. How long real MediaPipe glitches last needs your real clips. Changing it would also move every existing metric, baseline and T1's classification.

Instead the two amplitude metrics read their peaks from a second track cleaned *without* that pass (`clean_track(..., despike=False)`, gait movements only, identical NaN pattern), and the median over steps absorbs glitches: a 3-frame 0.4 m glitch changes neither value. `overstride_indicator` became a median (was a mean). T2's test band tightened from 0.85–1.02 to 0.97–1.02. Files: `pose/analysis.py`, `pose/processing.py`, `biomechanics/movement_analysis.py`, `seed.py` (descriptions no longer say "reads low").

**Still open:** every other peak-based fast-movement metric still passes through the despike (T2's limit 1). Measure them on real clips before touching it.

### D5. Ankle dorsiflexion is `qualitative` (▲ changes behaviour)

`SCIENCE_CONSTRAINTS.md` says the usable sagittal angles are knee/hip flexion and trunk lean. T2 tagged the ankle `validated` only because "sagittal = validated", while its own cited study (Russo 2026) found MAE ≈ 7.5° and ICC 0.43–0.48, and said the tag was doubtful. Only `validated` per-frame metrics become anomaly features, so as shipped the ankle would have entered scoring with an error above the 3.25° noise floor *and* (T2's own limit 2) made every pre-2.3 baseline video count as incomplete ("baseline building" after deploy). As `qualitative` neither happens.

**To reverse:** set the two ankle entries in `METRIC_CONFIDENCE` (`calculations.py`) and the ankle row in `seed.py` back to `"validated"`, and flip the assertion in `test_lower_body_calculators_emit_ankle_qualitative…`.

Related: `seed_movements` now **updates** existing registry rows instead of skipping them, so a database seeded by an older version converges on the code (the registry is informational; behaviour follows the code, not the table). Test: `test_reseeding_converges_a_registry_seeded_by_an_older_version`.

### D6. T3's overstride text

The flag still never fires (no validated cut-off exists), but its `reason` / `caveat` said the pipeline "does not measure" foot position, which stopped being true when T2 added `overstride_indicator`. Reworded; an assertion ties the caveat to the metric name.

### D7. DECISIONS.md, SCHEMA.md, STATE.md, AGENTS.md

- `docs/DECISIONS.md`: all seven task entries + one new 2026-10-09 entry for this pass (including the two ▲ items and their reverts).
- `docs/SCHEMA.md`: the `camera_view` spec line allows `auto` (transient).
- `docs/STATE.md`: a verified block for 2026-10-09; "Last verified" moved; engine version 2.3.
- `AGENTS.md`: "Engine 2.2" → 2.3 and "384 passed" → 540, so the next agent does not start from stale facts.

### D8. `process_corpus.py` closes T1's open loop

T1's report says its thresholds are synthetic-only and that this script was the natural place to check them on real clips. It now prints, per completed clip: what the classifier saw, its confidence, the backend's `agrees` verdict for movement and view, and what Auto-detect would have done; then the count of false alarms and the right / WRONG / declined tally. Every corpus label is known-right, so every `DIFFERS` is a false alarm.

## 4. Calls I made that you may reverse

| call | why | revert |
|---|---|---|
| Built Auto-detect instead of deleting the option | T4's UI and report expected it; fail-closed makes it safe to ship | delete the radio block in `videos/upload/page.tsx` |
| Gate at 0.7 for both verdicts | the value T1 already uses to warn | `WARN_MIN_CONF` in `classification.py` (also moves T1's warning) |
| Ankle → `qualitative` | evidence below the project's own bar | D5 |
| Left the shared Hampel alone | needs real clips to choose the trade | — |
| Seed now overwrites existing registry rows | otherwise a DB seeded earlier keeps stale tiers/text | revert the `if row:` branch in `seed_movements` |

## 5. Not changed, on purpose

- The shared despike, and any threshold in T1–T3. All are synthetic-validated only.
- T2's video-level metrics (stride, flight time, contact flexion, stiff-landing index, countermovement depth, stance time, COM sway, trunk rotation velocity) are stored in `analysis.movement.metrics` but **no page displays them**. Nobody's task covered that.
- The `validated` tag on T2's video-level proxies (e.g. stiff-landing index is a kinematic proxy, not a force) follows T2's rule; I did not re-litigate it.
- `frontend/e2e/part4_classification.mjs` was not executed.

## 6. Not verified: do these before trusting the numbers

1. `python backend/scripts/process_corpus.py` on the 14 real clips, then read **"Classifier vs the known labels"**: false alarms should be near 0 and Auto-detect WRONG must be 0. Nothing in T1–T3 has been checked on real footage.
2. `reprocess_metrics.py`: videos processed before this pass have no `classification` and no `analysis.movement.metrics`. Reprocessing re-runs no pose model.
3. Chrome run of `e2e/part4_classification.mjs` against the live stack.
4. `npm run build` with network access to Google Fonts (I used the font mock).

## 7. Files in `integration_fix_changed_files.zip`

Backend — `app/main.py`, `app/seed.py`, `app/modules/biomechanics/{calculations,classification,movement_analysis}.py`, `app/modules/pose/{analysis,processing,reprocess,tasks}.py`, `app/modules/risk_scoring/movement_signals.py`, `app/modules/video/{router,schemas}.py`, `scripts/process_corpus.py`, tests: `test_engine_2_3.py`, `test_movement_signals.py`, `test_process_corpus.py` (edited); `test_auto_labels.py`, `test_classification_contract.py`, `test_upload_formats.py` (new).

Frontend — `src/lib/{types,format}.ts`, `src/app/(authenticated)/videos/[id]/results/page.tsx`, `src/app/(authenticated)/videos/upload/page.tsx`, `e2e/part4_classification.mjs` (edited); `e2e/classification_contract.mjs`, `e2e/fixtures/classification_contract.json` (new).

Docs — `DECISIONS.md` (merged), `SCHEMA.md`, `STATE.md`, `AGENTS.md`, this file.
