# DECISIONS.md

Append-only. New entries go at the top of their section, dated, never edited or deleted after the fact.

## Format for new entries

```
### YYYY-MM-DD — Short title
**Decision:** what was decided
**Why:** the reasoning
**Alternatives considered:** what else was on the table, if relevant
```

---

## Decisions log

### 2026-10-07 — Lateral-motion tracking: BoT-SORT + ID-fragment merging
**Decision:** `pose/pipeline.py` runs YOLO tracking with `tracker="botsort.yaml"` (was the ByteTrack default; override with `YOLO_TRACKER=bytetrack.yaml`) and merges ID-switch fragments of the same person before main-subject selection. `merge_track_fragments(tracks, fps)` is pure: two fragments merge only when temporally disjoint (no shared frames) with gap ≤ 0.5 s, median box heights within 35%, and box-centre displacement ≤ 8 subject-heights/s; union-find, merged track keeps the earliest fragment's ID. `track_persons` takes `fps=` (gap in seconds); `pose/tasks.py` and `scripts/verify_data_videos.py` pass the real fps.
**Why:** ByteTrack's constant-velocity motion model loses athletes on sharp cuts and re-acquires them under new IDs — one lateral-moving person fragmented into several substantive tracks, reading as false "multiple people" with deflated per-fragment coverage and wrongful rejection. BoT-SORT's motion model survives direction changes; merging repairs residual switches. Overlapping-in-time tracks NEVER merge, so genuine group scenes (3 runners, HIIT class) still read multi-person and are still rejected/flagged honestly. Thresholds (0.5 s, 35%, 8 heights/s) are conservative engineering heuristics, not validated cut-offs; they only affect track attribution, never raise a score.
**Verification:** 7 new unit tests in `tests/test_tracking.py` (single-athlete ID switch merges; transitive 3-fragment merge; simultaneous people / teleport / size mismatch / long gap never merge; end-to-end via fake model); full `pytest` **394 passed**; `verify_data_videos.py --all --fast` 9/9 expectations hold (6 pass, 3 reject `multiple_people_subject_unstable`); all 5 `test-assets/` clips verified (`scripts/verify_test_assets.py`): 2 squats pass, synthetic stick-figure + 2 group-fitness classes correctly rejected.

### 2026-10-07 — Broader video-format support (.webm, .avi, .mkv, .m4v)
**Decision:** upload validation now accepts `.webm`, `.avi`, `.mkv`, and `.m4v` in addition to `.mp4`/`.mov`: widened `SAFE_FILENAME_PATTERN` and the `confirm_upload` extension check in `backend/app/modules/video/router.py`, and updated `acceptFile`, the file-input `accept` attribute, and helper/error copy in `frontend/src/app/(authenticated)/videos/upload/page.tsx`. No shape changes (typed Pydantic models untouched, snake_case keys unchanged); all other gates unchanged (ffprobe validation, 2–60 s, ≥480p, ≤200 MB); annotated-video output stays `.mp4`.
**Why:** ffprobe validation is codec-agnostic and OpenCV decodes webm (VP9) / avi / mkv fine, so the `.mp4`/`.mov`-only gate was an artificial restriction, not a pipeline limit.
**Verification:** `tests/test_video_upload.py` (3 passed, isolated DB `injury_detection_test_fmt` + Redis db 2); `npx tsc --noEmit` clean; `npx eslint src` clean.

### 2026-10-04 — Native host execution support & Docker Desktop zombie mitigation
**Decision:** Support both Docker Compose execution and direct native Windows host runtime (`postgresql-x64-17` on port 5432, local uvicorn on port 8000, local Next.js on port 3000). Added `backend/.env` configuration pointing to port 5432. Documented and cleared orphaned Windows processes (`com.docker.backend`, stale `docker` / `docker-compose` CLI processes) that hung named pipes (`//./pipe/dockerDesktopLinuxEngine`) and blocked commands. Live stack verified with all 5 Alembic migrations (`0001` → `0005`), database seeding (`python -m app.seed`), live backend `/health` (HTTP 200), and automated browser login flow to `/dashboard/coach`.
**Why:** In non-elevated user sessions on Windows hosts where `com.docker.service` cannot be started without administrative UAC elevation (System Error 5: Access is denied), native execution allows immediate full-stack development, database migration execution, and UI verification without container virtualization dependencies.
**Verification:** Native PostgreSQL 17 on 5432 migrated to revision `0005`, seeded with 5 demo roles; FastAPI running on `localhost:8000` (docs and auth endpoints responsive); Next.js running on `localhost:3000`; automated browser subagent logged into `coach@demo.com`, navigated to `/dashboard/coach`, and loaded real athlete profiles from the database.

### 2026-10-02 — Containers get container-correct service URLs; readiness probe added
**Decision:** `docker-compose.yml` gives `backend` and `arq_worker` an `environment:` block (shared via a YAML anchor) that sets `DATABASE_URL`, `DATABASE_URL_SYNC` (host `postgres`, port 5432, credentials from the same `POSTGRES_*` variables the database service uses) and `REDIS_URL` (host `redis`). `environment:` overrides `env_file:`, so the host-side `.env` (`localhost:5433`, `localhost:6379`) is untouched for non-Docker runs. Added `GET /health/ready` (typed, 200/503): `SELECT 1` against Postgres plus a Redis `PING`; `GET /health` stays a static liveness probe.
**Why:** inside a container `localhost` is the container itself, so the backend and worker could not reach Postgres or Redis. The existing `/health` returns `{"status":"healthy"}` without touching either, so it cannot detect this class of fault — verifying the fix "by hitting `/health`" would have passed on the broken configuration. Readiness is what deploy checks should use.
**Verification:** Docker was not available in the environment that made this change, so the stack was **not** brought up. Instead (1) `tests/test_compose_env.py` resolves the effective environment from the real compose file (fails on the original file, passes on the fix) and (2) the real app was run with the compose-resolved environment in a simulated container network (service names resolve; `localhost:5433`/`:6379` empty): original → `/health` 200 but `/health/ready` **503 (database and redis unreachable)**; fixed → `/health/ready` 200. Re-verify with `docker compose up` before relying on it.

