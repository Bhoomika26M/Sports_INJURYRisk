# STATE.md

The single source of truth for "what actually exists right now." Update this after every verified task — not from memory, from actually re-running the checks below against the real repo. If this file and reality disagree, reality wins; fix this file.

**Last verified:** 2026-10-02
**Verified by (2026-10-02, real runs):** docker compose postgres+redis healthy on 5433/6379; `alembic upgrade head` clean (single head `0004`); `pytest tests/` → **191 passed, 0 failed, 0 skipped**; **all 9 clips in `/data` processed end-to-end with real YOLO 8.4.166 + real MediaPipe** (6 completed, 3 correctly rejected); UI verified in headless Chrome against the live stack — login, role-routed dashboard, `/videos`, `/videos/{id}/results` all render real data.
**Two bugs found and fixed this session:**
1. `backend/alembic/env.py` read `DATABASE_URL_SYNC` from `os.environ` instead of app settings, so a **host-side `alembic upgrade head` silently fell back to the container hostname `postgres:5432`** and failed with "could not translate host name". It now uses `settings.database_url_sync`, which honours `backend/.env` on the host and the compose-exported env var in Docker.
2. `BiomechanicsFrame` was missing `model_config = {"from_attributes": True}` (the convention already used by `VideoResponse`, `AthleteResponse`, `Notification` and auth schemas), so **`GET /videos/{id}/biomechanics` returned 500 for any video that had metrics**. Caught by `tests/test_regressions.py::test_biomechanics_endpoint_serializes_stored_frames`, which was failing. Now 191/191.

**Real-clip results (`/data`, all 9 processed with real models — the run STATE.md previously said was owed):**

| Movement | Clip | Detection | Outcome |
|---|---|---|---|
| squatting | barbell_back_squat_side_view | 94.4% | completed, 743 frames, 3,715 metrics |
| landing | single_leg_drop_soft_landing | 97.5% | completed, 272 frames |
| landing | one_foot_landing_pivot | 93.0% | completed, 348 frames (6 persons max) |
| jumping | box_jump_demo (3840x2026 AV1) | 100% | completed, 235 frames |
| throwing | shot_put_slow_motion | 100% | completed, 767 frames |
| cutting | aquabag_punch_cod | 84.4% | completed, 577 frames |
| running | running_form_side_view | 30.9% | **rejected** `multiple_people_subject_unstable` |
| cutting | 180_cut_mechanics | 41.9% | **rejected** `multiple_people_subject_unstable` |
| sprinting | sprint_speed_drills | 14.9% | **rejected** `multiple_people_subject_unstable` |

The three rejections are **correct behaviour**, not failures: each clip has 2-6 people in frame and the selected athlete could not be tracked in >=70% of frames, so the pipeline refuses to measure rather than substituting another person. This is the first validation of the 70% / 160px / track-stability thresholds on real footage — previously only covered by unit tests with fake YOLO/MediaPipe.

**Open data-quality findings (not fixed — see DECISIONS.md):**
- **Angle conventions are inconsistent between metrics.** `knee_flexion_angle_*` is reported as deviation from full extension (0 = straight, deep squat ~120), `trunk_lean_angle` as deviation from upright (0 = vertical), but `hip_flexion_angle_*` reads ~160-176 deg on clips where the athlete is standing or landing (i.e. it is a raw included angle where 180 = extended). The results page renders all three as a bare "Peak N°", so a physio comparing "hip 176°" with "knee 36°" is comparing opposite conventions with nothing on screen saying so.
- **`trunk_lean_angle` still produces impossible outliers** on newly processed clips: `landing_single_leg_drop_soft_landing` has median 16.7 deg but p95 **152.6 deg**.
- **Stale pre-fix rows remain in the database.** `squat_sample.mp4` was processed *before* the trunk-lean axis fix and stores `trunk_lean_angle` median **164.4 deg**. New clips are fine (medians 6-47 deg), which confirms the axis fix worked, but the old rows must be recomputed (`?recompute=true`) or purged before any of this data is shown to a user.

**Still not verified:**
- **Google OAuth against real Google**, and the OAuth browser landing: untested (no client credentials).
- **Risk scoring has never returned a 200 on real footage.** Baselines require >=5 completed videos of the same movement type from >=3 athletes; the database cannot satisfy this with 9 clips. Every real clip correctly returns HTTP 202 `insufficient_baseline_data` (e.g. "0 of 5 videos"). The 0-anchored anomaly scale is still only verified on synthetic data.
- **Full HTTP upload path** (`/upload-url` → PUT → `/confirm-upload` → arq worker enqueue) is not yet exercised; the 9 clips were run through `scripts/e2e_video_check.py`, which calls the real `process_video` coroutine directly and inserts the `Video` row itself, bypassing the upload endpoint and the Redis/arq hop.
- S3/R2 swap still mocked to local disk. Deploy still owed.

---

## Current status

