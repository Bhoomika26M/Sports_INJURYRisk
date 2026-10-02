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

### 2026-10-02 — Containers get container-correct service URLs; readiness probe added
**Decision:** `docker-compose.yml` gives `backend` and `arq_worker` an `environment:` block (shared via a YAML anchor) that sets `DATABASE_URL`, `DATABASE_URL_SYNC` (host `postgres`, port 5432, credentials from the same `POSTGRES_*` variables the database service uses) and `REDIS_URL` (host `redis`). `environment:` overrides `env_file:`, so the host-side `.env` (`localhost:5433`, `localhost:6379`) is untouched for non-Docker runs. Added `GET /health/ready` (typed, 200/503): `SELECT 1` against Postgres plus a Redis `PING`; `GET /health` stays a static liveness probe.
**Why:** inside a container `localhost` is the container itself, so the backend and worker could not reach Postgres or Redis. The existing `/health` returns `{"status":"healthy"}` without touching either, so it cannot detect this class of fault — verifying the fix "by hitting `/health`" would have passed on the broken configuration. Readiness is what deploy checks should use.
**Verification:** Docker was not available in the environment that made this change, so the stack was **not** brought up. Instead (1) `tests/test_compose_env.py` resolves the effective environment from the real compose file (fails on the original file, passes on the fix) and (2) the real app was run with the compose-resolved environment in a simulated container network (service names resolve; `localhost:5433`/`:6379` empty): original → `/health` 200 but `/health/ready` **503 (database and redis unreachable)**; fixed → `/health/ready` 200. Re-verify with `docker compose up` before relying on it.

### 2026-10-02 — Google OAuth2 is a real authorization-code flow; auth cookies are Secure; middleware reads a non-secret session hint
**Decision:** `GET /auth/google` now returns a 302 to Google with a fresh `state` (also set as a 10-minute httpOnly cookie). `GET /auth/google/callback?code&state` (what Google actually calls) validates `state` FIRST (constant-time compare of query vs cookie; before even acting on `error`), then exchanges the code, runs the existing account-linking logic, sets the refresh token as an **httpOnly, Secure, SameSite=Lax** cookie on a 302 to `FRONTEND_URL/auth/callback`, and clears the state cookie. No token is ever in a URL. The Next.js `/auth/callback` page just waits for `AuthProvider`'s bootstrap (`POST /auth/refresh` → in-memory access token → `/auth/me`) and routes to `/dashboard`. Failures redirect to `/login?error=<stable code>` (`oauth_state_mismatch`, `oauth_denied`, `oauth_code_invalid`, `oauth_email_unverified`, `oauth_account_conflict`, `oauth_account_disabled`, …). The old `POST /auth/google/callback` (JSON body, no `state` check, unreachable by a real Google redirect) is **removed**. New settings: `FRONTEND_URL`, `COOKIE_SECURE` (default true), `GOOGLE_REDIRECT_URI` documented in `.env.example`. All auth cookies are issued through `auth/cookies.py`; the password login/refresh cookies were hard-coded `secure=False` and now follow `COOKIE_SECURE`.
**Hardening added to `handle_google_callback` (linking logic otherwise unchanged):** Google must assert `email_verified` (otherwise an unverified IdP email could claim an existing password account); an account already linked to a *different* Google `sub` is rejected, not silently reused; deactivated accounts cannot sign in via Google. `access_type=offline`/`prompt=consent` were dropped: we never use a Google refresh token, so we should not request one.
**Why a session hint:** the refresh cookie is httpOnly and scoped to `/api/v1/auth`, so the browser **never sends it to `/dashboard` etc.** (verified with RFC 6265 cookie-jar semantics: `Cookie header: None`). The middleware that `frontend/AGENTS.md` requires for route protection therefore redirected every login — password or Google — straight back to `/login`. The frontend now sets a non-secret `session_active=1` cookie at its own origin (set on login/successful bootstrap, cleared on logout/failed refresh); middleware checks that. It is not a token and grants nothing: the API still authorises every request. **Not verified in a real browser in this environment** (see STATE.md).
**Alternatives considered:** widening the refresh cookie to `Path=/` — rejected, sends a long-lived credential to every route and still fails when API and frontend are on different domains; storing state server-side in Redis — rejected, the double-submit httpOnly cookie is the standard stateless CSRF defence and needs no new infrastructure.