### 2026-10-02 — Google OAuth2 is a real authorization-code flow; auth cookies are Secure; middleware reads a non-secret session hint
**Decision:** `GET /auth/google` now returns a 302 to Google with a fresh `state` (also set as a 10-minute httpOnly cookie). `GET /auth/google/callback?code&state` (what Google actually calls) validates `state` FIRST (constant-time compare of query vs cookie; before even acting on `error`), then exchanges the code, runs the existing account-linking logic, sets the refresh token as an **httpOnly, Secure, SameSite=Lax** cookie on a 302 to `FRONTEND_URL/auth/callback`, and clears the state cookie. No token is ever in a URL. The Next.js `/auth/callback` page just waits for `AuthProvider`'s bootstrap (`POST /auth/refresh` → in-memory access token → `/auth/me`) and routes to `/dashboard`. Failures redirect to `/login?error=<stable code>` (`oauth_state_mismatch`, `oauth_denied`, `oauth_code_invalid`, `oauth_email_unverified`, `oauth_account_conflict`, `oauth_account_disabled`, …). The old `POST /auth/google/callback` (JSON body, no `state` check, unreachable by a real Google redirect) is **removed**. New settings: `FRONTEND_URL`, `COOKIE_SECURE` (default true), `GOOGLE_REDIRECT_URI` documented in `.env.example`. All auth cookies are issued through `auth/cookies.py`; the password login/refresh cookies were hard-coded `secure=False` and now follow `COOKIE_SECURE`.
**Hardening added to `handle_google_callback` (linking logic otherwise unchanged):** Google must assert `email_verified` (otherwise an unverified IdP email could claim an existing password account); an account already linked to a *different* Google `sub` is rejected, not silently reused; deactivated accounts cannot sign in via Google. `access_type=offline`/`prompt=consent` were dropped: we never use a Google refresh token, so we should not request one.
**Why a session hint:** the refresh cookie is httpOnly and scoped to `/api/v1/auth`, so the browser **never sends it to `/dashboard` etc.** (verified with RFC 6265 cookie-jar semantics: `Cookie header: None`). The middleware that `frontend/AGENTS.md` requires for route protection therefore redirected every login — password or Google — straight back to `/login`. The frontend now sets a non-secret `session_hint=1` cookie at its own origin (set on login/successful bootstrap, cleared on logout/failed refresh); middleware checks that. (`frontend/src/lib/session.ts` — an earlier duplicate in `lib/session-hint.ts` was removed when the rebuilt frontend was adopted, so that `middleware.ts`, `lib/api-client.ts` and `lib/auth-context.tsx` all share one implementation.) It is not a token and grants nothing: the API still authorises every request. **Not verified in a real browser in this environment** (see STATE.md).
**Alternatives considered:** widening the refresh cookie to `Path=/` — rejected, sends a long-lived credential to every route and still fails when API and frontend are on different domains; storing state server-side in Redis — rejected, the double-submit httpOnly cookie is the standard stateless CSRF defence and needs no new infrastructure.

### 2026-10-02 — Pose coverage: diagnose why detection was low; accept partial coverage only with an explicit caveat; never measure another person
**Decision:** the 70% floor is **unchanged**. `pose/coverage.py` (pure, unit-tested) classifies a below-floor result as `subject_too_small` (selected athlete < 160 px tall), `multiple_people_subject_unstable` (several people and the athlete followed in < 70% of frames, or tracking unavailable with several people), or `low_detection_quality`; the message states the pixel height, how many people/track IDs were seen, which track was selected, and its coverage. Between 40% and 70% a clip is accepted as **partial coverage** only when the subject is large enough and reliably tracked; it is stored with an explicit `videos.coverage_caveat` (new nullable TEXT, migration `0004`) and surfaced in the API as `risk-score.data_quality`. Multi-person clips at full coverage also get a note naming the analysed track (the selection heuristic is "present in the most frames", which can pick a bystander). Below 40% the video fails. Failures now persist `person_count_detected` and `detection_rate` (both were NULL on every failed video). Videos with a caveat are scored for their own athlete but **never contribute to a population baseline**.
**Also fixed (root cause of "tracker picked the wrong one"):** when tracking was active but the selected athlete was absent from a frame, the pipeline ran full-frame pose, which in a group shot measures *whichever other person* MediaPipe finds and silently mixes identities into the athlete's metrics. For multi-person clips those frames are now skipped (`full_frame_fallback=False`), so the detection rate means "frames where the selected athlete was measured". Single-person and untracked clips keep the full-frame fallback.
**Why / limits:** the 160 px, 40%, and "10% of frames = a person" thresholds are conservative heuristics, **not validated cut-offs**; they gate wording and the partial fallback, never raise a score. `person_count_detected` keeps its meaning (max people in any single frame) and can be inflated by a one-frame duplicate detection; `tracks_seen`/substantive tracks are reported separately in messages. The two real internet clips (`test-assets/internet-clips/`) were **not available in this environment** (not in the repo zip, no network route to YouTube), so this was verified with unit tests plus `process_video` integration tests using fake YOLO/MediaPipe passes — not on real footage.

