# STATE.md

The single source of truth for "what actually exists right now." Update this after every verified task — not from memory, from actually re-running the checks below against the real repo. If this file and reality disagree, reality wins; fix this file.

**Last verified:** 2026-10-02
**Verified by (this session, real runs):** native PostgreSQL 16.15 + Redis (Docker was **not** available), `alembic upgrade head` clean from an empty database (0001 → 0004) with 0003/0004 downgrade/upgrade round trips, `python -m app.seed` run twice (idempotent; 7 users, 7 movement types), `pytest tests/` → **189 passed, 0 failed, 0 skipped**, a live `uvicorn` answering `/health` 200 and `/health/ready` 200, `npm run build` → compiled + type-checked, 17 routes.
**Caveats on those runs:** (1) `ultralytics` was replaced by a stub that raises if YOLO is instantiated (torch does not fit in that sandbox); nothing in the test suite runs real YOLO. (2) The frontend build was run with the `next/font/google` import temporarily swapped for a system font (Google Fonts is unreachable there) and then reverted — an unmodified build was not run. (3) `static-ffmpeg==2.5.1` did not resolve from that environment's package index (see DECISIONS.md open items).

---

## Current status

**Backend + API complete and verified at unit / DB / ASGI / live-HTTP level.** Schema `0001_init` → `0002_widen_confidence` → `0003_baseline_honesty_and_confidence_width` → `0004_video_coverage_caveat`; 7-movement registry seeded; JWT + a real Google OAuth2 authorization-code flow (state-validated, httpOnly refresh cookie; Google itself faked in tests); YOLO tracking with main-subject selection and pose-coverage diagnostics; 7 movement-specific biomechanics calculators; Isolation Forest anomaly scoring on a **0-anchored** scale, scored against a **leave-one-video-out** baseline that must contain ≥5 videos from ≥3 athletes (else HTTP 202 `insufficient_baseline_data`); transparent composite scoring (anomaly / asymmetry / prior-injury / ACWR / fatigue); rule-based recommendations; analytics; notifications; PDF/Excel/CSV exports with `methodology_note`; `/health` (liveness) and `/health/ready` (Postgres + Redis).

**Frontend — all pages built; build compiles and type-checks (17 routes).** Includes the Google callback route (`/auth/callback`), login error messages for failed Google sign-in, and data-quality banners for partial-coverage / multi-person videos.

**Not yet verified (be honest about these):**
- **End-to-end video processing on a real clip was NOT re-run in this session** (no clip in the repo archive, no MediaPipe pose model reachable, no YOLO). A previous session reported 213/213 frames, 1065 metrics and a risk score of 44.7 / moderate; **that score is obsolete** — it predates the trunk-lean fix, the leave-one-out baseline and the 0-anchored scale. On a database holding only that one clip the endpoint now correctly returns **202**, not a score. `scripts/e2e_video_check.py` handles both outcomes and must be re-run on a machine with the clip and model weights.
- **Real multi-person clips** (`test-assets/internet-clips/7a6W56OeU8w.mp4`, `Px4cyTAHrWc.mp4`) were not available. The coverage diagnostics are verified by unit tests and by `process_video` integration tests with fake YOLO / MediaPipe passes, not on real footage. The 160 px / 40% / 10%-of-frames thresholds are unvalidated heuristics.
- **Google OAuth against real Google, and any real-browser session** (including the new `session_active` middleware hint): untested. Needs real client credentials and a manual browser pass.
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
