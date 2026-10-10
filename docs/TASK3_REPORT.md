# Task 3 report — rep outliers, heuristic flags, athlete trend, fatigue index (2026-10-08)

Scope: Task 3 only (`risk_scoring/` + recommendations rules). No file owned by T1, T2 or T4 was touched.
Everything below marked "executed" was run on the final tree; nothing is reasoned-only unless it says so.

## 1. Files in this change

| File | Change |
|---|---|
| `backend/app/modules/risk_scoring/movement_signals.py` | **new**: pure `rep_outliers`, `fatigue_index`, `heuristic_flags`, `athlete_trend`, plus the `FLAGS` evidence table |
| `backend/app/modules/risk_scoring/service.py` | `_population_rep_peaks`, `_prior_features`, `_extras` (one guarded call); four new keys in the assessment; flags passed to the injury categories |
| `backend/app/modules/risk_scoring/injury_categories.py` | `FLAG_DRIVERS`, `FLAG_POINTS`; new optional `heuristic_flags=` argument; module docstring |
| `backend/app/modules/recommendations/rules.py` | `FLAG_RECS` and one block (flagged flags only) |
| `backend/tests/test_movement_signals.py` | **new**: 23 tests |
| `docs/DECISIONS.md` | one entry, 2026-10-08 |
| `docs/TASK3_REPORT.md` | this report |