### 2026-10-02 — More findings (reported, not changed unless stated)
- **Open — schema drift found by `alembic check` (pre-existing, not caused by this work):** `ReportExport` (`report_exports`) is specified in SCHEMA.md and defined as a model but has **no migration** (nothing reads or writes it, so no runtime impact today; tests use `create_all` and cannot see it); several indexes are named `ix_*` in the models but `idx_*` in migrations; `movement_baselines` has no unique constraint in the model although the migration has one; `recommendations.priority` is `SMALLINT` in the migration and `Integer` in the model. The DoD check "`\dt` matches SCHEMA.md exactly" would currently fail for `report_exports`.
- **RESOLVED 2026-10-03 — `static-ffmpeg==2.5.1` did not resolve** when running `pip install -r backend/requirements.txt` in the environment that made this change (the index offered 2.5, 2.7, 2.8, … but no 2.5.1; 2.5 was installed instead to proceed). This may be a lagging package mirror rather than a bad pin, but if 2.5.1 does not exist on PyPI the Docker image build fails. Check `pip index versions static-ffmpeg` on a normal network before relying on the pin; the pin was left unchanged.
- **Open — existing stored risk scores keep their old values.** `GET /videos/{id}/risk-score` returns the stored row unless `?recompute=true`. Scores computed under the old self-referential baseline and percentile scale are not invalidated; recompute them after deploying this change.
- **Open — high/critical risk notifications fan out to every staff user** (all coaches, physiotherapists, scientists, admins), not just those assigned to the athlete.
- **RESOLVED 2026-10-03 (by the engine rebuild) — `hip_flexion_angle` convention.** It returns the interior shoulder-hip-knee angle (≈180° standing, falling with flexion), while its docstring says 0° = leg extended and larger = more flexed. Direction-agnostic anomaly scoring is unaffected and nothing else consumes it, so it was not changed, but the metric label is misleading. Needs a decision before the value is shown to clinicians.
- **Y-axis audit (trunk-lean fix `0e7d137`):** `trunk_lean_angle` is the only calculation that depends on the vertical axis sign. `joint_angle`, `knee_flexion_angle` and `hip_flexion_angle` are rotation-invariant vertex angles; throwing `trunk_rotation` projects onto x–z (sign-agnostic); `knee_valgus_flag` uses the x (lateral) axis in frontal views only. Checked against the documented real-landmark orientation (head y≈−0.6, hip≈0, ankle≈+0.75) with synthetic poses built from it, **not** against stored real landmarks (no database or clip was available here).

### 2026-10-02 — Defects found while fixing the listed ones (reported, not in the handoff)
- **`biomechanical_metrics.confidence` was `VARCHAR(10)`; the structural tier `'qualitative'` is 11 characters.** Any frontal/"other"-view video (knee-valgus flags) would fail to store its qualitative metrics (`StringDataRightTruncationError`, reproduced). Migration 0002 had only widened `movement_metrics`. **Fixed** in migration `0003` (→ `VARCHAR(20)`), model and SCHEMA.md; regression test `test_qualitative_confidence_tier_can_be_stored`.
- **Malformed UUID path IDs returned HTTP 500** (unhandled `DBAPIError`) instead of 422. **Fixed on the two risk-scoring endpoints** via `core.deps.UuidPath`. **Still open:** every other route that takes an ID path parameter (`athletes`, `videos`, `reports`) has the same pattern.
- **The anomaly model cache was keyed `movement:metric` only.** Once baselines became per-video (leave-one-out) that key would have served a model fitted on a baseline containing video X to X. Cache is now keyed by video id + baseline content hash and bounded to 32 entries.
- **`scripts/e2e_video_check.py` asserted the self-referential baseline was "the correct outcome"** (a single video scoring 200 against its own frames). Fixed together with the baseline change.
- **Open, not changed — `anomaly_scores` table is never written.** `AnomalyScore` is defined and read by analytics, but no code path inserts rows, so the scientist dashboard's anomaly distribution is always empty. Needs a decision on granularity (the table has no `metric_name` column) before wiring.

### 2026-10-02 — Baseline sufficiency counts videos and athletes; baselines are leave-one-video-out; insufficient baselines store NULL
> **SUPERSEDED 2026-10-03** — the engine rebuild below replaced the per-frame baseline with video-level features (floor 10 videos). What survives, and is enforced by the merged engine: the scored video is never in its own baseline; insufficient baselines store NULL (never a fabricated 0.0); the **athlete-diversity floor is kept** (`MIN_BASELINE_ATHLETES`, default 3, counted over the videos actually in the baseline). The 5-video floor and `risk_scoring/constants.py` no longer exist.
**Decision:** (1) `risk_scoring/constants.py` replaces `MIN_BASELINE_SAMPLES = 10` with three unit-named floors, all counted **excluding the video being scored**: `MIN_BASELINE_VIDEOS = 5` distinct completed videos, `MIN_BASELINE_ATHLETES = 3` distinct athletes, `MIN_BASELINE_FRAMES = 100` validated frame rows per metric (estimator floor only). (2) `baselines.fetch_baseline(db, movement_type, metric_name, *, exclude_video_id)` is the only baseline query; `exclude_video_id` is keyword-only with no default, so a caller cannot forget it. `None` is an explicit "no video under evaluation" used only by the stored descriptive population baseline, which is never used to score a member video. Rows are ordered deterministically and non-finite values are dropped before counting. (3) The anomaly model cache key now includes the video id plus a content hash of the baseline array (and the cache is bounded), so a model fitted on a baseline that contained video X can never be served to X. (4) `movement_baselines.mean_value`/`std_dev` are now NULLable and stored as NULL when insufficient (was a fabricated `0.0 ± 0.0`); new `video_count` and `athlete_count` columns make the row state its own unit (`sample_size` is per-metric frames). Migration `0003` also NULLs every pre-existing baseline row (computed under the old gate) — rebuild with `POST /baselines/recompute`. (5) The HTTP 202 body is now the typed `InsufficientBaselineResponse`: `status`, `metric_name`, `unit` (`videos`|`athletes`|`frames`), `have`, `need`, `coverage` (all three units), `message`. **Contract change:** `have`/`need` previously counted frame rows; they now count the named `unit`, and `have` excludes the scored video.
**Why:** a single 7-second clip of one athlete produced 426 validated rows per metric, so "10 samples" was met instantly and the guard that exists to stop fabricated scores effectively never fired. Separately the athlete's own frames supplied most of the "population" they were compared against, damping deviation toward zero (leakage). `0.0 ± 0.0` is a plausible wrong number; NULL is "we don't know". The floors 5 / 3 / 100 are conventions, not statistically derived: they are the point below which the "population" is one or two people. They are floors against fabrication, not evidence of adequacy, and should be raised as real data accrues.
**Alternatives considered:** counting athletes only — rejected, a single athlete's many sessions still under-represent variation but videos are the unit the model actually fits over; a caller-side `if video.id != x` filter — rejected, exactly the kind of check that gets dropped in the next refactor; keeping the previous good value on insufficient recompute plus a `sufficient` flag — rejected, stale numbers from a different population are worse than "unknown".

