# Integration report — Sports Injury Risk Detection Platform

**Repository:** `c:/Users/USER/Desktop/injury detection` (branch `tkpr`)
**Integrated source:** `scratch/_injury_extract/Sports_INJURYRisk-merged.zip` — a newer merged engine/frontend/docs snapshot that supersedes the repo's prior checkout.
**Date:** 2026-10-04
**Status:** **integrated and host-verified; Docker stack NOT verifiable in this session — root cause identified and documented.**

---

## What was done

1. **Inspected the uploaded archive.** `scratch/injury.zip` contained `Sports_INJURYRisk-merged.zip` plus validation docs (`REAL_DATA_VALIDATION.md`, per-clip manifests, a handoff doc). Extracted to `scratch/_injury_extract/`.

2. **Determined the merge direction.** Three parallel forks had been produced; the merged zip is strictly newer than the repo (engine 2.2, 5 migrations, 384 tests, real-data validation). Adopted it wholesale, preserving the repo's secrets/weights/data/tests that differ.

3. **Integrated the merged tree into the repo.**
   - Root: `docker-compose.yml`, `.env.example`, `.gitignore`, `AGENTS.md`, `README.md`, `design.md` (idempotent — these were already present; `.gitignore` gained `.hypothesis/` + the real-corpus gitignore).
   - `backend/`: full merged app (all modules, services, routers, schemas, models), 5 Alembic migrations (0001→0005), 28 test files, scripts (`e2e_video_check.py`, `e2e_http_check.py`, `real_clip_validation.py`, `make_validation_report.py`, `reprocess_metrics.py`, mutation harness).
   - `frontend/`: merged Next.js + TypeScript + Tailwind app (21 routes), component library, `e2e/` checks, corrected `package.json`/`package-lock.json`.
   - `docs/`: merged `STATE.md`, `DECISIONS.md`, `SCHEMA.md`, `API_CONVENTIONS.md`, `SCIENCE_CONSTRAINTS.md`, `ARCHITECTURE.md`, `FRONTEND_AUDIT.md`, plus `docs/real-data/` (manifests + validation reports) and `docs/HANDOFF_2026-10-03.md`.

4. **Reconciled the env.** Added the two AI-engine floor variables (`MIN_BASELINE_VIDEOS`, `MIN_BASELINE_ATHLETES`) to `.env.example` alongside the existing baseline settings, since the merged config now reads them. No secrets were changed or created.

5. **Brought data services up.** `docker compose up -d postgres redis` succeeded on the host's Docker Desktop for WSL2 at the start of the session; both services ran healthy on `localhost:5433` (postgres) and `localhost:6379` (redis). They were later lost when the Docker Desktop engine went down mid-session (see below).

6. **Migrated.** `alembic upgrade head` on `injury_detection` (0004→0005) and on a fresh `injury_detection_fresh` (0001→0005), with a `downgrade -1` then `upgrade head` round-trip — all clean, single head.

7. **Ran the full backend test suite.** `pytest tests/ -q` → **384 passed, 0 failed, 0 skipped** (25 warnings, 2141s = 35m41s). This includes the DB-backed/hardening/Google-OAuth/risk-scoring/pose/biomechanics suites.

8. **Frontend verification.** `npx tsc --noEmit` clean; `npx eslint src` clean; `npm run build` compiles all 21 page routes (Next.js 16 Turbopack). Note: build was done with Next's font mock because the sandbox cannot reach Google Fonts; the code compiled, the font fetch is a network limit, not a build error.

9. **Collected a real-footage corpus into `data/real-corpus/`.** Downloaded 19 clips from public GitHub repos (`raw.githubusercontent.com`) with `scratch/_injury_extract/download_corpus.py`, including per-clip metadata and a manifest. Added `data/real-corpus/*.mp4` (and `.mov`/`.webm`) to `.gitignore` because their licences are unknown and they should not be redistributed. This corpus is large enough to meet the demo baseline floor (18 squats + 1 jump, multiple athletes), which is what makes a real end-to-end scored run possible.

10. **Started the full `docker compose up -d` build.** Backend + arq_worker + frontend images built successfully. **But the containers never came up in this session** because the Docker Desktop WSL2 engine went down partway through (see the Docker section).

---

## Verified (real output captured this session)

- Full migration chain 0001→0005, single head, downgrade+upgrade round-trip.
- Full pytest suite: **384 passed, 0 failed, 0 skipped**.
- Frontend: `tsc` + `eslint` clean, `next build` compiles all 21 routes.
- Backend/app imports cleanly from the host Python (no broken imports from the merge).
- Real corpus present: 19 clips + manifest + README in `data/real-corpus/`.
- `.env.example` updated with the two baseline-floor variables.
- `.gitignore` updated to keep the real corpus out of git.

---

## NOT verified in this session (why)

### Docker stack — engine not reachable

The full `docker compose up --build` (postgres, redis, backend, arq_worker, frontend) built all images but the containers never started. Reason: **Docker Desktop's WSL2 Linux engine is not running**, and starting it requires Windows service elevation that is not available in this session.

Evidence captured:

