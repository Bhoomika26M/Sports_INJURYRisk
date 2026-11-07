# API_CONVENTIONS.md

## Versioning

Every route under `/api/v1/`. A breaking change gets a new version prefix — never a silent change to v1's existing shape.

## Success responses

Single-resource endpoints return the resource directly, no wrapper:
```json
{ "id": "...", "email": "...", "role": "coach" }
```

List endpoints always use this shape, even when a filter makes the result small:
```json
{
  "items": [ ... ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

## Error responses — one shape, every endpoint, every module, no exceptions

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable summary",
    "details": {}
  }
}
```

| Status | When |
|---|---|
| 400 | Malformed request |
| 401 | Not authenticated (missing/invalid/expired token) |
| 403 | Authenticated, but not permitted for this role/resource |
| 404 | Resource doesn't exist |
| 409 | Conflict (e.g. duplicate email on register) |
| 422 | Request parsed but failed validation |
| 500 | Server error — message must never leak internals (stack traces, SQL, file paths) |

## Auth

`Authorization: Bearer <access_token>` header on every protected route. The refresh token never appears in a header or a body the frontend JS can read — it travels only as an httpOnly cookie set and read by the backend.

## Naming — deliberately uniform, no conversion layer

- URL paths: kebab-case, plural nouns — `/athletes`, `/athletes/{id}/training-load`
- JSON keys: **snake_case**, matching Python and the database exactly — `athlete_id`, not `athleteId`
- DB columns: snake_case, matches `/docs/SCHEMA.md` exactly

This is a deliberate simplicity trade-off (see `/docs/DECISIONS.md`): one casing convention end-to-end removes an entire class of bugs from forgetting a camelCase conversion on one model out of dozens. Do not add an `alias_generator` or any camelCase conversion layer without a `/docs/DECISIONS.md` entry explaining why the trade-off changed.

## Source of truth

FastAPI's auto-generated docs (`/docs`, `/openapi.json` on the running server) are the live contract. If this file and the running server disagree, the code has a bug — fix the code, don't edit this file to match it.

---

## Comparison & Hardened Platform Endpoints (Engine 2.3 / Hardened Build)

### Dual-Video Comparison
- `POST /api/v1/videos/compare`
  - Body: `{"reference_video_id": "...", "comparison_video_id": "..."}`
  - Access: Caller must have access to both videos.
  - Returns: Real biomechanical metric deltas, inflection frames, qualitative valgus assessment, 6.5° noise floor flags.

### Within-Athlete History & Rolling Baseline
- `GET /api/v1/athletes/{id}/history`
  - Access: Athlete, or coach/physio assigned to athlete.
  - Returns: Chronological list of completed video metrics for trend sparklines.
- `GET /api/v1/videos/{video_id}/history-comparison`
  - Access: Same as video.
  - Returns: Deviations against the athlete's personal rolling baseline across $\ge 3$ eligible prior sessions. Returns HTTP 202 `history_building` if $< 3$ priors exist.

### Video Processing Retries
- `POST /api/v1/videos/{video_id}/retry`
  - Access: Video owner / athlete's coach.
  - Returns: Queues failed video for reprocessing. Rejects fatal non-retryable errors (`resolution_too_low`, `duration_too_short`, `duration_too_long`) with HTTP 422.

### Password Reset Flow
- `POST /api/v1/auth/password/forgot`
  - Body: `{"email": "..."}`
  - Returns: Constant HTTP 202 `{"message": "If this email is registered, a password reset code has been sent."}` (no user enumeration). Rate limited to 3 req/min.
- `POST /api/v1/auth/password/reset`
  - Body: `{"email": "...", "otp": "...", "new_password": "..."}`
  - Returns: HTTP 200 on success. Revokes active refresh tokens. Rate limited to 5 req/min.

### Athlete Claiming & Profile
- `GET /api/v1/athletes/me`
  - Access: Athlete role.
  - Returns: Current user's athlete profile.
- `POST /api/v1/athletes/claim`
  - Body: `{"athlete_id": "..."}`
  - Access: Unclaimed athlete user.
  - Returns: Links logged-in user to unassigned athlete record.

