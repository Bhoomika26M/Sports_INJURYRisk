# STATE.md

The single source of truth for "what actually exists right now." Update this after every verified task — not from memory, from actually re-running the checks below against the real repo. If this file and reality disagree, reality wins; fix this file.

**Last verified:** 2026-07-11
**Verified by:** full docker compose up --build, alembic upgrade, pytest run, and manual UI build verification.

---

## Current status

**Milestone 1 — Fully Complete.** Scaffolding, infrastructure, PostgreSQL/Redis setup, complete Auth module, and complete Athlete module are live. The frontend is fully scaffolded and built, successfully handling JWT rotation and RBAC routing.

**Milestone 2 — Fully Complete (Post-Audit).** Video upload flow (mock S3), YOLOv8 person-count, MediaPipe Pose extraction, and Biomechanics math engines are fully implemented and passing security/robustness audits.

**Milestone 3 — Fully Complete.** Risk scoring baseline generation, anomaly detection using Isolation Forest, and rule-based recommendation engine implemented and verified via automated tests. Frontend Results view integrated.

**Next step:** execute Milestone 4 — dashboards, notifications, reports, deploy.

| Milestone | Modules | Status |
|---|---|---|
| M1 — auth, athletes, env setup | 1, 2 | complete |
| M2 — video, pose, biomechanics | 3, 4, 5 | complete |
| M3 — risk scoring, recommendations | 6, 7, 8, 9 | complete |
| M4 — dashboards, notifications, reports, deploy | 10, 11, 12, 13 | not started |

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