**Backend + API complete and verified at unit / DB / ASGI / live-HTTP level.** Schema `0001_init` → `0002_widen_confidence` → `0003_baseline_honesty_and_confidence_width` → `0004_video_coverage_caveat`; 7-movement registry seeded; JWT + a real Google OAuth2 authorization-code flow (state-validated, httpOnly refresh cookie; Google itself faked in tests); YOLO tracking with main-subject selection and pose-coverage diagnostics; 7 movement-specific biomechanics calculators; Isolation Forest anomaly scoring on a **0-anchored** scale, scored against a **leave-one-video-out** baseline that must contain ≥5 videos from ≥3 athletes (else HTTP 202 `insufficient_baseline_data`); transparent composite scoring (anomaly / asymmetry / prior-injury / ACWR / fatigue); rule-based recommendations; analytics; notifications; PDF/Excel/CSV exports with `methodology_note`; `/health` (liveness) and `/health/ready` (Postgres + Redis).

**Frontend — rebuilt and adopted; build compiles and type-checks (20 routes).** The audited frontend rebuild (`docs/FRONTEND_AUDIT.md`) was adopted wholesale: a real component library (`src/components/`, 18 components), `lib/{format,hooks,nav,providers,session,types}.ts`, the previously missing `/videos` library, a 404 page, an error boundary, mobile bottom-nav, toasts/dialogs, and `@tanstack/react-query` as `frontend/AGENTS.md` requires. Its 10 documented frontend bugs (login 307 loop, empty upload dropdowns, 401 uploads, hard-coded 0% progress, unauthenticated media/PDF/Excel, no-op logout, no mobile nav, dead links) and its backend `select`-import 500 are fixed. The Google callback route (`/auth/callback`), login error messages for failed Google sign-in, and data-quality banners for partial-coverage / multi-person videos are retained.

**Not yet verified (be honest about these):**
- **End-to-end video processing on a real clip was NOT re-run in this session** (no clip in the repo archive, no MediaPipe pose model reachable, no YOLO). A previous session reported 213/213 frames, 1065 metrics and a risk score of 44.7 / moderate; **that score is obsolete** — it predates the trunk-lean fix, the leave-one-out baseline and the 0-anchored scale. On a database holding only that one clip the endpoint now correctly returns **202**, not a score. `scripts/e2e_video_check.py` handles both outcomes and must be re-run on a machine with the clip and model weights.
- **Real multi-person clips** (`test-assets/internet-clips/7a6W56OeU8w.mp4`, `Px4cyTAHrWc.mp4`) were not available. The coverage diagnostics are verified by unit tests and by `process_video` integration tests with fake YOLO / MediaPipe passes, not on real footage. The 160 px / 40% / 10%-of-frames thresholds are unvalidated heuristics.
- **Google OAuth against real Google, and any real-browser session** (including the `session_hint` middleware hint): untested. Needs real client credentials and a manual browser pass.
- **`docker compose up`** was not run. The container-URL fix is verified by resolving the compose file's effective environment and by running the app in a simulated container network (DECISIONS.md, container-URLs entry).
- Existing stored risk scores computed under the old calibration are not invalidated; use `?recompute=true`.
- S3/R2 swap still mocked to local disk.

| Milestone | Modules | Status |
|---|---|---|
| M1 — auth, athletes, env setup | 1, 2 | complete (verified; Google flow verified with a faked Google only) |
| M2 — video, pose, biomechanics | 3, 4, 5 | complete (verified at unit / DB level; real-clip run owed) |
| M3 — risk scoring, recommendations | 6, 7, 8, 9 | complete (verified; calibration measured on synthetic production-scale data, not real athletes) |
| M4 — dashboards, notifications, reports, deploy | 10, 11, 12, 13 | complete except deploy (verified: build + API level, no live deploy) |

---

## Reusable Definition-of-Done template

Copy this checklist for every new task. A task is done only when every relevant box has been checked by **actually running the command**, not by reasoning about the code.

```
### Task: <description> — Milestone <N>

Environment
- [ ] `docker compose up --build` — zero errors from a clean state
- [ ] `docker compose ps` — all relevant services healthy

Database (if schema touched)
- [ ] Migration runs clean: `alembic upgrade head`
- [ ] `psql $DATABASE_URL -c '\dt'` matches /docs/SCHEMA.md exactly for tables touched
- [ ] `psql $DATABASE_URL -c '\d <table>'` matches column-for-column

API (if endpoints touched)
- [ ] Happy path verified via curl/httpx against the real running server
- [ ] Auth-failure case returns 401/403 as specified, not a token or 500
- [ ] Validation-failure case returns 422, not a crash
- [ ] Response shape matches /docs/API_CONVENTIONS.md exactly

Frontend (if UI touched)
- [ ] `npm run build` — zero type errors
- [ ] Manually exercised in a real browser against the real backend, not a mock

Code hygiene
- [ ] Zero TODO/FIXME/pass-only stubs in anything claimed complete
- [ ] Zero commented-out test code
- [ ] `pytest` (backend) fully green, zero skipped/xfail, for the modules touched

Documentation
- [ ] This file (STATE.md) updated to reflect the new reality
- [ ] Any new architectural choice logged in /docs/DECISIONS.md
```

---

## Update protocol

1. Finish a task and run its full DoD checklist above, for real.
2. Update the status table at the top of this file.
3. If you made a decision not already covered in `/docs/DECISIONS.md`, log it there in the same change.
4. If you hit something genuinely ambiguous, add it to `/docs/DECISIONS.md` §Open Questions rather than guessing silently.

Never edit this file to describe intended future work — it describes only what's been verified to exist right now.