### 2026-10-02 — Pose coverage: diagnose why detection was low; accept partial coverage only with an explicit caveat; never measure another person
**Decision:** the 70% floor is **unchanged**. `pose/coverage.py` (pure, unit-tested) classifies a below-floor result as `subject_too_small` (selected athlete < 160 px tall), `multiple_people_subject_unstable` (several people and the athlete followed in < 70% of frames, or tracking unavailable with several people), or `low_detection_quality`; the message states the pixel height, how many people/track IDs were seen, which track was selected, and its coverage. Between 40% and 70% a clip is accepted as **partial coverage** only when the subject is large enough and reliably tracked; it is stored with an explicit `videos.coverage_caveat` (new nullable TEXT, migration `0004`) and surfaced in the API as `risk-score.data_quality`. Multi-person clips at full coverage also get a note naming the analysed track (the selection heuristic is "present in the most frames", which can pick a bystander). Below 40% the video fails. Failures now persist `person_count_detected` and `detection_rate` (both were NULL on every failed video). Videos with a caveat are scored for their own athlete but **never contribute to a population baseline**.
**Also fixed (root cause of "tracker picked the wrong one"):** when tracking was active but the selected athlete was absent from a frame, the pipeline ran full-frame pose, which in a group shot measures *whichever other person* MediaPipe finds and silently mixes identities into the athlete's metrics. For multi-person clips those frames are now skipped (`full_frame_fallback=False`), so the detection rate means "frames where the selected athlete was measured". Single-person and untracked clips keep the full-frame fallback.
**Why / limits:** the 160 px, 40%, and "10% of frames = a person" thresholds are conservative heuristics, **not validated cut-offs**; they gate wording and the partial fallback, never raise a score. `person_count_detected` keeps its meaning (max people in any single frame) and can be inflated by a one-frame duplicate detection; `tracks_seen`/substantive tracks are reported separately in messages. The two real internet clips (`test-assets/internet-clips/`) were **not available in this environment** (not in the repo zip, no network route to YouTube), so this was verified with unit tests plus `process_video` integration tests using fake YOLO/MediaPipe passes — not on real footage.

### 2026-10-02 — More findings (reported, not changed unless stated)
- **Open — schema drift found by `alembic check` (pre-existing, not caused by this work):** `ReportExport` (`report_exports`) is specified in SCHEMA.md and defined as a model but has **no migration** (nothing reads or writes it, so no runtime impact today; tests use `create_all` and cannot see it); several indexes are named `ix_*` in the models but `idx_*` in migrations; `movement_baselines` has no unique constraint in the model although the migration has one; `recommendations.priority` is `SMALLINT` in the migration and `Integer` in the model. The DoD check "`\dt` matches SCHEMA.md exactly" would currently fail for `report_exports`.
- **Open, unverified — `static-ffmpeg==2.5.1` did not resolve** when running `pip install -r backend/requirements.txt` in the environment that made this change (the index offered 2.5, 2.7, 2.8, … but no 2.5.1; 2.5 was installed instead to proceed). This may be a lagging package mirror rather than a bad pin, but if 2.5.1 does not exist on PyPI the Docker image build fails. Check `pip index versions static-ffmpeg` on a normal network before relying on the pin; the pin was left unchanged.
- **Open — existing stored risk scores keep their old values.** `GET /videos/{id}/risk-score` returns the stored row unless `?recompute=true`. Scores computed under the old self-referential baseline and percentile scale are not invalidated; recompute them after deploying this change.
- **Open — high/critical risk notifications fan out to every staff user** (all coaches, physiotherapists, scientists, admins), not just those assigned to the athlete.
- **Open question — `hip_flexion_angle` convention.** It returns the interior shoulder-hip-knee angle (≈180° standing, falling with flexion), while its docstring says 0° = leg extended and larger = more flexed. Direction-agnostic anomaly scoring is unaffected and nothing else consumes it, so it was not changed, but the metric label is misleading. Needs a decision before the value is shown to clinicians.
- **Y-axis audit (trunk-lean fix `0e7d137`):** `trunk_lean_angle` is the only calculation that depends on the vertical axis sign. `joint_angle`, `knee_flexion_angle` and `hip_flexion_angle` are rotation-invariant vertex angles; throwing `trunk_rotation` projects onto x–z (sign-agnostic); `knee_valgus_flag` uses the x (lateral) axis in frontal views only. Checked against the documented real-landmark orientation (head y≈−0.6, hip≈0, ankle≈+0.75) with synthetic poses built from it, **not** against stored real landmarks (no database or clip was available here).

