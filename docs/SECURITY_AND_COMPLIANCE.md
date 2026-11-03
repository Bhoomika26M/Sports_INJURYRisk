# AthletiQ Security, Privacy & Compliance Architecture

AthletiQ handles biometric motion capture, video recordings, and clinical injury screening data. This document outlines our data privacy protocols, compliance frameworks (HIPAA & GDPR), and security controls.

---

## 1. Compliance Framework Alignment

### 1.1 HIPAA (Health Insurance Portability and Accountability Act) Considerations
- **Protected Health Information (PHI)**: Athlete video recordings, biomechanical movement telemetry, and injury histories are treated as confidential clinical health telemetry.
- **Access Controls (§ 164.312(a))**: Strict Role-Based Access Control (RBAC) ensures athletes only view their personal records, and clinical/coaching staff only view assigned athletes.
- **Audit Controls (§ 164.312(b))**: All API operations are tagged with `X-Request-ID` and structured log records recording access timestamps, user IDs, and endpoint paths.
- **Transmission Security (§ 164.312(e))**: All HTTP communications are forced over HTTPS / TLS 1.3 in production with strict cipher suites.

### 1.2 GDPR (General Data Protection Regulation) Considerations
- **Lawful Basis & Consent (Art. 6 & 9)**: Explicit consent is obtained prior to video recording and biometric landmark processing.
- **Right of Erasure ("Right to be Forgotten", Art. 17)**: Deleting an athlete profile cascades deletion across all associated video files, landmarks JSON artifacts, kinematic assessments, and notifications.
- **Data Minimization (Art. 5(1)(c))**: Only joint coordinate vectors necessary for kinematic angle computation are extracted and stored.

---

## 2. Role-Based Access Control (RBAC) Matrix

| Endpoint Group | Athlete | Coach | Physiotherapist | Sports Scientist | Administrator |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Self Profile (`/users/me`, `/athletes/me`)** | Read / Write | Read / Write | Read / Write | Read / Write | Read / Write |
| **Upload Movement Video (`/videos/`)** | Self Only | Assigned | Assigned | Assigned | Any Athlete |
| **View Athlete Videos** | Self Only | Assigned | Assigned | Assigned | All |
| **View Athlete Assessments** | Self Only | Assigned | Assigned | Assigned | All |
| **Export Clinical Reports (PDF/Excel)** | Self Only | Assigned | Assigned | Assigned | All |
| **Manage Squad Roster (`/athletes/{id}/assign`)** | Self Assign | Assigned | Assigned | Assigned | All |
| **User Management (`/admin/users`)** | Denied | Denied | Denied | Denied | Full Access |
| **System Metrics (`/health/metrics`)** | Allowed | Allowed | Allowed | Allowed | Allowed |

---

## 3. Cryptographic Security & Hardening Controls

### 3.1 Authentication & Token Security
- **Algorithm**: HMAC-SHA256 (`HS256`) signed with a 256-bit cryptographically secure pseudorandom key (`SECRET_KEY`).
- **Storage**: Tokens are delivered both as JSON payloads and inside `HttpOnly`, `SameSite=Lax` cookies, neutralizing Cross-Site Scripting (XSS) credential theft.
- **Google OAuth 2.0 / OpenID Connect**: Real token verification with Google's public key sets prevents token forging and identity spoofing.

### 3.2 Input Sanitization & Attack Mitigation
- **SQL Injection**: Parameterized SQL execution enforced across all endpoints via SQLAlchemy 2.0 ORM.
- **Path Traversal Defense**: All uploaded videos are renamed to UUIDv4 hex strings prior to filesystem persistence, preventing directory traversal attacks.
- **Content-Type & Magic Byte Validation**: Files are checked for valid video headers (`ftypmp42`, `moov`, `mdat`) and safe file extensions before processing.
- **File Size Restrictions**: Max upload limit enforced at 500 MB to prevent resource exhaustion and denial-of-service.

### 3.3 HTTP Response Hardening Headers
Every response emitted by AthletiQ includes:
```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
```
