# STATE.md

The single source of truth for "what actually exists right now." Update this after every verified task — not from memory, from actually re-running the checks below against the real repo. If this file and reality disagree, reality wins; fix this file.

**Last verified:** 2026-10-04 (Host verification, native PostgreSQL 17 + local runtime verification, Alembic 0001→0005, backend & frontend live servers running, automated browser dashboard login verified)

**Verified on 2026-10-04 (Live local stack, native Postgres 17 on :5432, Uvicorn on :8000, Next.js on :3000):**
- **Database & Migrations**: Local PostgreSQL 17 active on port 5432; `injury_detection` database created; `injury_user` role provisioned; all 5 Alembic migrations (`0001` → `0005`) executed cleanly, establishing all 17 schema tables including `videos.analysis` and `risk_scores.assessment`.
- **Database Seeding**: Executed `python -m app.seed`, creating 5 demo users across all roles (`coach@demo.com`, `athlete@demo.com`, `physio@demo.com`, `scientist@demo.com`, `admin@demo.com`), 3 athletes, injury records, training loads, and 7 movement types.
- **FastAPI Backend**: Uvicorn running live on `http://localhost:8000`. `GET /health` returns HTTP 200 `{"status":"healthy"}`. OpenAPI docs verified at `/docs`. Auth endpoint `POST /api/v1/auth/login` and data endpoint `GET /api/v1/athletes` verified with real JWT Bearer tokens.
- **Next.js Frontend**: Next.js 16 running live on `http://localhost:3000` (HTTP 200).
- **Automated Browser Flow**: Verified via automated browser subagent: navigated to `http://localhost:3000/login`, authenticated with `coach@demo.com`, redirected to `http://localhost:3000/dashboard/coach`, and rendered the live coach dashboard with "Hi Sarah", team summary statistics, and all seeded athletes from PostgreSQL.
- **Process & Named Pipe Diagnostics**: Diagnosed root cause of earlier Docker CLI hangs: orphaned `com.docker.backend` and stale CLI processes held Windows named pipes and ports from prior sessions; terminated zombies and documented native host pathway when non-elevated user permissions restrict starting `com.docker.service`.

**Previously verified on 2026-10-03 (merge of the three parallel lines of work, then a real-data and end-to-end run):**
- `alembic upgrade head` on a fresh database: `0001 → 0005`, single head, every column from all three lines present, `0005 → 0003 → head` round trip clean.
- `pytest` → ****384 passed, 0 failed, 0 skipped** (3 min 58 s)** (see `docs/DECISIONS.md` 2026-10-03 for what the merge changed and why).
- Frontend: `tsc --noEmit` clean, `eslint --max-warnings=0` clean, `next build` compiles all 21 page routes. *The sandbox cannot reach Google Fonts, so the build was run with Next's font mock; the code compiled, the font fetch is a network limit.*
- **True end-to-end over HTTP** (`backend/scripts/e2e_http_check.py`): real uvicorn + a separate `arq` worker process. Login → create athlete → refusals (bad camera view 422, malformed id 422, no token 401, a text file renamed `.mp4` rejected by ffprobe at confirm) → real upload via the local-storage PUT → `confirm-upload` → worker runs YOLO + MediaPipe (39 s for a 6 s clip) → biomechanics → **risk score 200 against a baseline of 11 real videos from 11 athletes** → all five components, the five PDF sub-scores, six injury categories → recommendations. *Run with `MIN_BASELINE_VIDEOS=8`: the repo's real corpus is one clip short of the production floor (below).*
- **Browser, against that live API** (`frontend/e2e/part3_results.mjs`, headless Chrome): 5/5 — login, scored results page (five sub-scores, injury-type cards, no console errors), a two-person clip shows its coverage caveat and a "provisional" warning, a front-view clip explains why it has no score, a poor-visibility clip shows its warning. Screenshot inspected.
- **Real footage** (`docs/REAL_DATA_VALIDATION.md`, `docs/real-data/`): 24 clips from public GitHub repos through the real pipeline — **19 completed, 5 refused by the quality gates** (all five unusable). Scoring under the production floors and under a labelled demo floor of 8 videos is in that report.