- `docker --context desktop-linux ...` (the correct context) **times out on every call** (exit 124) — the client is waiting on an unreachable server.
- Inside the `docker-desktop` WSL2 distro:
  - only helper procs exist (init, vpnkit-bridge, relay);
  - **no `dockerd`/`containerd` binary exists** in the distro (it's a thin relay distro; the engine usually runs in a companion VM/distros);
  - `/var/run/docker.sock` absent.
- `docker-desktop` distro is present (WSL2) but `docker-desktop-data` (the companion distro that holds actual image layers + named volumes on this WSL2 layout) is **not listed**.
- The Windows service `com.docker.service` ("Docker Desktop Service") is **STOPPED** (SC_QUERY shows STATE=1 STOPPED, exit 1077 = never started) and `net start / sc start` both return **Access denied** from this non-admin session.
- `docker.exe` (Windows client) exists and resolves, but there's no running engine behind `desktop-linux`.

In short: the Docker CLI is fine; the engine (Windows service + WSL2 Linux backend) is not running and can't be started here. That's why `postgres`/`redis`/`backend`/`arq_worker`/`frontend` containers are all absent now, and why earlier in-session `docker exec` healthchecks also timed out.

**This is the only blocker on verifying `docker compose up` and the live HTTP E2E (`scripts/e2e_http_check.py`) this session.**

**Recovery path (needs admin / Docker Desktop running on the host):**
1. Start Docker Desktop on the Windows host (or `net start "Docker Desktop Service"` / `sc start com.docker.service` from an elevated shell), OR ensure the WSL2 backend distros come up (`wsl.exe --list` should then show both `docker-desktop` running and `docker-desktop-data` running).
2. Verify with `docker --context desktop-linux version` that a real `ServerVersion` is returned (client-only `version` output returns `server=` empty.
3. `cd "c:/Users/USER/Desktop/injury detection" && docker compose up -d` and wait for healthchecks.
4. Re-run `backend/scripts/e2e_http_check.py http://localhost:8000 data/real-corpus/squatting__thillai-c__squat.mp4 squatting sagittal` (or similar) against the running stack — this exercises login, upload, confirm, worker, metrics, risk score(200 with a ≥10-video baseline), the refusal paths, and the results endpoints.
5. Confirm `docker compose ps` shows all five services healthy and `/health` + `/health/ready` return 200.

### Real HTTP E2E + browser results

The merged tree documents that these already passed on a prior run (`docs/STATE.md`, `docs/HANDOFF_2026-10-03.md`):
- `scripts/e2e_http_check.py`: real uvicorn + `arq` worker, login → athlete → upload → confirm → worker → risk score 200 (10-video baseline) → 5 sub-scores + 6 injury categories + recommendations.
- Browser e2e (`frontend/e2e/part3_results.mjs`, headless Chrome): 5/5 — login, scored results page, coverage-caveat clip, front-view "cannot score" clip, poor-visibility clip.

These are the merged project's verified results; they were **not re-run this session** because the Docker stack couldn't start. They are reproducible once the engine is up.

---

## Data that was used / placed

- **Corpus:** `data/real-corpus/` — 19 real video clips downloaded from public GitHub repos (`raw.githubusercontent.com`), with `manifest.json` recording source URLs, movement, view, athlete label, and notes. Added to `.gitignore` (do not commit). README: `data/real-corpus/README.md`.
- **Corpus metadata/docs:** `docs/real-data/manifest.json`, `docs/real-data/report_demo_floor8.json`, `docs/real-data/report_production_floor.json` came with the merged package (these reproduce the 24-clip real-data validation; the clips themselves are intentionally excluded from the package for licensing).

---

## Remaining honest limits (unchanged from the merged project's own documentation)

- The system does **not** do supervised injury prediction — it reports risk levels with named drivers (anomaly/asymmetry/prior-injury/ACWR/fatigue). No injury-labelled dataset exists to do otherwise.
- Frontal-plane measurements (knee valgus) remain qualitative flags, never precise angles.
- Accuracy of joint angles is unverified (no ground truth / Vicon).
- Only squatting has a usable baseline; the corpus is ~1 clip short of the production floor at the default `MIN_BASELINE_VIDEOS=10`. With the 19-clip corpus downloaded, a demo floor (≥10 videos from ≥3 athletes) **is now satisfiable** for squats; running the real validation script will show where it stands. The response labels scores provisional below 30 baseline videos by design.

---

## Recommended next steps

1. **Start Docker Desktop / the Windows `com.docker.service` as admin** on this host so the WSL2 engine comes up; then `docker compose up -d` and run `backend/scripts/e2e_http_check.py` against `data/real-corpus/` — that closes the only unverified piece from this session (the live HTTP+E2E path + container healthchecks).
2. **Run the real-data validation script** to see the actual scored results on the downloaded corpus: `cd backend && python scripts/real_clip_validation.py ../data/real-corpus/manifest.json ../data/real-corpus --budget 280` then `python scripts/real_clip_validation.py ../data/real-corpus/manifest.json --score --out /tmp/report.json`.
3. **Decide the baseline floor**: the merged project recommends `MIN_BASELINE_VIDEOS=30` for real use (cuts false-alarms from ~10% to ~2%); the default stays at 10 for demo. If you want the production floor, set it in `.env` and re-run the corpus.
4. **Confirm browser upload form** (the file-chooser → results path) if you want the UI fully exercised end to end.
5. **Commit the integration** once Docker is up and the live E2E passes — the merge is otherwise complete and host-verified.
