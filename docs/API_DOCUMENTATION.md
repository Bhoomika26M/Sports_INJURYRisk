# AthletiQ REST API Reference Guide

The AthletiQ backend exposes a RESTful API with automated OpenAPI specifications accessible at `/docs` (Swagger UI) and `/redoc` (ReDoc).

Base URL: `http://localhost:8000/api/v1` (Development) or `/api/v1` (Production via Nginx)

---

## 1. Authentication & Session Management

### `POST /auth/register`
Create a new athlete, coach, physiotherapist, sports scientist, or administrator account.
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "SecurePassword123!",
    "full_name": "Marcus Vance",
    "role": "athlete",
    "admin_code": "optional-secret-code-for-admin"
  }
  ```
- **Response**: `200 OK` with user record.

### `POST /auth/login`
OAuth2 form-encoded login returning JWT Bearer token and setting HttpOnly session cookie.
- **Form Data**: `username=user@example.com&password=SecurePassword123!`
- **Response**: `200 OK`
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1...",
    "token_type": "bearer",
    "user": { "id": 1, "email": "user@example.com", "role": "athlete" }
  }
  ```

### `POST /auth/google`
Authenticates Google One Tap / Google Sign-In with real Google ID Token verification.
- **Request Body**:
  ```json
  {
    "credential": "eyJhbGciOiJSUzI1...",
    "role": "athlete"
  }
  ```

### `POST /auth/logout`
Terminates user session and invalidates HttpOnly authentication cookie.

---

## 2. Athletes & Roster Management

### `GET /athletes/me`
Retrieve currently authenticated athlete's biometric profile and training load telemetry.

### `POST /athletes/me`
Create or configure initial athlete profile (sport, position, age, height, weight, injury history).

### `GET /athletes/`
List athletes.
- **Allowed Roles**: Coach, Physiotherapist, Sports Scientist, Administrator.
- **Query Parameters**:
  - `skip` (int): Pagination offset (default: 0).
  - `limit` (int): Pagination limit (default: 100).
  - `filter_by` (string): `assigned` (default for staff), `unassigned`, or `all` (admin).

### `POST /athletes/{athlete_id}/assign?staff_id={staff_id}`
Connect an athlete to a staff member's active squad roster.

---

## 3. Movement Video Processing Pipeline

### `POST /videos/`
Upload a movement trial video and trigger asynchronous MediaPipe pose estimation.
- **Headers**: `Authorization: Bearer <token>`, `Content-Type: multipart/form-data`
- **Form Fields**:
  - `file`: MP4/MOV/AVI/WEBM binary file.
  - `athlete_id` (int): Profile ID.
  - `movement_type` (str): `squatting`, `running`, `sprinting`, `landing`, `jumping`, `cutting`, `throwing`, `general`.
- **Response**: `200 OK` with initial video record (`status: "uploaded"`).

### `GET /videos/{video_id}`
Get processing status, video resolution, duration, FPS, and quality audit scores.

### `GET /videos/athlete/{athlete_id}`
List all historical movement trial recordings for a given athlete.

---

## 4. Biomechanical Kinematics & Anomaly Detection

### `GET /analysis/{video_id}`
Extract detailed kinematics including trunk lean, dynamic knee valgus angles, and bilateral symmetry.

### `GET /anomaly/{video_id}`
Detect abnormal kinematic excursions exceeding clinical safety thresholds.

---

## 5. Injury Risk & Corrective Recommendations

### `GET /risk/{video_id}`
Compute multi-factor weighted injury vulnerability score (0–100%) and categorizes risk (`Low`, `Moderate`, `High`).

### `GET /recommendations/{video_id}`
Generate personalized neuromuscular drills, mobility sequences, and strength protocols addressing detected deficits.

---

## 6. Clinical Assessment Reports & Exports

### `GET /reports/{athlete_id}/data`
Fetch complete structured assessment report payload for UI rendering.
- **Query Parameters**: `report_type`: `comprehensive` | `injury_risk` | `biomechanical` | `movement_analysis` | `athlete_performance` | `rehabilitation`.

### `GET /reports/{athlete_id}/export/pdf`
Download print-ready, high-resolution clinical PDF report with executive summary, biometric stats, and clinician signature block.

### `GET /reports/{athlete_id}/export/excel`
Download structured clinical Excel report workbook (`.xlsx`).

### `GET /reports/team/export/excel`
Download multi-sheet Team Movement Screening Workbook covering all assigned athletes on a coach's squad roster.

---

## 7. Notification & Alert System

### `GET /notifications`
List recent injury alerts and movement warnings.
- **Query Parameters**: `unread_only` (bool), `limit` (int, 1-100), `athlete_id` (optional).

### `GET /notifications/summary`
Get counts of total unread, critical, warning, and info notifications.

### `PATCH /notifications/{id}/read`
Mark a specific alert as read.

### `POST /notifications/mark-all-read`
Mark all alerts as read for current user.

---

## 8. Health, Readiness & Observability Endpoints

| Endpoint | Method | Purpose | Response |
| :--- | :--- | :--- | :--- |
| `/api/v1/health` | GET | Basic heartbeat healthcheck | `{"status": "ok", "message": "Backend is healthy"}` |
| `/api/v1/health/live` | GET | Kubernetes / Docker liveness probe | `{"status": "alive", "uptime_seconds": 124.5}` |
| `/api/v1/health/ready` | GET | Dependency readiness probe (PostgreSQL, disk write, ML models) | `{"status": "ready", "checks": {...}}` |
| `/api/v1/health/metrics` | GET | Operational runtime metrics (Uptime, disk storage, memory, DB counters) | `{"service": "AthletiQ", "uptime_seconds": 124.5, "storage": {...}}` |
