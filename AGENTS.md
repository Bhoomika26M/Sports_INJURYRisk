# AGENTS.md — Sports Injury Risk Detection Platform

Read this before any task, in full, every time. If your task touches backend code, also read `/backend/AGENTS.md`. If it touches frontend code, also read `/frontend/AGENTS.md`. Deep reference material lives in `/docs/` — it is linked below, not duplicated here. Do not skip the links because this file looks complete; it is deliberately short and the links are not optional reading.

## Project overview

A platform where coaches, physiotherapists, and sports scientists upload athlete movement videos and receive pose-derived movement-quality metrics and heuristic risk flags. Built for an 8-week, milestone-gated internship (Infosys Springboard) — 4 milestones, 2 weeks each. Five roles: `athlete`, `coach`, `physiotherapist`, `sports_scientist`, `admin`.

Full module map, milestone breakdown, tech stack rationale, directory tree: **`/docs/ARCHITECTURE.md`**

## Before you touch anything

1. Read **`/docs/STATE.md`** — this is what actually exists right now, verified, not assumed. If it disagrees with what you observe in the repo, trust the repo and fix `STATE.md` after your task, don't trust stale claims in this doc.
2. Find your task in `/docs/ARCHITECTURE.md`'s module map. Confirm its milestone. **Do not build ahead of the current milestone** — folders for future milestones exist but are intentionally empty.
3. If your task touches pose estimation, biomechanics, or risk scoring, read **`/docs/SCIENCE_CONSTRAINTS.md` first.** This isn't optional — violating it means shipping a false medical claim, not a style nitpick.
4. Genuinely blocked or facing a decision this doc doesn't cover? Add it to `/docs/DECISIONS.md` under "Open Questions" and stop there. Do not guess and quietly move on — a wrong guess baked into code is far more expensive than a flagged question.

## The non-negotiable laws

- **One deployable backend** (modular monolith). No microservices, no independently networked services, ever — not even "just this one small one."
- **PostgreSQL is the only database engine.** No MongoDB, no vector DB, no data warehouse. Time-series/vector needs, if they ever arise, go through Postgres extensions (TimescaleDB, pgvector) on the same instance.
- **Never claim ML-based injury *prediction*.** No dataset exists that a student team can access linking video biomechanics to confirmed injury outcomes. Risk output is either a literature-cited heuristic score or unsupervised anomaly detection against a movement baseline — never a supervised "this athlete has an X% chance of injury" claim.
- **Never train a pose model from scratch.** Pretrained MediaPipe Pose and Ultralytics YOLO26-pose only.
- **Frontal-plane measurements (knee valgus) are qualitative flags, never precise angles** — in UI copy, API responses, and reports alike. Full numbers and sources: `/docs/SCIENCE_CONSTRAINTS.md`.

Full rationale for every law above: `/docs/ARCHITECTURE.md` §1.

## Setup

Exact commands live in `/backend/AGENTS.md` and `/frontend/AGENTS.md`. Fastest path: `docker compose up --build` brings up postgres, redis, backend, and frontend together.

## Naming (deliberately simple, cross-cutting)

`snake_case` everywhere — Python, SQL, DB columns/tables, **and JSON wire keys.** `kebab-case` only for URL paths (`/athletes/{id}/training-load`). We are intentionally *not* converting to camelCase at the API boundary: one casing convention end-to-end removes an entire class of bugs, at the minor cost of TypeScript interfaces reading as `athlete_id` instead of `athleteId`. Do not "fix" this later — it's deliberate, see `/docs/DECISIONS.md`.

Full request/response envelope, error shape, versioning: `/docs/API_CONVENTIONS.md`

## Anti-patterns — do not do these

- Don't invent a file, function, or endpoint that isn't in this repo or these docs. Grep the actual codebase first. Not found means it doesn't exist yet.
- Don't silently add a dependency. Pin it in the real requirements/package file **and** log it with a reason in `/docs/DECISIONS.md`.
- Don't refactor or restructure working code unless the task explicitly asks for it.
- Don't report a task "done" without having actually run its verification commands and read the real output. Template: `/docs/STATE.md`.
- Don't leave TODO/stub/`pass`-only functions in anything you're claiming is complete.
- Don't change a locked schema (`/docs/SCHEMA.md`) or API contract (`/docs/API_CONVENTIONS.md`) without a same-change entry in `/docs/DECISIONS.md`.

## Security considerations

- Passwords: argon2 only. Never plaintext, never reversible encryption.
- Refresh tokens: httpOnly, secure, SameSite=Lax cookie. **Never localStorage, for any token, ever.**
- Every endpoint gets a typed Pydantic request/response model — no raw `dict` handling.
- Secrets via `.env`, never hardcoded, never committed. `.env.example` documents every required variable with a placeholder value.

## Reference docs (read on demand, not preloaded)

| Doc | Contains |
|---|---|
| `/docs/ARCHITECTURE.md` | Full module map (all 13 areas from the original brief), milestone breakdown, directory tree, tech stack + rationale, full explanation of the Laws above |
| `/docs/SCHEMA.md` | Complete data model across all 4 milestones — DDL, with clear current-vs-designed status per table |
| `/docs/API_CONVENTIONS.md` | Request/response envelope, error shape, naming, versioning, pagination |
| `/docs/SCIENCE_CONSTRAINTS.md` | What's scientifically valid to claim about video-based biomechanics, with numbers and sources |
| `/docs/DECISIONS.md` | Append-only log of why things are the way they are, plus open questions |
| `/docs/STATE.md` | What's actually built right now, and the reusable Definition-of-Done checklist |