### 2026-10-02 — Defects found while fixing the listed ones (reported, not in the handoff)
- **`biomechanical_metrics.confidence` was `VARCHAR(10)`; the structural tier `'qualitative'` is 11 characters.** Any frontal/"other"-view video (knee-valgus flags) would fail to store its qualitative metrics (`StringDataRightTruncationError`, reproduced). Migration 0002 had only widened `movement_metrics`. **Fixed** in migration `0003` (→ `VARCHAR(20)`), model and SCHEMA.md; regression test `test_qualitative_confidence_tier_can_be_stored`.
- **Malformed UUID path IDs returned HTTP 500** (unhandled `DBAPIError`) instead of 422. **Fixed on the two risk-scoring endpoints** via `core.deps.UuidPath`. **Still open:** every other route that takes an ID path parameter (`athletes`, `videos`, `reports`) has the same pattern.
- **The anomaly model cache was keyed `movement:metric` only.** Once baselines became per-video (leave-one-out) that key would have served a model fitted on a baseline containing video X to X. Cache is now keyed by video id + baseline content hash and bounded to 32 entries.
- **`scripts/e2e_video_check.py` asserted the self-referential baseline was "the correct outcome"** (a single video scoring 200 against its own frames). Fixed together with the baseline change.
- **Open, not changed — `anomaly_scores` table is never written.** `AnomalyScore` is defined and read by analytics, but no code path inserts rows, so the scientist dashboard's anomaly distribution is always empty. Needs a decision on granularity (the table has no `metric_name` column) before wiring.

### 2026-10-02 — Baseline sufficiency counts videos and athletes; baselines are leave-one-video-out; insufficient baselines store NULL
**Decision:** (1) `risk_scoring/constants.py` replaces `MIN_BASELINE_SAMPLES = 10` with three unit-named floors, all counted **excluding the video being scored**: `MIN_BASELINE_VIDEOS = 5` distinct completed videos, `MIN_BASELINE_ATHLETES = 3` distinct athletes, `MIN_BASELINE_FRAMES = 100` validated frame rows per metric (estimator floor only). (2) `baselines.fetch_baseline(db, movement_type, metric_name, *, exclude_video_id)` is the only baseline query; `exclude_video_id` is keyword-only with no default, so a caller cannot forget it. `None` is an explicit "no video under evaluation" used only by the stored descriptive population baseline, which is never used to score a member video. Rows are ordered deterministically and non-finite values are dropped before counting. (3) The anomaly model cache key now includes the video id plus a content hash of the baseline array (and the cache is bounded), so a model fitted on a baseline that contained video X can never be served to X. (4) `movement_baselines.mean_value`/`std_dev` are now NULLable and stored as NULL when insufficient (was a fabricated `0.0 ± 0.0`); new `video_count` and `athlete_count` columns make the row state its own unit (`sample_size` is per-metric frames). Migration `0003` also NULLs every pre-existing baseline row (computed under the old gate) — rebuild with `POST /baselines/recompute`. (5) The HTTP 202 body is now the typed `InsufficientBaselineResponse`: `status`, `metric_name`, `unit` (`videos`|`athletes`|`frames`), `have`, `need`, `coverage` (all three units), `message`. **Contract change:** `have`/`need` previously counted frame rows; they now count the named `unit`, and `have` excludes the scored video.
**Why:** a single 7-second clip of one athlete produced 426 validated rows per metric, so "10 samples" was met instantly and the guard that exists to stop fabricated scores effectively never fired. Separately the athlete's own frames supplied most of the "population" they were compared against, damping deviation toward zero (leakage). `0.0 ± 0.0` is a plausible wrong number; NULL is "we don't know". The floors 5 / 3 / 100 are conventions, not statistically derived: they are the point below which the "population" is one or two people. They are floors against fabrication, not evidence of adequacy, and should be raised as real data accrues.
**Alternatives considered:** counting athletes only — rejected, a single athlete's many sessions still under-represent variation but videos are the unit the model actually fits over; a caller-side `if video.id != x` filter — rejected, exactly the kind of check that gets dropped in the next refactor; keeping the previous good value on insufficient recompute plus a `sufficient` flag — rejected, stale numbers from a different population are worse than "unknown".

