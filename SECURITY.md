# Security Policy — Sports Injury Risk Detection Platform

## 1. Authentication & Session Architecture

The platform enforces strict identity boundaries across 5 role tiers: `athlete`, `coach`, `physiotherapist`, `sports_scientist`, and `admin`.

### Token Storage & Transmission
- **Access Tokens:** Short-lived JWTs (15 minutes) kept **strictly in memory** on the client. **Never stored in `localStorage` or `sessionStorage` under any circumstance.**
- **Refresh Tokens:** High-entropy random tokens stored exclusively in `httpOnly`, `secure` (in production), `SameSite=Lax` cookies with explicit expiry (`/api/v1/auth/refresh`).
- **Session Hints:** A non-secret, unforgeable `session_hint=1` cookie is set for Next.js App Router edge routing and middleware redirect checks.
- **Password Hashing:** Passwords and OTP verification codes are hashed using **Argon2id** (`argon2-cffi`), resistant to GPU/ASIC cracking. Plaintext passwords never touch logs or persistent storage.

---

## 2. Multi-Tenant Authorization & IDOR Protection

All resources (`Athlete`, `Video`, `RiskScore`, `BiomechanicalMetric`, `PostureVector`, `InjuryHistory`, `TrainingLoad`) are gated by centralized access loaders in `app.core.access`:

- **Ownership Invariants:**
  - Coaches, physiotherapists, and scientists can only access athletes assigned to their roster or organization.
  - Athletes can only access their own profile and video kinematics (`user_id == current_user.id`).
  - Cross-user lookups (`POST /videos/compare`, `GET /videos/{id}/history-comparison`, etc.) require valid access to **both** participating resources; any mismatch terminates immediately with HTTP 403 `INSUFFICIENT_PERMISSIONS`.
- **Automated Verification:**
  - A dynamic authorization matrix test suite (`backend/tests/test_authorization_matrix.py`) walks all routes containing `{video_id}` and `{athlete_id}` on every CI run, verifying 403/404 isolation across role combinations.

---

## 3. Account Enumeration & Rate Limiting

- **Password Reset:** `POST /api/v1/auth/password/forgot` always returns HTTP 202 `ACCEPTED` with the identical message regardless of whether the requested email address exists in the database.
- **Brute-Force Lockout:** OTP codes expire after 10 minutes and lock out after 5 consecutive failed attempts with HTTP 429 `TOO_MANY_ATTEMPTS`.
- **Session Revocation:** Resetting a password automatically revokes all existing refresh tokens in the database, immediately terminating stale sessions.
- **Rate Limiting:** Auth endpoints are throttled via in-process sliding-window rate limiters.

---

## 4. Privacy & Third-Party AI Boundaries

- **Zero Supervised ML Outcome Claims:** The platform never predicts injury probabilities or percentages. All outputs are transparent heuristic risk levels or unsupervised anomaly scores against a movement baseline.
- **Display-Only Gemini Integration:**
  - Gemini visual observations (`google-genai`) are strictly **display-only** and never feed scoring formulas, comparison deltas, or clinical classifications.
  - Video footage processed by Gemini uses short visual snippets only when baseline population videos are insufficient (< 10 videos across 3 athletes).
  - No athlete PII (name, email, age, medical history) is ever transmitted to external AI APIs.

---

## 5. Reporting a Security Vulnerability

If you discover a potential vulnerability in this platform, please do not file a public GitHub issue. Instead, report it privately to the project maintainers with reproducible steps and proof-of-concept payloads. Vulnerabilities are reviewed and addressed within 48 hours.