### 2026-10-02 — Anomaly score is anchored at 0: Isolation Forest decides "outside the envelope", baseline-robust distance decides "how far"
> **SUPERSEDED 2026-10-03** — the per-frame anomaly module this entry describes was replaced by the cross-fitted, video-level, tail-only engine below (same goal: a normal athlete scores ~0). Its measurements remain useful history.
**Decision:** `risk_scoring/anomaly.py::compute_anomaly_scores` now returns, per frame: 0 if Isolation Forest scores the frame at least as normal as the baseline's own 5th-percentile frame; otherwise `100 * (1 - 2^(-d/2))`, where `d` is the distance (in baseline robust SDs, `1.4826 * MAD` per feature) from the frame to the nearest of the 95% most-normal baseline frames. Anchors: 0 at the envelope edge, 50 at 2 SD outside, 75 at 4 SD, 87.5 at 6 SD, never 100. Fully deterministic (`random_state=42`). Direction is unchanged (higher = more anomalous). `scoring.py` formula is unchanged (`min(70, 0.7 * mean frame score)`); the `detail` string now states the scale and the baseline composition. Category cut-points **kept at low ≤25 / moderate ≤50 / high ≤75 / critical >75**; recommendation triggers on the anomaly component moved from >40 / >60 to >25 / >50 points so they track the moderate / high band floors.
**Why:** measured with the repo's own function on production-scale data (degrees, baseline N(90, 8), n=426): the old percentile-of-baseline scale gave in-distribution frames a mean percentile of ~54 (≈38 of 70 points) because the baseline's median frame is the 50th percentile by construction, so a perfectly normal athlete carried a large constant floor that is not risk. It also saturated: x4 and x8 deviations scored ~86 vs ~94 percentile. New scale, same data, mean over 10 seeds: in-distribution 0.6, scale ×2/×4/×8 = 9 / 31 / 57, mean shifted by 2/4/8 SD = 11 / 47 / 87, and worst-case movement across baseline sizes n∈{60,200,426,1200} is 7.5 points (old: ~14 even in-distribution). **Finding that shaped the design:** Isolation Forest's own decision score saturates for any point outside the training range (median decision score −0.275 for both +4 SD and +8 SD at n=426), so no transform of its output alone can separate "clear" from "extreme" — the forest is used for the in/out decision (and handles multi-modal baselines such as a squat's standing/bottom modes) while geometry supplies magnitude. Cut-points: there is no outcome data to recalibrate against (AGENTS.md law), so 25/50/75 are conventional quarter bands of a bounded index, not risk probabilities. They are kept because they were written assuming 0 = no anomaly, which is now true. The movement component caps at 70, so "critical" cannot be reached by movement pattern alone — it needs corroborating flags; that is deliberate.
**Alternatives considered:** rescaling the decision function by its MAD — rejected, the baseline-score MAD varies ~2× across n (0.027 at n=60 → 0.012 at n=1200) and the score still saturates; a median/MAD z-score on the raw metric — rejected, wrong for multi-modal baselines; subtracting 50 from the old percentile — rejected, still saturates; changing the `anomaly_scores.method` value — rejected, the locked schema pins `isolation_forest`.
**Known limits (not changed):** ~5% of in-distribution frames register a small non-zero score by construction; a multi-modal baseline has a wide robust SD so within-mode deviations are scored leniently (conservative); the composite still takes the mean over frames pooled across metrics, which dilutes a short, severe deviation (e.g. only the bottom of a squat) — revisit with real data.