### 2026-10-02 — Anomaly score is anchored at 0: Isolation Forest decides "outside the envelope", baseline-robust distance decides "how far"
**Decision:** `risk_scoring/anomaly.py::compute_anomaly_scores` now returns, per frame: 0 if Isolation Forest scores the frame at least as normal as the baseline's own 5th-percentile frame; otherwise `100 * (1 - 2^(-d/2))`, where `d` is the distance (in baseline robust SDs, `1.4826 * MAD` per feature) from the frame to the nearest of the 95% most-normal baseline frames. Anchors: 0 at the envelope edge, 50 at 2 SD outside, 75 at 4 SD, 87.5 at 6 SD, never 100. Fully deterministic (`random_state=42`). Direction is unchanged (higher = more anomalous). `scoring.py` formula is unchanged (`min(70, 0.7 * mean frame score)`); the `detail` string now states the scale and the baseline composition. Category cut-points **kept at low ≤25 / moderate ≤50 / high ≤75 / critical >75**; recommendation triggers on the anomaly component moved from >40 / >60 to >25 / >50 points so they track the moderate / high band floors.
**Why:** measured with the repo's own function on production-scale data (degrees, baseline N(90, 8), n=426): the old percentile-of-baseline scale gave in-distribution frames a mean percentile of ~54 (≈38 of 70 points) because the baseline's median frame is the 50th percentile by construction, so a perfectly normal athlete carried a large constant floor that is not risk. It also saturated: x4 and x8 deviations scored ~86 vs ~94 percentile. New scale, same data, mean over 10 seeds: in-distribution 0.6, scale ×2/×4/×8 = 9 / 31 / 57, mean shifted by 2/4/8 SD = 11 / 47 / 87, and worst-case movement across baseline sizes n∈{60,200,426,1200} is 7.5 points (old: ~14 even in-distribution). **Finding that shaped the design:** Isolation Forest's own decision score saturates for any point outside the training range (median decision score −0.275 for both +4 SD and +8 SD at n=426), so no transform of its output alone can separate "clear" from "extreme" — the forest is used for the in/out decision (and handles multi-modal baselines such as a squat's standing/bottom modes) while geometry supplies magnitude. Cut-points: there is no outcome data to recalibrate against (AGENTS.md law), so 25/50/75 are conventional quarter bands of a bounded index, not risk probabilities. They are kept because they were written assuming 0 = no anomaly, which is now true. The movement component caps at 70, so "critical" cannot be reached by movement pattern alone — it needs corroborating flags; that is deliberate.
**Alternatives considered:** rescaling the decision function by its MAD — rejected, the baseline-score MAD varies ~2× across n (0.027 at n=60 → 0.012 at n=1200) and the score still saturates; a median/MAD z-score on the raw metric — rejected, wrong for multi-modal baselines; subtracting 50 from the old percentile — rejected, still saturates; changing the `anomaly_scores.method` value — rejected, the locked schema pins `isolation_forest`.
**Known limits (not changed):** ~5% of in-distribution frames register a small non-zero score by construction; a multi-modal baseline has a wide robust SD so within-mode deviations are scored leniently (conservative); the composite still takes the mean over frames pooled across metrics, which dilutes a short, severe deviation (e.g. only the bottom of a squat) — revisit with real data.

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
