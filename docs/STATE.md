# STATE.md

The single source of truth for "what actually exists right now." Update this after every verified task — not from memory, from actually re-running the checks below against the real repo. If this file and reality disagree, reality wins; fix this file.

**Last verified:** 2026-09-30
**Verified by:** postgres+redis via Docker, `alembic upgrade head` clean, seed idempotent, `pytest` 46/46 green, `npm run build` clean (16 routes), `/health` 200 against live server.

---

## Current status

**Rebuild (all 4 milestones) — Backend + API complete and verified.** Fresh schema (`0001_init` + `0002_widen_confidence`), 7-movement registry seeded, JWT + Google OAuth2 scaffold, YOLO tracking with main-subject selection, 7 movement-specific biomechanics calculators, Isolation Forest anomaly + transparent composite scoring (anomaly/asymmetry/prior-injury/ACWR/fatigue), rule-based recommendations, team/coach/movement analytics, notifications, PDF/Excel/CSV exports with methodology_note.

**Frontend — all pages built, `npm run build` clean.** Design-system shell (sidebar/topbar/canvas), login/register (+Google button), landing, 5 role dashboards (athlete/coach/physio/scientist/admin with role router), athletes CRUD + ACWR view, video upload/detail/results (recharts + exports), notifications, reports.

**Not yet verified:** end-to-end video processing on a real clip (needs YOLO/MediaPipe model downloads + arq worker running); Google OAuth2 needs real client credentials; S3/R2 swap still mocked to local disk; no browser-based manual UI pass yet.

| Milestone | Modules | Status |
|---|---|---|
| M1 — auth, athletes, env setup | 1, 2 | complete (verified) |
| M2 — video, pose, biomechanics | 3, 4, 5 | complete (verified, unit + API level) |
| M3 — risk scoring, recommendations | 6, 7, 8, 9 | complete (verified) |
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