### 2026-10-02 — AI engine rebuilt to the spec PDF; video analysis hardened (supersedes parts of 2026-07-11 M3 entries)
**Decision:**
1. **Baseline unit = videos, not metric rows.** The 10-sample floor now counts *other completed videos of the same movement type* (`MIN_BASELINE_VIDEOS`, default 10, env-overridable). The scored video is excluded from its own baseline. Anomaly detection runs on **video-level features** (95th/5th percentile of each validated metric), not per-frame values. *Why:* one video produced hundreds of per-frame rows, so a single clip satisfied the old floor and was scored against itself (reproduced: 1 video → HTTP 200, textbook squat 34.7 "moderate"); and per-frame values cannot detect a shallow squat at all (its frame values also occur in a deep squat).
2. **Composite follows the spec PDF: 35% biomechanical deviation / 20% injury history / 20% asymmetry / 15% training load / 10% fatigue.** This **reverses** the 2026-07-11 decision not to adopt those weights. *Why:* they are the project specification being delivered against. They remain a *specification*, not fitted to injury outcomes — no labelled dataset exists; every mapping parameter is a named constant with its evidence level stated in `risk_scoring/scoring.py`. A component with no data is reported unavailable (never scored 0) and weights are renormalised; `data_completeness` is returned.
3. **Still no injury probability.** The PDF's "injury probability prediction" is delivered as *risk levels built from named drivers*; the 2026-07-09 "No supervised injury prediction" decision stands. The five PDF scores are returned (`sub_scores`) each with a stated definition; **biomechanical efficiency is an explicit proxy** (asymmetry + rep-to-rep consistency).
4. **Six injury categories (ACL, hamstring, ankle sprain, shoulder, lower back, overuse)** via named drivers. Video kinematics are used only where research supports them (ACL; trunk for lower back/shoulder); ankle, hamstring and overuse are history/load-driven, and the response says so (`based_on`, `video_kinematics_used`).
5. **Anomaly scoring:** cross-fitted Isolation Forest percentile (removes in-sample bias) blended with a robust-z extremity score (IF is blind to points beyond the training range); only the tail counts (floor at the 90th percentile), thresholds widened by (1 + 4/n) for small baselines. Calibration (simulated, 10 correlated Gaussian features): gross outliers scored 100 in 100% of runs; a mild two-knee 25° shortfall was caught 78–88% of the time. The (1 + 4/n) widening was tuned on the **z-score component alone** (false positives with score>50: 16%→4% at n=10, →1% at n=30, while detecting 83–91% of 4σ deviations). The full *blended* scorer's false-positive rate was measured BEFORE that widening (14% at n=10, 8% at n=30) and **was not re-measured afterwards** — treat the post-widening blended rate as unverified (see HANDOFF.md, open items).
6. **Video analysis:** raw landmarks stored with MediaPipe **visibility**; landmarks below 0.5 visibility are treated as missing (never measured); short gaps interpolated, Hampel despike, per-movement frequency-aware smoothing; metrics only for frames the model observed. New per-video quality report (grade, occlusion, jitter, camera tilt, lighting, wrong camera view) and movement-specific analysis (rep segmentation + tempo for squat/landing/jump/throw; cadence + step-time asymmetry for running/sprint/cutting; mislabelled-clip detection). Pipeline: shared frame loop, monotonic timestamps from frame index/fps, per-frame error isolation, portrait-safe writer, stride for >60 fps footage, gated low-light enhancement, `POSE_LANDMARKER_VARIANT` (default `full`, was `lite`; falls back to a bundle on disk if the download fails).
7. **Schema (migration 0003):** `videos.analysis` JSONB, `risk_scores.assessment` JSONB (both nullable), and **`biomechanical_metrics.confidence` widened VARCHAR(10)→(20)**. Scores from older engine versions (assessment NULL / engine_version mismatch) are recomputed automatically on next read. `scripts/reprocess_metrics.py` re-derives metrics from stored landmarks without re-running pose models.
8. **Other fixes:** hip flexion now flexion-from-extension (was raw interior angle, ~180° standing); false `phase: "initial_contact"` stamped on every landing frame removed; ACWR counts rest days as zero over a full 28-day window (was divided by training days only, overstating chronic load) and refuses without 28 days of history; RPE trend implemented (was `pass`); high-risk alerts go to the athlete's coach/athlete/clinical roles only (was broadcast to every coach) and only on a *new* high/critical score (was re-sent on every recompute); `anomaly_scores` is now actually written; analytics trends looked up videos with a UUID against string keys so every `movement_type` was `"unknown"`; `numpy`-typed output is JSON-safe.
9. **Found by mutation testing / fuzzing / calibration after the first build (all fixed, all with regression tests):** hip flexion used the same-side shoulder, leaking ~10° of frontal-plane offset into a sagittal angle (upright pose read ~10° of hip flexion) — now uses the shoulder/hip-midpoint trunk axis like `trunk_lean_angle`; video-quality jitter was measured on the raw landmarks including a hidden leg's hallucinated coordinates, grading a clip with one occluded leg `poor` — now only frames where the limb was visible count; `np.convolve(mode="same")` crashed `analyze_frames` for clips shorter than the smoothing kernel (a 1-frame clip) — now length-safe; non-finite coordinates are treated as missing at ingestion; rep timing reported only *active* time (~12% under the true cycle for continuous reps) — an exact `mean_cycle_s` (peak-to-peak) is now reported alongside it. A 130-mutant campaign was used to harden the test suite (65/119 real mutants killed by the first suite → 128/129 by the final one; the lone survivor, the title-dedupe guard in `rules.py`, is an *equivalent* mutant because no current rule can emit a duplicate title).
**Why (the confidence-width bug):** `'qualitative'` is 11 characters; migration 0002 widened `movement_metrics.confidence`, a different table, so every frontal/"other"-view video (anything computing knee valgus) died at the metrics INSERT with `internal_error`. Reproduced by test against a database built with `create_all`; confirmed in `0001_init.py`.
**Alternatives considered:** keeping the 2026-07-11 weights (rejected — spec delivery); a trained injury-probability model (rejected — no data; see SCIENCE_CONSTRAINTS prior-art); per-athlete baselines (deferred — needs many videos per athlete); rolling camera-tilt correction of trunk lean (rejected for now — reported as a warning instead, because correcting it without real clips to validate would risk silently removing genuine forward lean).

### 2026-09-30 — Trunk lean measured against MediaPipe's downward +Y axis (real-data bug)
**Decision:** `biomechanics/calculations.py::trunk_lean_angle` now measures against `[0,-1,0]` instead of `[0,+1,0]`; added 3 regression tests. Also `static-ffmpeg==2.5.1` pinned, with `video/router.py::confirm_upload` resolving `ffprobe` from `PATH` first and falling back to the static-ffmpeg bundle.
**Why:** the first real-video E2E stored trunk lean of 154–175° on genuine squats. MediaPipe *world* landmarks use Y-down (verified against stored keypoints: head y≈−0.6, hip y≈0.0, ankle y≈+0.75), so the old reference vector inverted every lean measurement. This is exactly the class of bug unit tests with synthetic landmarks cannot catch — it only appears on real landmark data. `static-ffmpeg` is needed because the host has no system ffprobe, so `confirm_upload` could never complete outside Docker.
**Alternatives considered:** deriving "up" from nose-to-ankle vector per frame — rejected as fragile and it re-introduces the same assumption indirectly; requiring system ffmpeg on every dev host — rejected, pip-installed binaries keep the host path working.

### 2026-09-30 — Pin mediapipe>=1.0.1, add lap, verify real video end-to-end
**Decision:** require `mediapipe>=1.0.1` (was `>=0.10.21`) and add explicit `lap>=0.5.12` (ByteTrack); verified `squat_sample.mp4` end-to-end: YOLO track → MediaPipe pose (213/213 frames) → 1065 validated metrics → risk 44.7/moderate → prior-injury recommendation.
**Why:** 0.10.30's Windows wheel ships a broken `libmediapipe.dll` (loader fails with `function 'free' not found`), so the Tasks path could not run on the host; 1.0.1 verified working. `lap` was auto-installed mid-run by ultralytics — pinning makes tracking deterministic.
**Alternatives considered:** Docker-backend verification — blocked, registry pulls fail with TLS errors; host verification chosen instead.

### 2026-09-30 — Multi-person videos tracked instead of rejected
**Decision:** `pose/pipeline.py` gains YOLO tracking (`track_persons`, persistent IDs, main-subject selection by presence then box size) and `run_mediapipe_full_pass` crops each frame to the tracked athlete; `tasks.py::process_video` no longer raises `multiple_people_detected` — it logs the selected track and analyzes that one consistent person. No schema change (`person_count_detected` still records max persons seen).
**Why:** real-world clips (gyms, fields, physio rooms) routinely have other people in frame; rejecting the whole video made injury screening unusable outside a studio. Cropping before pose also keeps single-person MediaPipe (`num_poses=1`) correct without identity flips.
**Alternatives considered:** per-frame largest-box without IDs — rejected, identity flips frame-to-frame corrupt per-frame metric series; multi-pose estimation + clustering — rejected, MediaPipe single-pose plus crop is simpler and already in the stack.

