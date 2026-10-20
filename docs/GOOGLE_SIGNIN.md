# Google Sign-In (OAuth 2.0 authorization-code flow)

This document describes the **"Continue with Google"** sign-up / sign-in
integration.

It uses the standard **OAuth 2.0 authorization-code flow with a client
secret**: the browser is redirected to Google, Google returns a short-lived
authorization *code* to a redirect URI you control, and the backend exchanges
that code for tokens using the client secret. The secret never reaches the
browser.

> The feature is **disabled until credentials are set**. With
> `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` empty, `/auth/google/authorize-url`
> returns **`503 Service Unavailable`**, and the button on the sign-in page shows
> an "unavailable" message.

## Endpoints

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/api/v1/auth/google/authorize-url` | none | Returns `{authorization_url, state}`. Optional `?next=/some/path` echoes a return path back in the signed state. `503` if unconfigured. |
| `POST` | `/api/v1/auth/google/exchange` | none | Body `{code, state}`. Verifies the state, exchanges the code with Google, and returns the normal `{access_token, token_type}`. |
| `GET` | `/api/v1/auth/google/callback` | none | Server-side redirect variant: exchanges the code and `302`-redirects to `GOOGLE_FRONTEND_SUCCESS_REDIRECT` with the token in the URL **fragment**; failures redirect to `GOOGLE_FRONTEND_FAILURE_REDIRECT`. Optional alternative to `/google/exchange`. |

The frontend uses `/authorize-url` + `/exchange`. The `/callback` route exists
for deployments that prefer to point Google directly at the backend.

## Configuration

Set these in the backend environment (see `backend/.env.example`):

| Variable | Meaning |
| --- | --- |
| `GOOGLE_CLIENT_ID` | OAuth 2.0 **Web application** client id from Google Cloud. |
| `GOOGLE_CLIENT_SECRET` | The matching client secret. Server-side only — never expose it to the frontend. |
| `GOOGLE_REDIRECT_URI` | Must **exactly** match an "Authorized redirect URI" on the client. Defaults to `http://localhost:5173/auth/google/callback`. |
| `GOOGLE_FRONTEND_SUCCESS_REDIRECT` | Where the `/callback` route sends the browser on success. |
| `GOOGLE_FRONTEND_FAILURE_REDIRECT` | Where the `/callback` route sends the browser on failure. |
| `GOOGLE_STATE_EXPIRE_SECONDS` | Lifetime of the signed OAuth `state` (CSRF protection). Default 600. |

The Google endpoints themselves are configurable (`GOOGLE_AUTH_URI`,
`GOOGLE_TOKEN_URI`, `GOOGLE_USERINFO_URI`) but rarely need changing.

### Google Cloud setup (when you have the key)

1. Google Cloud console → **APIs & Services → Credentials**.
2. **Create credentials → OAuth client ID → Web application**.
3. Under **Authorized redirect URIs**, add the exact `GOOGLE_REDIRECT_URI`
   (e.g. `http://localhost:5173/auth/google/callback`; add your production URL
   too).
4. Copy the **Client ID** and **Client secret** into the backend env and restart.
5. On the OAuth consent screen, add test users if the app is still in "Testing".

## Flow

```
Browser                      Frontend                    Backend                     Google
  |  click "Continue with Google" |                            |                         |
  |------------------------------>| GET /google/authorize-url  |                         |
  |                               |--------------------------->| build signed state      |
  |                               |<-- {authorization_url} ----|                         |
  |  redirect to Google ----------|--------------------------------------------------->   |
  |  (consent screen) ------------------------------------------------------------------> |
  |<-- redirect to /auth/google/callback?code=...&state=... ---------------------------- |
  |                               | POST /google/exchange {code,state}                   |
  |                               |--------------------------->| verify state            |
  |                               |                            | exchange code ---------> |
  |                               |                            | fetch userinfo --------> |
  |                               |                            | resolve local account   |
  |                               |<-- {access_token} ---------| mint JWT + session      |
  |  navigate to /dashboard       |                            |                         |
```

## Account resolution rules

After Google confirms the profile, the backend resolves it to a local account.
The email **must be verified by Google** (`email_verified`), otherwise the
sign-in is refused (`403`).

1. **Existing federated identity** — a user whose `oauth_provider` +
   `oauth_subject` match → **sign in**. (The `sub` is Google's stable account
   id; this is the primary key for the link, not the email.)
2. **Existing email, not yet linked** — a user with the same verified email →
   **link** the Google identity to that local account and sign in. This
   prevents duplicate accounts for the same person. Comparison is
   case-insensitive.
   * If that account is already bound to a **different** Google `sub`, the
     request is refused (`409`) rather than silently hijacking the account.
3. **No match** → **create a new account**. Self-provisioned Google accounts are
   always **`athlete`**, exactly like public registration, and get an athlete
   profile. Professional roles still require an administrator.

Inactive accounts are refused (`403`) at every step.

## Security properties

* **CSRF / code injection:** the `state` is a short-lived, HMAC-signed value
  (stateless — no server session store). The callback verifies the signature and
  age before exchanging anything.
* **Client secret stays server-side.** The browser never sees it.
* **Verified email only.** We refuse unverified addresses so nobody can claim an
  address they don't control.
* **No silent account theft.** An email bound to a different Google subject is
  rejected instead of re-linked.
* **No accounts created for professional roles** via Google.
* **Google-only accounts cannot be password-loggable.** Their `password_hash`
  holds a hash of random bytes, so password login can never match. They can
  still set a password later via the email-OTP change-password flow.
* **Normal session semantics.** Google sign-in mints the same JWT + server-side
  session as password login, so revocation (`logout`, password change revoking
  all sessions) works identically.
* **Audit logging.** `GOOGLE_SIGNIN` (with the outcome: `created` / `linked` /
  `signed_in`) and `GOOGLE_SIGNIN_FAILED` (with the reason) are recorded. Tokens,
  authorization codes, secrets, and raw profile payloads are **never** logged.

## Database

Migration `b7d4c1e9a2f3` adds two nullable columns to `users`:

* `oauth_provider` — e.g. `"google"` (indexed)
* `oauth_subject` — the provider's stable user id (indexed)

Both are `NULL` for password-only accounts, so the change is additive and
non-destructive; downgrade drops the columns.

## Frontend

* `frontend/src/components/GoogleSignInButton.jsx` — the button, used on both
  the sign-in and registration pages.
* `frontend/src/pages/GoogleCallback.jsx` — public route
  `/auth/google/callback` that reads `?code=&state=`, calls the exchange
  endpoint, and finishes sign-in (guarded against React 18 double-invoke).
* `frontend/src/context/AuthContext.jsx` — `startGoogleLogin()` (fetch URL then
  navigate) and `loginWithGoogle(code, state)`.
* `frontend/src/services/api.js` — `googleAuthorizeUrl()` / `googleExchange()`.

## Enabling it

1. Put `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and a matching
   `GOOGLE_REDIRECT_URI` in the backend env.
2. Restart the backend (`alembic upgrade head` first if the DB predates
   migration `b7d4c1e9a2f3`).
3. The button becomes active; no frontend rebuild is required for the secrets
   (they live server-side).