Deliberately **not** touched: `ENGINE_VERSION` (the scoring version is T2's), `schemas.py` (`RiskScoreResponse` is not wired to the route, which returns the raw dict), `docs/STATE.md` (four tasks edit it in parallel; update it once after the merge), the frontend (T4), `biomechanics/*`, `pose/*`.

## 2. What the API now returns

Four new keys inside the existing assessment (stored in `risk_scores.assessment`, no migration). They are additive: **the composite score, sub-scores, baselines and notifications are unchanged.** A block that cannot be computed is `{"available": false, "reason": "..."}`; it is never a zero.

```jsonc
"heuristic_flags": [ { "key": "stiff_landing", "label": "Stiff landing", "status": "flagged",   // flagged | borderline | ok | not_assessable
                       "value": 38.0, "unit": "deg", "threshold": 45.0, "margin": 6.5,
                       "measure": "...", "evidence": "...", "caveat": "..." },
                     { "key": "overstride", "status": "not_assessable", "value": null, "reason": "..." } ],
"rep_outliers":  { "available": true, "score": 100.0, "flagged": true, "n_reps": 6,
                   "worst_rep": { "rep": 4, "peak_deg": 55.0, "from_set_median_deg": -44.5 },
                   "z": 12.68, "population": { "videos": 12, "athletes": 4, "provisional": true }, "label": "..." },
"fatigue_index": { "available": true, "index": 89.7, "n_reps": 6, "total_change_deg": -24.0, "direction": "decrease", "label": "..." },
"athlete_trend": { "available": true, "n_priors": 5, "notable": true,
                   "changes": [ { "feature": "knee_flexion_angle_left.p95", "value": 60.0, "prior_median": 100.0,
                                  "change_deg": -40.0, "z": -6.15, "n_priors": 5 } ], "label": "..." }
```

Only the flags that apply to the movement are listed: landing → stiff landing; squatting → partial-depth squat; running → low step rate + overstride; sprinting → overstride; other movements → `[]`.

## 3. How each one works

- **Rep outliers** (squatting, landing, jumping, throwing). For the scored set take the worst rep's distance from the set's own median peak, and compare that number with the same number in other videos' sets (their `rep_peaks` are already stored in `videos.analysis`). Scored with the engine's existing `robust_z` + `z_tail_score`, so it inherits the 3→5 robust-SD ramp, the 6.5° noise floor and the small-population widening. Refuses (unavailable + reason) below 3 reps, below the baseline's own video/athlete floors, or when a leg was not reliably visible. Reps are counted on the signal stored with each video; videos counted on a different signal are not mixed in.
- **Fatigue index** (≥ 5 reps). |Theil–Sen total change of the rep peaks| ramped from 1× to 4× the 6.5° pose noise. Direction is reported, not assumed harmful (SCIENCE_CONSTRAINTS: no consistent direction in the meta-analysis). Median-of-slopes means one bad rep cannot create or hide a drift.
- **Athlete trend**. This video's features against the same athlete's *earlier* videos of the same movement and camera view (newest 10, at least 3 sharing the feature). Robust z with a scale never below the 6.5° pose noise (set-ups differ between sessions), |z| clipped at 10, five largest changes, `notable` at |z| ≥ 2. Descriptive and labelled as such.
- **Heuristic flags**. Absolute cut-offs, all "lower is worse". A flag is `flagged` only when the value is beyond the cut-off by *more than its measurement margin*; inside the margin it is `borderline`. Uncertainty is never read as a finding.

| Flag | Applies to | Input | Cut-off (margin) | Source | Feeds |
|---|---|---|---|---|---|
| Stiff landing | landing | knee-flexion range across the clip (p95 − p05, reliable legs) | < 45° (6.5°) | LESS knee-flexion-displacement item (Padua 2009, Am J Sports Med 37:1996, doi:10.1177/0363546509343200; items in PMC4527442); stiff upright landings had higher impact force / vGRF than soft ones in a 28-woman single-leg study (SL-LESS, doi:10.25035/jsmahs.09.02.03) | ACL driver (w 1.5) + recommendation |
| Partial-depth squat | squatting | p95 knee flexion (reliable legs) | < 90° (6.5°) | partial squat < 90°; only the half-squat group of a 10-week loaded-squat trial (53 men) reported rising pain, stiffness, disability (Pallarés 2019, Eur J Sport Sci, doi:10.1080/17461391.2019.1612952) | recommendation only |
| Low step rate | running | `gait.cadence_spm` | < 166 spm (5 spm) | lowest-tertile high-school runners (≤ 166 spm, self-selected pace) had higher odds of shin injury, OR 5.85 (95% CI 1.1–32.1) (Luedke 2016, Med Sci Sports Exerc, PMID 26818150); lower step rate predicted bone stress injury in 54 collegiate runners, RR 0.95 per +1 step/min (Kliethermes 2021, Br J Sports Med 55:851) | overuse driver (w 1.5) + recommendation |
| Overstride | running, sprinting | — | — | foot landing position relative to the hip (Lieberman 2015, J Exp Biol 218:3406) | nothing (refused, below) |

Category drivers use coarse points (ok 0 / borderline 33 / flagged 66): a flag alone can never reach "critical" (> 75). Partial-depth feeds no category because the evidence is loaded-squat pain/ROM, not an injury outcome; claiming otherwise would be an unsourced claim.

## 4. Left out on purpose

- **Overstride is not flagged.** The pose pipeline does not measure foot landing position, and no cut-off exists in the literature to flag it against. Inventing either would be a fabricated claim, so it returns `not_assessable` with that reason. Low step rate is the evidence-linked proxy. To enable it: a calculator that emits foot-landing-position-over-leg-length (T2's stride-length work is the natural home) plus a population-relative rule once there is data. Any new validated metric already flows into `athlete_trend` and the baselines with no change here.
- **Not wired into the composite or `ENGINE_VERSION`.** Changing `score_fatigue` to use the new index would shift every stored score and needs the version bump that belongs to T2.
- **No recommendations for rep outliers, fatigue index or trend** (not requested; the data is in the payload). **No frontend** (T4).
- **Simplifications with a known ceiling** (marked `ponytail:` in the code): rep outliers use peaks only and are not stratified by set length; the athlete trend's priors can include a poorly visible leg and cost a second population scan per assessment; fatigue index has no tempo / velocity-loss term (per-rep timing is not stored); the stiff-landing input is the clip's knee-flexion range, not displacement measured from initial contact.
- **Limits that matter to a reader:** `SCIENCE_CONSTRAINTS.md` prefers relative (within-session / own-trend) comparison over "an absolute number compared to an outside standard", and the heuristic flags are exactly the latter because absolute literature cut-offs were the brief. Mitigation: a measurement margin before anything is `flagged`, a per-flag `caveat`, capped driver points, and no influence on the composite. Also: depth and landing flags read monocular angles that over-read by ~17° in squats, so a flag is credible and a pass is not proof; the low-step-rate cut-off is one cohort's tertile with a wide interval and step rate rises with speed (a slow jog reads low); the rep-outlier rates below come from simulated sets, because no labelled real "bad reps" exist yet.

## 5. Verification (executed)

| Check | Result |
|---|---|
| Full suite, final tree (`pytest -q`) | **417 passed, 0 failed** (394 existing + 23 new), 7 min 9 s |
| Calibration (`tests/test_anomaly_calibration.py`) | **8 passed**: normal videos rarely anomalous at 10 and 30 baseline videos, large deviation caught, monotone, conservative, refuses below the floor, features explained, order-independent |
| New tests (`tests/test_movement_signals.py`) | **23 passed**, including one end-to-end test through the real API (below) |
| Mutation checks (6 deliberate breaks on a scratch copy) | **6 / 6 caught**: wiring removed, comparison flipped, population scale ×3, category-driver loop removed, supersede step removed, Theil–Sen replaced by endpoints; the unmutated control passed |

The end-to-end test scores a real analysed squat clip through `GET /risk-score` and `GET /recommendations` against a 12-video, 3-athlete baseline and checks: the four blocks are present; the partial-depth flag is `flagged`; the fatigue index is available and reads `decrease`; rep outliers are available against the 12-video population; the athlete trend finds ≥ 3 earlier videos and calls the change notable; the depth recommendation appears exactly once and carries its evidence; and with `_extras` made to raise, the composite score and category are identical and the four keys are simply absent (failure isolation, composite untouched).

Rep-outlier rates (simulated sets: reps ~ N around 100°, athlete steadiness log-normal, 3–10 reps per set; 400 trials per cell):

| Population videos | Normal set scores > 50 | One rep 45° off | 30° off | 20° off |
|---|---|---|---|---|
| 30 | 1.0% (3.0% with heavy-tailed reps) | 98% | 60% | 14% |
| 10 | 0.2% | 85% | 39% | 7% |

The spread (SD) of the rep peaks was simulated first and caught a 45° rep only 20–42% of the time, which is why the worst-rep deviation is used. These are simulated sets; there are no labelled real "bad reps" to validate against yet.

**Environment (what this run was, exactly)**
- Python 3.12 venv with the repo's pinned requirements (numpy 1.26.4, scikit-learn 1.6.1, …); mediapipe resolved to 1.1.0 (requirement `>=1.0.1`).
- **`ultralytics` was a stand-in.** `download.pytorch.org` is blocked in this sandbox and PyPI's torch needs multi-GB CUDA libraries, so torch/ultralytics could not be installed. Every test imports `app.main` → the pose worker → `ultralytics`, so a no-op `YOLO` class (raises if instantiated) sat outside the repo on `PYTHONPATH` for the test runs only. The repo's tests inject fake models; none loaded real weights. It is not in the zip.
- Postgres 16 on :5433 with an isolated database (`injury_detection_test_t3`, UTF-8) and Redis on :6379. A first full run on a SQL_ASCII cluster failed 4 pose tests (`test_pose_tasks.py` × 3, `test_worker_task.py` × 1: "unsupported Unicode escape sequence"); the same four fail identically on the pristine tree and pass once the database is UTF-8, so that was the environment, not the code.
- **Not run:** the real-model scripts (`verify_data_videos.py`, `verify_test_assets.py`; they need YOLO weights and the data videos), frontend `tsc` / `eslint` (no frontend file changed), the Docker stack. None of them exercise the files changed here.

## 6. Merge notes for the other three tasks

- `docs/DECISIONS.md`: all four tasks insert at the top of the log, so expect a trivial conflict; keep every entry.
- **Stored scores:** `ENGINE_VERSION` is unchanged here, so assessments already stored under 2.2 do not contain the new keys until `?recompute=true` or until T2's version bump lands. New assessments contain them immediately.
- `docs/STATE.md` still needs one line after the merge (I did not edit it).
- T4: render `heuristic_flags[].status`, `reason` for `available: false`, and the `label`/`caveat` strings; every flag entry has the same keys, including overstride.
- Coupling to other tasks: none by name. The code reads `analysis.movement.reps` (`rep_peaks`, `signal`), `analysis.movement.gait.cadence_spm` and the feature keys `knee_flexion_angle_{left,right}.{p95,p05}`, all of which exist today.

## 7. Re-verify

```bash
cd backend && pytest -q tests/test_movement_signals.py           # 23 new tests (needs Postgres + Redis for the end-to-end one)
cd backend && pytest -q                                          # full suite
cd backend && pytest -q tests/test_anomaly_calibration.py        # calibration
```