### 2026-09-30 — M4 reports deps + mediapipe dual-API support
**Decision:** add `reportlab==4.2.5` + `openpyxl==3.1.5` for PDF/Excel risk-report export; relax `mediapipe==0.10.21` to `mediapipe>=0.10.21` with dual `solutions`/`tasks` code path in `pose/pipeline.py`.
**Why:** PDF brief modules 12 requires PDF/Excel export with methodology_note preserved; host Python 3.13 cannot install 0.10.21 and newer mediapipe removed `solutions.pose`, while Docker Python 3.12 still uses it — dual path works in both.
**Alternatives considered:** pin Python 3.12 locally — rejected, host toolchain stays 3.13.

### 2026-07-11 — YOLO26-pose confirmed unavailable, yolov8n-pose.pt is the real decision
**Decision:** use `yolov8n-pose.pt`, not YOLO26-pose as originally logged.
**Why:** yolo26n-pose.pt is not available as a downloadable checkpoint in the installed
`ultralytics` version at build time. yolov8n-pose.pt is a mature, well-tested model and
fully adequate for this project's person-count pre-check use case.

### 2026-07-11 — Isolation Forest over an autoencoder for anomaly detection
**Decision:** `modules/risk_scoring/anomaly.py` uses `sklearn.ensemble.IsolationForest`.
**Why:** a pilot with a handful to a few dozen videos per movement type doesn't have enough data for a deep autoencoder to learn a meaningful reconstruction. Isolation Forest is meaningful with small samples, fast, interpretable, and already implied by the original brief's own tech stack (scikit-learn).

### 2026-07-11 — Anomaly score rescaling: percentile rank against baseline, not a fixed formula
**Decision:** anomaly scores are computed as the percentile rank of a sample's `decision_function` value against the baseline's own `decision_function` distribution.
**Why:** tested in a sandbox before building: a fixed linear formula assuming a universal `decision_function` range produced an uninformative narrow spread (43 vs. 65 for clearly-normal vs. clearly-anomalous test samples). Percentile rank against the baseline's own distribution self-calibrates and produced a real spread (16 vs. 96) on identical test data.
**Alternatives considered:** fixed linear rescaling — tested and rejected, see above.

### 2026-07-11 — Population-level baselines only, per-athlete deferred
**Decision:** `movement_baselines.athlete_id` is NULL for every row built in Milestone 3 — no per-athlete baselines yet.
**Why:** per-athlete baselines need multiple videos of the same athlete doing the same movement, which a new pilot won't have. Population-level only needs enough videos of that movement type across all athletes — achievable much sooner.

### 2026-07-11 — Minimum 10 baseline samples before any score is computed
**Decision:** requesting a risk score for a movement_type with fewer than 10 validated-metric samples returns `202 insufficient_baseline_data`, never a fabricated score.
**Why:** below this floor, a "baseline" is noise, not a distribution — scoring against it would be actively misleading rather than just imprecise.

### 2026-07-11 — LSI included as a bounded, caveated flag — not a pass/fail rule
**Decision:** the risk-score formula adds a fixed 15 points if LSI < 90%, always alongside the documented caveat that this threshold has known predictive-validity problems (see `docs/SCIENCE_CONSTRAINTS.md`).
**Why:** research for this milestone found a study directly titled "Return-to-Sport Criteria... Fail to Identify the Risk of Second ACL Injury" — 22% of athletes who passed the 90% LSI criteria still sustained a second ACL injury. Treating 90% as a hard safety line would misrepresent what the literature actually shows. Using it as one bounded, labeled input among three is honest; using it as the score's foundation would not have been.

### 2026-07-11 — Prior injury as a simple flag, not a weighted formula
**Decision:** `has_prior_relevant_injury` adds a fixed 15 points if present, no attempt at a more granular weighting.
**Why:** "previous injury" is a well-established risk factor generally, but there's no single citable number for exactly how much weight it deserves in a composite score — a fabricated precise percentage would be less honest than a simple, bounded flag. Same discipline applied to the original brief's invented 35/20/20/15/10 weighting, which was never adopted.

### 2026-07-11 — ACWR (training load) deferred, not built in Milestone 3
**Decision:** acute:chronic workload ratio is not part of the v1 risk score.
**Why:** needs weeks of consistent `training_load_entries` history a new pilot won't have; also, ACWR itself has faced credible methodological criticism in recent sports-science literature and shouldn't be adopted uncritically just because it's commonly referenced — the same standard applied to LSI above.

### 2026-07-11 — M2 audit applied: CHECK constraints included in M3's schema from the start
**Decision:** `docs/SCHEMA.md`'s Milestone 3 tables include `CHECK` constraints in the initial design, not added retroactively.
**Why:** `IMPLEMENTATION_REVIEW.md` finding H2 found the M2 migration silently omitted three constraints that were specified in `SCHEMA.md` at the time. Don't repeat it.

### 2026-07-10 — Presigned-URL upload, not backend-proxied upload
**Decision:** browsers upload video files directly to object storage using a presigned URL; the backend never streams the raw file through itself.
**Why:** keeps the API process free to handle other requests while a multi-MB video uploads.
**Status update (2026-07-10, post-audit):** the actual Milestone 2 build implemented a local-disk mock instead — see the audit's Medium finding M1 in `IMPLEMENTATION_REVIEW.md`. This decision's *intent* (interface shape) still stands; the *implementation* diverged and needs a real S3/R2 swap before deployment.

### 2026-07-10 — YOLO26-pose for person-count pre-check, MediaPipe for keypoints
**Decision:** every video runs a YOLO26-pose person-count pass before MediaPipe extracts keypoints.
**Status update (2026-07-10, post-audit):** the actual build used `yolov8n-pose.pt`, undocumented at the time — see `IMPLEMENTATION_REVIEW.md` Medium finding M2. The person-count *logic* is correct; the model version needs reconciling.

