# AGENTS.md — Backend (FastAPI)

Closest-file-wins: this overrides `/AGENTS.md` for anything under `/backend`. Read the root file first for the cross-cutting laws — they still apply here in full.

## Setup commands

- Install: `cd backend && pip install -r requirements.txt`
- Run dev server: `uvicorn app.main:app --reload --port 8000`
- Run via Docker: `docker compose up backend`
- Apply migrations: `alembic upgrade head`
- Create a migration: `alembic revision --autogenerate -m "description"`
- Seed demo data (idempotent, safe to re-run): `python -m app.seed`
- Run full test suite: `pytest`
- Run one test: `pytest tests/test_auth.py::test_login_wrong_password -v`
- Pose pipeline smoke test (M1 only — proves dependencies work, does not implement pose estimation): `python scripts/pose_smoke_test.py test-assets/sample-clips/<file>`

## Module map (backend side — full detail in `/docs/ARCHITECTURE.md`)

| Folder | Purpose | Milestone | Status |
|---|---|---|---|
| `app/modules/auth/` | register / login / refresh / RBAC | M1 | build now |
| `app/modules/users/` | user records | M1 | build now |
| `app/modules/athletes/` | athlete profiles, injury history, training load | M1 | build now |
| `app/modules/video/` | upload, storage, format validation | M2 | do not touch |
| `app/modules/pose/` | pose estimation on uploaded video | M2 | do not touch |
| `app/modules/biomechanics/` | joint angle / ROM / symmetry calculation | M2 | do not touch |
| `app/modules/risk_scoring/` | heuristic risk score + anomaly detection | M3 | do not touch |
| `app/modules/recommendations/` | corrective exercise suggestions | M3 | do not touch |
| `app/modules/analytics/` | dashboard backing queries | M4 | do not touch |
| `app/modules/notifications/` | alerts | M4 | do not touch |

Each future-milestone folder contains a single `README.md` stating what it will hold and when. Do not populate it early, even partially, even as a "preview."

## Code style

- Every route: typed Pydantic request + response models. No raw `dict` in, no raw `dict` out.
- Every route touching athlete data: explicit `Depends(require_role(...))`. Never rely on the frontend to hide a button as the only access control.
- Routers stay thin — parse request, call the service layer, return the response. Business logic lives in `service.py`, not `router.py`.
- Structured logging (stdlib `logging` with a JSON formatter, or `structlog`). No bare `print()` anywhere in `app/`.
- No bare `except:`. Catch specific exceptions, log them with context, return the standard error envelope from `/docs/API_CONVENTIONS.md`.
- snake_case for everything, including JSON response keys — see root `AGENTS.md` for why.

## Testing instructions

- Every new endpoint needs at minimum: one happy-path test, one auth-failure test (401 or 403), one validation-failure test (422).
- `pytest` must be fully green — zero skipped, zero xfail — before any task is considered done.
- Full Definition-of-Done checklist template: `/docs/STATE.md`.

## Security considerations

- `argon2-cffi` for password hashing.
- Refresh tokens: only the hash is stored, in `refresh_tokens.token_hash` — never the raw token, anywhere, in any log either.
- CORS: explicit allowed origins read from `.env`. Never `allow_origins=["*"]`, not even "temporarily for testing."
