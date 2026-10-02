# Frontend audit & rebuild — 2026-10-01

Method: read every page and the backend contract, ran the **original** frontend against the real backend in headless
Chrome to reproduce bugs, rebuilt, then re-verified in the browser (56 checks) plus `pytest` (48), `tsc`, `eslint`, `next build`.

## What was broken (original code)

| # | Problem | Evidence |
|---|---|---|
| 1 | **Could not log in.** Refresh cookie is `Path=/api/v1/auth`; middleware read it on `/dashboard`. | trace: `POST /auth/login` 200 → `GET /auth/me` 200 → `GET /dashboard` **307 → /login** |
| 2 | Upload dropdowns always empty (`loadData` never called; `useEffect` not imported) | code |
| 3 | Storage `PUT` sent no `Authorization` header; endpoint requires it → every upload 401 | code + backend route |
| 4 | Processing bar hard-coded to 0% although API returns `progress_pct` | code |
| 5 | `<video src>` / PDF / Excel `<a href>` can't send a Bearer token → 401; `/local-storage/` has no GET | code |
| 6 | Logout cleared an **httpOnly** cookie from JS (no-op); `POST /auth/logout` never called | code |
| 7 | Sidebar hidden < 900px with no replacement nav (no navigation on phones) | CSS |
| 8 | Dead links: `/athletes/[id]/edit`, `/injuries/new`, `/training-load/new`, and no `/videos` page | routes |
| 9 | Knee valgus plotted as numbers (forbidden by `SCIENCE_CONSTRAINTS.md`); fake "Not assessed" column | code |
| 10 | 46 lint errors; TanStack Query mandated but not installed | `npm run lint` |

## Backend bugs found by driving the real API (fixed; regression tests added)

| Bug | Impact |
|---|---|
| `biomechanical_metrics.confidence` was `VARCHAR(10)`; worker writes `'qualitative'` (11) — migration 0002 missed this column | any clip with valgus frames fails at DB commit → video "failed" (migration `0003`) |
| `GET /videos/{id}/biomechanics` passed ORM rows to a schema without `from_attributes` | **500 for every video with frames** — results page could never load |
| `GET /athletes` used `select` without importing it | **500 for every athlete-role user** (dashboard, profile, upload) |

## What changed (frontend)
Rebuilt auth/session, API client (authenticated upload/download/media, token refresh, friendly errors), design-system CSS,
app shell (desktop sidebar + mobile bottom nav + user menu), and every page. New: Videos library, athlete edit/injury/training modals,
404 + error boundary, toasts, confirm dialogs. Upload flow: drag & drop, client pre-checks (type/size/duration), real progress + cancel,
tab-close warning, polling that stops itself, specific failure messages.

## Verification summary
- Browser (real API, simulated ML worker): 56/56. Highlights: signed-out redirect keeps destination; PUT carries Bearer token; confirm 200;
  bad/short/oversize/fake files each rejected with a clear message; PDF/Excel/CSV download with valid file headers; playback via blob;
  sign-out revokes the refresh token (`/auth/refresh` → 401); all 5 roles load; athlete role sees only own profile; mobile 390px has nav and no horizontal scroll.
- `pytest` 48/48 (46 existing + 2 new that fail without the fixes). `tsc` clean. `eslint` 0 errors (baseline 46). `next build` clean.

## NOT verified / known limits
- **Real ML processing** (mediapipe/YOLO) — not run; worker output simulated with SQL.
- Typography with the real Inter font (sandbox used a stub font; screenshots show a fallback serif).
- Turbopack `npm run build` (verified with `next build --webpack` + font mock because Google Fonts is unreachable in the sandbox).
- Two results states were verified with a **mocked response** (insufficient baseline; "not yet scored" report) — shapes copied from the backend code.
- Keyboard/screen-reader behaviour was built to spec (native `<dialog>`, labelled fields, `aria-live`, focus rings) but not tested with assistive tech. No automated contrast check.
- Not run: real-device Safari/iOS (`.mov` metadata probing, `100vh` quirks).

## Backend gaps found, not fixed
1. `/auth/register` accepts `role: "admin"` from anyone (UI no longer offers it).
2. Athlete names come only from a linked user; `POST /athletes` has no name → UI shows "Basketball athlete, 24".
3. Athlete-role signups get no athlete profile → cannot upload (UI explains; needs a link/claim flow).
4. Video playback downloads the whole file as a blob before playing; a short-lived signed-URL endpoint would stream.
5. Google sign-in cannot work as built (no frontend callback page; backend callback is POST, Google redirects GET).
6. `middleware.ts` is deprecated in Next 16 → rename to `proxy.ts`.
7. The pytest suite builds schema with `create_all` from models, so model↔migration drift (like #1 above) is invisible to it.