### 2026-07-10 — World landmarks, not image landmarks, for all angle math
**Decision:** `compute_biomechanics` uses MediaPipe's `pose_world_landmarks` exclusively.
**Why:** image-space landmarks are distorted by camera distance and aspect ratio in ways that corrupt angle geometry.
**Status:** confirmed correctly implemented in the actual M2 build.

### 2026-07-10 — `videos` table upgraded from Milestone 1's placeholder
**Decision:** added `pending_upload` status plus diagnostic fields (`person_count_detected`, `detection_rate`, `error_code`, `error_message`, `job_id`, timestamps).
**Why:** the original placeholder had no way to represent an incomplete upload or explain a failure.

### 2026-07-10 — Sagittal-plane accuracy figure revised, not treated as a single fixed number
**Decision:** `docs/SCIENCE_CONSTRAINTS.md` presents a range rather than one precise figure; the system leans on trends and symmetry over absolute values.
**Why:** a newer, movement-specific study found more bias than the general-gait figure originally cited.

### 2026-07-09 — Modular monolith, not microservices
**Decision:** one deployable backend, module folders mirror the original diagram's service boundaries.
**Why:** 12 separately-networked services is 6–12 months of ops work for a student team in 8 weeks.

### 2026-07-09 — PostgreSQL only, no MongoDB/vector DB/data warehouse
**Decision:** single database engine; time-series/vector needs via Postgres extensions if they ever arise.

### 2026-07-09 — No supervised injury prediction
**Decision:** risk output is a cited heuristic score or unsupervised anomaly detection, never a trained "injury probability" claim.
**Why:** no public dataset links video biomechanics to confirmed injury outcomes at usable scale.

### 2026-07-09 — Frontal-plane knee valgus is qualitative only, never a precise angle
**Decision:** encoded structurally via `biomechanical_metrics.confidence`.

### 2026-07-09 — snake_case everywhere, including JSON wire keys
**Decision:** Python, SQL, and JSON response keys are all snake_case.
**Why:** removes a class of bugs from inconsistent camelCase conversion.

### 2026-07-09 — MediaPipe Pose + Ultralytics YOLO, pretrained only
**Decision:** no training a pose model from scratch.

### 2026-07-09 — Rate limiting and formal audit logging deferred to Milestone 4
**Decision:** not built in Milestone 1, deliberately.

### 2026-07-09 — OAuth2 login deferred, JWT-only for v1
**Decision:** email + password + JWT for Milestone 1.

---

## Open questions

- **Storage:** local-disk mock (M2) needs a real S3/R2 swap before any deployment beyond local dev/demo — see `IMPLEMENTATION_REVIEW.md` M1.

### 2026-10-02 - Host-side alembic reads settings, not os.environ
**Decision:** `backend/alembic/env.py` now takes the migration URL from `app.config.settings.database_url_sync` instead of `os.environ.get("DATABASE_URL_SYNC", <container default>)`.
**Why:** `Settings` has `model_config = {"env_file": ".env"}`, so it resolves `backend/.env` for a host run, while compose still wins inside Docker because pydantic-settings gives real env vars priority over `.env`. The old code bypassed settings entirely and fell through to the container hostname `postgres:5432`, making the documented `cd backend && alembic upgrade head` fail with "could not translate host name".

### 2026-10-02 - `BiomechanicsFrame` uses `from_attributes`
**Decision:** added `model_config = {"from_attributes": True}` to `BiomechanicsFrame`, matching `VideoResponse`, `AthleteResponse`, `Notification` and the auth schemas.
**Why:** the router passes raw `BiomechanicalMetric` ORM rows straight into `BiomechanicsResponse`, so without it pydantic raised `model_type` and the endpoint 500'd for every video that had metrics. `tests/test_regressions.py` guards this.

### 2026-10-02 - `puppeteer-core` added as a frontend devDependency
**Decision:** `npm i -D puppeteer-core` only. **Not** `@sparticuz/chromium`.
**Why:** needed to drive a real browser against the live stack for the UI verification STATE.md owed. A full Chrome is already installed on this machine, so the ~50MB AWS-Lambda-specific `@sparticuz/chromium` the `frontend/e2e/README.md` suggests is unnecessary; `puppeteer-core` downloads no browser. Used for local verification only, alongside the pre-existing `frontend/e2e/` harness.

### 2026-10-02 - OPEN: joint-angle conventions differ between metrics and are not labelled
**Question:** `knee_flexion_angle_*` is stored as deviation from full extension (0 = straight), `trunk_lean_angle` as deviation from upright (0 = vertical), but `hip_flexion_angle_*` behaves like a raw included angle (180 = extended, giving ~160-176 deg on clips where the athlete is standing or landing). The results page shows every metric as a bare "Peak N deg".
**Why it matters:** a physiotherapist reading "hip flexion 176 deg" beside "knee flexion 36 deg" is comparing opposite conventions with nothing on screen saying so. This is a false-precision risk, not just a UI nit.
**Needed decision:** either normalise all joint angles to one convention (and name it in the schema + UI), or label the convention per metric. Not guessed - flagged.
**Also observed:** `trunk_lean_angle` still yields p95 = 152.6 deg on `landing_single_leg_drop_soft_landing` (median 16.7 deg), i.e. impossible outliers survive on newly processed clips, so the axis fix corrected the bulk but not every frame.

### 2026-10-02 - OPEN: pre-fix metric rows are still stored in the dev database
**Question:** `squat_sample.mp4` rows were computed before the trunk-lean axis fix and hold `trunk_lean_angle` median 164.4 deg. New clips are correct (medians 6-47 deg).
**Needed decision:** recompute with `?recompute=true` or purge, before any of this data is shown to a user or used to build a baseline. Left in place so the discrepancy stays visible rather than being silently deleted.

### 2026-10-02 - OPEN: risk scoring has never scored real footage
**Question:** leave-one-video-out baselines need >=5 completed videos of one movement type from >=3 athletes. With 9 clips that is unreachable, so every real clip honestly returns HTTP 202 `insufficient_baseline_data`.
**Needed decision:** whether to author/segment enough footage per movement type to exercise the 200 path on real data, or to accept synthetic-data verification for the anomaly scale. Flagged rather than faked by seeding synthetic rows.