**Bugs found by the merge or the real-data run, all fixed with regression tests:** caveated (multi-person / partial) videos could enter population baselines; the coverage gate rejected perfectly tracked slow-motion clips (frames read vs frames analysed); a leg visible in 13.5% of frames drove a 63.6 "high" score (engine 2.1); **the score depended on database row order** (a normal video flipped between 0 and 100; fixed by canonical ordering, engine 2.2); baselines stored a fabricated `0.0 ± 0.0`; the frontend never showed the coverage caveat; `static-ffmpeg==2.5.1` does not exist; the test harness reused a Redis client bound to a closed event loop and let Redis state (the recompute debounce key) leak between tests.

**Real-data headline (read the report before quoting it):** the squat baseline has 9 other usable videos against a floor of 10 — **one clean, side-on, single-person squat from a new person closes it**. Running and jumping have none. Front/rear views correctly return "cannot score". The engine only flags large deviations (a 2-sigma shift is never flagged; ~half of 4-sigma shifts are caught at 30 videos), and with the 10-video floor ~10% of perfectly normal videos still score as strongly anomalous (~2% at 30 videos) — so scores on fewer than 30 baseline videos are labelled **provisional** in the API and the UI, and `MIN_BASELINE_VIDEOS=30` is recommended beyond a demo (`tests/test_anomaly_calibration.py`).

**Not verified (be honest about these):**
- **Accuracy.** No ground truth for joint angles and **no injury labels**. "Completed" means it passed the gates and produced metrics. Nothing here estimates injury probability, accuracy or a false-positive rate; the PDF brief's probability and accuracy targets are **not met** and cannot be without labelled data.
- **Squat variant / camera angle are not baseline dimensions.** Barbell back squats read "moderate" against a mostly bodyweight population.
- `squat_proper_form` (one woman, tracked in 66% of frames) was refused by the 70% floor; a second person registered somewhere. Possible over-rejection, not investigated.
- The 56 browser checks in `frontend/e2e/part1.mjs` / `part2.mjs` (which simulate the ML worker) were **not re-run** on the merged tree.
- A full browser-driven upload (file chooser → results). The upload path was exercised over HTTP, the results pages in a browser, but not the upload *form* in a browser.
- Google OAuth against real Google (no client credentials); `docker compose up` (not run); S3/R2 still mocked to local disk; deploy still owed.
- Existing stored scores from before engine 2.2 recompute on next read (`engine_version` mismatch); nothing else invalidates them.

---

## Current status

**Backend + AI engine: merged, verified at unit / DB / ASGI / live-HTTP / real-footage level.** Schema `0001_init` → `0002_widen_confidence` → `0003_baseline_honesty_and_confidence_width` → `0004_video_coverage_caveat` → `0005_analysis_and_assessment`; 7-movement registry seeded. The engine is the video-level, cross-fitted, tail-only design (`ENGINE_VERSION = "2.2"`): five weighted components, the five sub-scores the brief asks for, per-injury-type risk levels, and an athlete-diverse baseline gate. It reports risk **levels with named drivers**, never an injury probability.

**Frontend — rebuilt, adopted and merged; build compiles and type-checks (21 page routes).** Component library in `src/components/`; the results page now shows quality/coverage notes, the five sub-scores, injury-type cards and rep/gait summaries.

| Milestone | Modules | Status |
|---|---|---|
| M1 — auth, athletes, env setup | 1, 2 | complete (verified; Google flow verified with a faked Google only) |
| M2 — video, pose, biomechanics | 3, 4, 5 | complete; **verified on 24 real clips** (accuracy of angles not verifiable without ground truth) |
| M3 — risk scoring, recommendations | 6, 7, 8, 9 | complete; verified end to end on real footage; squat baseline one clip short of the production floor
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
