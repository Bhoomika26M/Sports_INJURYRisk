# Email OTP: Password Recovery & Password Change

This document describes the email one-time-password (OTP) workflows used for
**forgotten-password recovery** and **authenticated password change**.

The previous emailed *reset-link* flow (a 1-hour token in a URL handled by
`app/services/password_reset_service.py`) has been **replaced** by these OTP
workflows. The old module and the `password_resets` table are retained
(unused) so historical data stays valid; do not wire them into routes.

## Endpoints

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/api/v1/auth/forgot-password` | none | Request a recovery OTP. Body: `{"email": "..."}` |
| `POST` | `/api/v1/auth/reset-password` | none | Reset password. Body: `{"email": "...", "otp": "004281", "new_password": "..."}` |
| `POST` | `/api/v1/auth/change-password/request-otp` | bearer | Request a change OTP (sent to the account's own email, **not** a client-supplied address) |
| `POST` | `/api/v1/auth/change-password` | bearer | Body: `{"otp": "004281", "current_password": "...", "new_password": "..."}` |

> **Breaking change:** `reset-password` used to take `{token, new_password,
> confirm_password}` and `change-password` used to take `{current_password,
> new_password, confirm_password}`. Both now use the OTP contracts above.
> OTPs are **strings** — send `"004281"`, not `4281` (leading zeros matter).

## How OTPs are generated and stored

* Six-digit numeric codes produced with `secrets` (`app/core/otp.py`). Codes are
  zero-padded strings so leading zeros survive.
* Only a **keyed HMAC-SHA256 digest** is stored (column `password_otps.otp_hash`).
  The raw code is never persisted or logged. A database-only attacker cannot
  brute-force the stored digest without the server key.
* The **purpose** (`password_recovery` / `password_change`) is bound into the
  digest and stored on the row, so a code issued for one workflow can never
  authorize the other.
* Key management: the HMAC key comes from `OTP_HMAC_SECRET`. If unset, a
  **distinct** key is derived from `SECRET_KEY` via HKDF with domain separation
  (this is key derivation, not naive reuse). Production should set
  `OTP_HMAC_SECRET` explicitly and rotate it independently.

## Lifecycle rules

* **Expiry** — `OTP_EXPIRE_MINUTES` (default 5).
* **Attempts** — `OTP_MAX_ATTEMPTS` (default 5) per issued code. The 6th
  submission is refused with `429` and the code is unusable, even if correct.
* **Single use** — a correct code is consumed with one conditional `UPDATE`
  (`WHERE used_at IS NULL AND invalidated_at IS NULL AND expires_at > now AND
  attempt_count < max_attempts`). Two concurrent requests cannot both succeed.
* **Superseded codes** — issuing a new code for the same account/purpose
  invalidates any outstanding one.
* **Resend cooldown** — `OTP_RESEND_COOLDOWN_SECONDS` (default 60) between
  issues per account/purpose. Recovery requests are silently suppressed inside
  the window (generic response); the authenticated change flow returns `429`.
* **Consumption + password update are atomic** — both happen in the same
  transaction.

## Account enumeration protection

* `forgot-password` always returns the same generic response, for existing and
  non-existent emails. Unknown emails receive no email and create no row.
* No OTP, token, or account-existence detail appears in any response.
* `change-password/request-otp` always targets the authenticated account's own
  email; the request body cannot select a recipient.

## Session revocation

On **either** successful flow, **all** sessions for the account are revoked
server-side, including the caller's current session. Previously issued access
tokens are rejected by the auth dependency (`401`). The frontend clears its
local auth state and returns the user to `/login`.

## Email delivery failure

If the mail provider fails, the just-issued OTP is invalidated so an
undisclosed, unusable code cannot linger, and a `OTP_DELIVERY_FAILED` audit
event is written. The recovery endpoint still returns the generic response (no
oracle); the authenticated change-OTP endpoint returns `502`.

## Audit logging

Security events are written via `app/core/audit.py`: `OTP_REQUESTED`,
`OTP_VERIFICATION_FAILED`, `OTP_DELIVERY_FAILED`, `PASSWORD_RESET_REQUEST`,
`PASSWORD_RESET`, `PASSWORD_CHANGE`, and `SESSION_REVOCATION`. These **never**
contain the OTP, passwords, JWTs, or SMTP credentials.

## Development mode

When `ENVIRONMENT=development` the email service prints the code to the server
console instead of sending it:

```
[DEV MODE] OTP for user@example.com (password recovery): 004281 (expires in 5 min)
```

This is development-only. With any other `ENVIRONMENT`, codes are sent by SMTP
and never printed.

## Configuration

See `backend/.env.example`:

```
OTP_LENGTH=6
OTP_EXPIRE_MINUTES=5
OTP_MAX_ATTEMPTS=5
OTP_RESEND_COOLDOWN_SECONDS=60
OTP_HMAC_SECRET=          # recommended: set in production
```

## Database

New table `password_otps` (migration `9f1c2ab7d4e5`):

| Column | Notes |
| --- | --- |
| `id` | PK |
| `user_id` | indexed, nullable (current flows always set it) |
| `purpose` | indexed; `password_recovery` or `password_change` |
| `otp_hash` | keyed HMAC digest |
| `created_at`, `expires_at` | timestamps |
| `attempt_count`, `max_attempts` | verification limiting |
| `used_at`, `invalidated_at` | single-use / supersession markers |

The migration is additive and portable across SQLite and PostgreSQL.

## Frontend

* `frontend/src/pages/ForgotPassword.jsx` — two-step recovery (email → code +
  new password) with a resend cooldown.
* `frontend/src/pages/Profile.jsx` — a "Change Password" card (request code →
  code + current password + new password), which signs the user out on success.
* `frontend/src/services/api.js` — `forgotPassword`, `resetPassword`,
  `requestChangePasswordOtp`, `changePassword`.
* Route `/forgot-password` (public), linked from the sign-in page.

OTPs and passwords are held only in component state — never in `localStorage`,
and never logged to the console.