### 2026-10-03 — Merging the three forks; what the real-data run changed

Three lines of work had diverged from the 2026-09-30 snapshot: the repo fixes (OAuth, compose, coverage gate, baseline gate),
the frontend rebuild, and the AI-engine rebuild. The engine patch did not apply cleanly (migration `0003` and
`risk_scoring/service.py` collided). Decisions, in the order they mattered:

- **The rebuilt engine replaces the per-frame engine wholesale; the repo's unique guarantees are ported on top.** Two different
  algorithms fixed the same bug (a video scored against its own baseline). Merging them textually would have produced code neither
  author tested, so the rebuild (video-level features, cross-fitted anomaly, tail-only scoring; mutation-tested) won, and these
  survive from the other line: the scored video is never in its own baseline; insufficient baselines store **NULL, not 0.0**;
  an **athlete-diversity floor** (`MIN_BASELINE_ATHLETES`, default 3, counted over the videos actually in the baseline);
  `data_quality` and UUID validation on the API; a 202 body that reports *both* floors (`unit` = videos | athletes).
- **Migration chain** `0001 → 0002 → 0003 (honesty + widen) → 0004 (coverage caveat) → 0005 (videos.analysis, risk_scores.assessment)`.
  Verified on a fresh database, single head, with a downgrade/upgrade round trip.
- **Videos with a `coverage_caveat` never feed a population baseline** (multi-person / partial coverage). The rebuild did not do this; the merge would
  have regressed it silently. Enforced in `_baseline_select`, tested at API level.
- **Slow-motion bug (interaction between two forks).** The coverage gate divided the athlete's track by frames *read*; the rebuilt tracker only
  analyses every `stride`-th frame, so a perfectly tracked 240 fps clip read as 25% covered and was rejected. Denominator is now frames analysed.
- **Engine 2.1: features from a leg that was not reliably visible are excluded from the anomaly comparison** (same 60% floor `score_asymmetry` already
  used). Found on real footage: a clip whose far leg was visible in 13.5% of frames scored 63.6 "high" off three left-leg angles; it now scores 0.0.
  Asymmetry still receives the unfiltered features so it keeps explaining its own reason. Bumping `ENGINE_VERSION` makes stored scores recompute.
- **Hip flexion convention resolved** by the rebuild (0° = extended, shoulder-midpoint trunk axis); the old test that pinned the mismatch was re-pinned.
- **Rebuilt tests were corrected, not the product, where they encoded fantasies**: a 10 px tall athlete, every baseline video from one athlete,
  `mean_value == 0.0` for "unknown", a detection rate sitting exactly on the 40% floor.
- **The rebuild's frontend edits were made against the pre-rebuild UI** and could not be dropped in. The results page was re-implemented in the
  current component library (quality notes, five sub-scores, injury-type cards, rep/gait summary, athlete-aware baseline notice). The frontend never
  displayed the coverage caveat the backend stores; it does now.
- **`static-ffmpeg==2.5.1` never existed on PyPI; pinned to 2.5.** Only a runtime fallback (the Dockerfile installs ffmpeg).
- **Engine 2.2: the score is now a pure function of the data.** The baseline arrives from a `GROUP BY` with no `ORDER BY` and the forest/cross-fit folds
  depend on row order, so the same data could score 0 or 100 depending on the query plan (found because a test passed alone and failed in a full run; 2 of 8
  simulated populations flipped). The baseline is sorted canonically inside `assess_video_anomaly`; `test_score_is_a_pure_function_of_the_data_not_of_row_order` guards it.
- **Scores on fewer than 30 baseline videos are labelled provisional** (`baseline.provisional`, shown on the results page). Default floor stays 10 so a small
  deployment can score at all; ~10% of perfectly normal videos score as strongly anomalous at 10 baseline videos vs ~2% at 30, so **`MIN_BASELINE_VIDEOS=30` is recommended
  for real use.** Not changed unilaterally because it is a product decision with a real cost (more "baseline building" for longer).
- **Test-harness fixes:** the module-global Redis client is reset per test (it was bound to a closed event loop in later tests), and Redis is flushed per test
  (the baseline-recompute debounce key leaked between tests and made a test order-dependent: HTTP 429).
- **Still true:** the product does not predict injury. There are no injury-labelled data, so there is no probability, accuracy or false-positive rate
  to report; the PDF brief's "probability" and its accuracy targets are not met and cannot be without such data. Output is a risk *level* with named drivers.
- **Open:** squat variant (bodyweight vs barbell) and exact camera angle are not baseline dimensions, so a barbell back squat reads "moderate"
  against a mostly-bodyweight population. See `docs/REAL_DATA_VALIDATION.md`.

## 2026-10-05 — Host (non-Docker) runs: four fixes

A native run from a fresh clone failed in four places that Docker and the author's pre-seeded host env hid.
- `DATABASE_URL_SYNC` is derived from `DATABASE_URL` when unset (it was missing from `.env.example`, so `alembic upgrade head` fell back to host `postgres`).
- `Settings` reads `../.env` then `.env`, so the repo-root `.env` the README creates is found when running from `backend/`.
- The arq pool/worker took `REDIS_URL` from `os.environ`, which a `.env` file never populates; it now uses `Settings.redis_url` (video confirm-upload and the worker defaulted to host `redis`).
- `/uploads` was hardcoded (and `makedirs`'d at import, crashing on macOS/Linux non-root). It is now `UPLOAD_DIR` (default `backend/uploads`; compose sets `/uploads`).
- `.env.example` now holds host values (`localhost`); compose still overrides DB/Redis URLs with service names.

- **Docker image uses CPU-only torch** (`--index-url https://download.pytorch.org/whl/cpu`, installed before `requirements.txt`). Inference already runs on CPU; the default Linux PyPI torch pulls several GB of unused CUDA wheels. The model weights themselves are small (`yolov8n-pose.pt`, pose landmarker `.task`) and download on first use. Not rebuilt/verified in the sandbox (no Docker, pytorch.org unreachable). Native Windows/macOS installs already get CPU torch from PyPI.
