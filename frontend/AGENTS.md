# AGENTS.md — Frontend (Next.js 16)

Closest-file-wins: this overrides `/AGENTS.md` for anything under `/frontend`. Read the root file first — the cross-cutting laws still apply here in full.

## Setup commands

- Install: `cd frontend && npm install`
- Run dev server: `npm run dev`
- Run via Docker: `docker compose up frontend`
- Build (must be zero type errors before any task is done): `npm run build`
- Lint: `npm run lint`

## Code style

- App Router only. Server Components by default; `"use client"` only where real interactivity is needed (forms, state, effects).
- TanStack Query for all backend data fetching. No raw `fetch()` scattered through components — go through `lib/api-client.ts`.
- Tailwind utility classes only. No ad hoc CSS files, no inline `style={}` unless a value is genuinely dynamic (e.g. a computed width).
- Auth: access token held in memory via `lib/auth-context.tsx`. Refresh token lives in an httpOnly cookie set by the backend — the frontend never reads or stores it directly. **Never `localStorage.setItem` for any token, under any circumstance.**
- Route protection via Next.js middleware (`middleware.ts`), not ad hoc checks scattered inside individual pages.
- JSON field names from the API are snake_case (`athlete_id`, not `athleteId`) — match that in TypeScript interfaces rather than converting. See root `AGENTS.md` for why.

## Structure

```
app/
├── login/page.tsx
├── register/page.tsx
├── dashboard/{layout.tsx, page.tsx}       # role-aware shell
├── athletes/{page.tsx, [id]/page.tsx}
├── videos/                                 # M2 — upload UI, do not build early
└── reports/                                 # M4 — do not build early
lib/{api-client.ts, auth-context.tsx}
components/
```

Dashboards get real charts/analytics content starting Milestone 4, not before. Milestone 1's dashboard is a role-aware shell that proves auth + routing work — see `/docs/ARCHITECTURE.md` for the exact M1 page scope.

## Testing instructions

- `npm run build` must be clean before any task is done.
- Manual verification for auth/role work: log in as each of the 5 seeded demo users, confirm the correct dashboard shell renders per role.

