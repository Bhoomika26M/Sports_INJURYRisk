# Sports Injury Risk Detection Platform — Comprehensive Technical Specification

This document provides a comprehensive end-to-end technical reference for the Sports Injury Risk Detection platform. It covers the full technology stack, computer vision and machine learning architecture, clinical risk rules, database modeling, workflows, and backend-enforced security mechanisms.

---

## 1. High-Level System Architecture & Overview

The **Sports Injury Risk Detection Platform** is a specialized computer vision and biomechanical analysis system designed to assess injury risk from monocular RGB video feeds (e.g., standard smartphone or camera footage). It couples deep-learning object detection and human pose estimation with kinematics calculations, clinical injury heuristics, and multi-tenant Role-Based Access Control (RBAC).

```
┌────────────────────────────────────────────────────────────────────────┐
│                   Frontend (React 18 + Vite + Tailwind CSS)            │
│  - Dual Video Sync / Comparison Player   - Biomechanical Charts        │
│  - Real-Time Analysis Progress Polling  - Care Team / Access Controls │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTPS / REST (Axios + JWT)
┌───────────────────────────────────▼────────────────────────────────────┐
│                  Backend (FastAPI - Python 3.11/3.12)                   │
│  - Middleware: JWT Authn, Session Revocation Check, Custom Rate Limiter│
│  - RBAC Guard: Role-checker dependencies & IDOR protection layer        │
│  - Async Worker: FastAPI BackgroundTasks execution pipeline            │
│  - Media Server: Partial Content streaming (HTTP 206 Byte Ranges)     │
└───────────────────┬───────────────────────────────┬────────────────────┘
                    │                               │
┌───────────────────▼──────────────────┐   ┌────────▼────────────────────┐
│      Video CV / ML Pipeline          │   │      Relational Database    │
│  - YOLO11n (Ultralytics)             │   │  - SQLite (Dev/Test)        │
│  - ByteTrack Multi-Object Tracking   │   │  - PostgreSQL (Production)  │
│  - Dynamic ROI Crop + BlazePose      │   │  - SQLAlchemy 2.0 ORM       │
│  - Savitzky-Golay Temporal Filter    │   │  - Alembic Migrations       │
│  - Kinematic Angles & Symmetry Engine│   └─────────────────────────────┘
│  - Explainable Risk Scoring Engine   │
│  - Fragmented MP4 (imageio-ffmpeg)   │
└──────────────────────────────────────┘
```

---

## 2. Full Technology Stack & Library Selection Rationale

### 2.1 Backend Technologies

| Technology / Library | Version | Role in Architecture | Engineering Rationale / Why Chosen |
| :--- | :--- | :--- | :--- |
| **Python** | `3.11 / 3.12` | Core backend runtime | Robust ecosystem for machine learning, numerical computation, and computer vision libraries alongside asynchronous ASGI web frameworks. |
| **FastAPI** | `0.104.1` | Web framework & REST API | High throughput via Starlette/ASGI; native async I/O; automatic OpenAPI/Swagger schema documentation; dependency injection for auth/security guards. |
| **Uvicorn** | `0.24.0` | ASGI Web Server | Lightning-fast asynchronous server implementation for Python based on `uvloop` and `httptools`. |
| **SQLAlchemy** | `2.0.23` | Object-Relational Mapper (ORM) | Type-safe, production-standard SQL abstraction layer providing complete control over queries, joins, and transactions. |
| **Alembic** | `1.12.1` | Database migration engine | Declarative schema migration tracker tied directly to SQLAlchemy models to ensure reproducible schema evolution across environments. |
| **Pydantic & Settings** | `2.5.0` / `2.1.0` | Data validation & configuration | High-performance schema validation, type coercion, and environment variable parsing powered by a Rust core (`pydantic-core`). |
| **python-jose** | `3.3.0` | Cryptographic JWT signing | Implements JSON Web Signature (JWS) and token encoding/decoding using HMAC-SHA256 (`HS256`). |
| **Passlib & bcrypt** | `1.7.4` / `4.0.1` | Password hashing | Industry-standard salted cryptographic hashing (`bcrypt`) with adjustable work factor (cost 12) resistant to GPU brute-force attacks. |
| **python-multipart** | `0.0.6` | Streaming file upload parser | Streaming parser for `multipart/form-data` uploads (video files up to 500 MB). |
| **OpenCV (`opencv-python-headless`)** | Latest | Video frame decoding & rendering | Industry standard for computer vision; headless variant minimizes Docker container footprint by omitting GUI dependencies. |
| **NumPy & SciPy** | Latest | Vector math & signal processing | Vectorized geometric operations, dot products, angular velocity derivatives, and polynomial curve filtering. |
| **imageio-ffmpeg** | `0.6.0` | Video muxing & stream encoding | Bundles self-contained `ffmpeg` binaries to encode annotated frames into fragmented MP4 containers for live streaming. |
| **Ultralytics (YOLO11n)** | Latest | Person detection & tracking | High-speed real-time bounding box extraction for human subjects. |
| **MediaPipe** | `>=0.10.14` | 3D/2D Human Pose Estimation | Sub-millisecond landmark estimation providing 33 anatomical keypoints. |

### 2.2 Frontend Technologies

| Technology / Library | Version | Role in Architecture | Engineering Rationale / Why Chosen |
| :--- | :--- | :--- | :--- |
| **React** | `18.2.0` | UI framework | Component-driven architecture, virtual DOM reconciliation, rich ecosystem for data visualization. |
| **Vite** | `5.0.8` | Frontend build tool | Near-instant HMR (Hot Module Replacement) and optimized production rollup bundling. |
| **Tailwind CSS** | `3.3.6` | Utility-first CSS framework | Rapid UI construction, zero runtime CSS overhead, responsive layouts, consistent design tokens. |
| **React Router DOM** | `6.20.0` | Client-side routing | Route protection, nested layouts, and programmatic history navigation. |
| **Axios** | `1.6.2` | HTTP Client | Request/response interceptor pipeline (automatically injects JWT tokens and handles global 401 unauth session expiry). |
| **Recharts** | `3.10.1` | SVG Data Visualizations | Declarative React charting library used for time-series joint angle curves, movement symmetry, and trendlines. |

---

## 3. Computer Vision & Machine Learning Architecture

The pipeline processes video footage to produce real-time pose metrics, kinematic measurements, and clinical injury findings.

### Detailed Pipeline Breakdown

```
[Input Video (MP4/MOV/AVI)]
          │
          ▼
[OpenCV Frame Capture & Downscaling] (Decodes at 15 FPS sampling)
          │
          ▼
[YOLO11n Person Detection] (Ultralytics nano model, COCO Class 0)
          │
          ▼
[ByteTrack Multi-Object Tracking] (Maintains persistent athlete ID across occlusions)
          │
          ▼
[Dynamic ROI Extraction & Padding] (Isolates athlete bounding box with 15% margin)
          │
          ▼
[MediaPipe BlazePose] (33 3D/2D Landmarks extracted from normalized ROI)
          │
          ▼
[Coordinate Un-mapping] (Projects normalized ROI coordinates back to full-frame space)
          │
          ▼
[Savitzky-Golay Temporal Smoothing] (5-frame window, 2nd-order polynomial to remove jitter)
          │
          ▼
[Skeleton Normalization] (Scale/translation invariant normalization relative to torso height)
          │
          ▼
[Biomechanical Calculator] (Joint angles, knee valgus proxy, trunk lean, angular velocities)
          │
          ▼
[Explainable Risk Engine] (Rule-based heuristics, anatomical knowledge base, penalty aggregation)
          │
          ▼
[Dual Video Synchronization & Fragmented MP4 Muxing] (imageio-ffmpeg fast preview)
```

### 3.1 Object Detection: YOLO11n (Ultralytics)
- **Role**: Identifies human bounding boxes (`COCO class 0: person`).
- **Why YOLO11n**: The `nano` variant provides high inference speeds on CPU/low-tier GPUs without sacrificing the localization precision required for subsequent pose estimation.
- **Optimization**: To avoid processing high-resolution (e.g., 4K) footage directly through convolutional layers, frames are downscaled to `DETECT_MAX_WIDTH: 640px` before inference, and the resulting bounding boxes are scaled back up.

### 3.2 Multi-Object Tracking: ByteTrack
- **Role**: Tracks athletes across consecutive frames, preserving identity even when other individuals enter the background or brief occlusions occur.
- **Why ByteTrack**: Rather than discarding low-confidence detection boxes, ByteTrack matches both high-confidence and low-confidence detections using Kalman filtering and motion similarity (IoU), preserving trajectory continuity.

### 3.3 Pose Estimation: MediaPipe BlazePose
- **Role**: Predicts 33 high-fidelity anatomical keypoints (including eyes, ears, shoulders, elbows, wrists, hips, knees, ankles, heels, and toes).
- **Why BlazePose over MoveNet Lightning**: MoveNet Lightning only provides 17 COCO keypoints (lacking foot indices and heels, which are critical for ankle dorsiflexion and foot alignment). BlazePose provides 33 landmarks, and its `.task` bundle integrates seamlessly with modern Python runtimes (Python 3.11/3.12).
- **Optimization (Parallel Workers)**: The pipeline uses a `ParallelPosePool` to distribute chunked frame pose inference across multiple CPU worker instances.

### 3.4 Signal Processing & Temporal Smoothing: Savitzky-Golay Filter
- **Library**: `scipy.signal.savgol_filter`
- **Role**: Video pose estimation often exhibits frame-to-frame landmark flutter due to compression artifacts or edge ambiguity. A 5-frame window with a 2nd-order polynomial fits local landmark trajectories, eliminating high-frequency noise while preserving true physiological acceleration peaks.

### 3.5 Biomechanical Kinematic Calculations
- **Library**: `numpy` / `scipy`
- **Computed Metrics**:
  - **Knee Flexion/Extension**: Angle between hip-knee-ankle vectors ($\arccos$ dot product).
  - **Hip Flexion/Extension**: Angle between shoulder-hip-knee vectors.
  - **Trunk Lean**: Angle between vertical axis and the midpoint-hip to midpoint-shoulder vector.
  - **Dynamic Knee Valgus (Proxy)**: Ratio/angle of knee displacement relative to ankle-hip alignment in the coronal plane (indicator for ACL strain).
  - **Bilateral Asymmetry**: Percentage difference between left and right limb angles ($|L - R| / \max(L, R) \times 100$).
  - **Angular Velocity**: Numerical derivative ($\Delta \theta / \Delta t$) of joint angles over time.

### 3.6 Video Visualization & Streaming: `imageio-ffmpeg`
- **Role**: Muxes annotated skeleton overlays into fragmented MP4 (`frag_keyframe+empty_moov`).
- **Why**: Standard MP4 files write the metadata atom (`moov`) at the end of the file, preventing playback until processing finishes. Fragmented MP4 allows the frontend browser video player to stream and play back processed segments while subsequent chunks are still being calculated.

---

## 4. Explainable Risk Scoring Engine & Clinical Rules

The risk engine does not rely on an opaque black-box classifier. Instead, it uses an **Explainable Rule-Based Clinical Engine** (`app/risk/engine.py` & `app/risk/knowledge_base.py`):

1. **Risk Score Derivation ($0 - 100$)**:
   $$\text{Score} = w_1(\text{Movement Quality}) + w_2(\text{Symmetry}) + w_3(\text{Alignment}) + w_4(\text{Control}) + \text{Penalties}$$
   - *Movement Quality ($40\%$)*: Depth, joint range of motion (ROM), rep smoothness.
   - *Bilateral Symmetry ($25\%$)*: Left vs. right limb coordination differences.
   - *Dynamic Alignment ($20\%$)*: Coronal knee valgus collapse, lateral trunk deviation.
   - *Motor Control ($15\%$)*: Angular velocity spikes and stability at the bottom of movements.
2. **Clinical Severity Thresholds**:
   - `0 - 24`: Low Risk
   - `25 - 49`: Moderate Risk
   - `50 - 74`: High Risk
   - `75 - 100`: Critical Risk
3. **Anatomical Findings & Corrective Feedback**:
   Each threshold violation generates a structured `RiskFinding` containing:
   - Specific muscle groups involved (primary drivers, overactive stabilizers, underactive muscles).
   - Biomechanical injury mechanism (e.g., "Excessive knee valgus during landing phase induces tensile stress on the Anterior Cruciate Ligament (ACL)").
   - Actionable corrective exercise drills (e.g., banded monster walks, single-leg Romanian deadlifts).

---

## 5. Database Architecture & Storage Strategy

### 5.1 Database Engine Selection
- **Development/Testing**: SQLite (`sqlite:///./test.db` / `e2e_check.db`) for rapid local bootstrapping and isolated CI/CD test runs without external server dependencies.
- **Production**: PostgreSQL (`psycopg2-binary` driver) running in Docker/cloud environments for robust concurrency, ACID transactions, and row-level locking.
- **ORM & Migrations**: SQLAlchemy 2.0 with Alembic revision tracking.

### 5.2 Schema & Entity Relationships

```
┌──────────────┐         1:N         ┌───────────────┐
│    users     ├─────────────────────┤   sessions    │
└──────┬───────┘                     └───────────────┘
       │ 1:1 (optional link)
       ▼
┌──────────────┐         1:N         ┌───────────────┐
│   athletes   ├─────────────────────┤    videos     │
└──────┬───────┘                     └───────┬───────┘
       │                                     │ 1:1
       │ 1:N                                 ▼
       │                             ┌──────────────────────┐
       ├─────────────────────────────┤ pose_analyses        │
       │                             └───────┬──────────────┘
       │                                     │ 1:1
       │                                     ▼
       │                             ┌──────────────────────┐
       │                             │ biomechanical_       │
       │                             │ analyses             │
       │                             └──────────────────────┘
       │ 1:N
       ▼
┌──────────────────────────┐
│    access_invitations    │  (Athlete ↔ Professional Care Team Grant)
└──────────────────────────┘
```

### 5.3 Stored Data Breakdown
1. **`users`**: Account credentials (`email`, `hashed_password`), `role` (`athlete`, `coach`, `physiotherapist`, `sports_scientist`, `administrator`), `full_name`, `is_active`, `google_id`.
2. **`sessions`**: Server-side session store (`jti`, `user_id`, `expires_at`, `revoked`). Enables immediate server-side revocation on logout or password changes.
3. **`password_otps`**: Stores SHA-256 HMAC hashed 6-digit one-time passcodes, purpose scopes (`recovery` vs `change`), expiration timestamps, and attempt counters.
4. **`athletes`**: Physical metrics (`age`, `height`, `weight`, `sport_type`, `position`, `injury_history`, `training_load`, `deleted_at`).
5. **`access_invitations`**: Explicit permission mappings linking an `athlete_id` to a `professional_user_id` with statuses: `pending`, `accepted`, `rejected`, `revoked`.
6. **`videos`**: Upload records (`filepath`, `annotated_filepath`, `processing_status`, `duration`, `fps`, `resolution`).
7. **`pose_analyses`**: Keypoint coordinates JSON, tracking statistics, detection confidence averages.
8. **`biomechanical_analyses`**: Joint angle sequences, symmetry indices, peak velocities, and movement quality scores.
9. **`movement_windows`**: Segmented exercise repetition intervals (start frame, peak frame, end frame).
10. **`analysis_snapshots`**: Rolling baselines and historical trend snapshots.

---

## 6. Security Architecture & Role-Based Access Control (RBAC)

The security implementation adheres to **Zero-Trust** and **Principle of Least Privilege** designs, guarding against OWASP Top 10 vulnerabilities (including Insecure Direct Object References - IDOR).

### 6.1 Authentication & Session Management
- **Stateless Tokens with Stateful Revocation**:
  Authentication issues a signed JWT (`HS256`) containing `sub` (email), `exp` (30-minute expiry), and `jti` (unique UUID session ID).
  On every request, the backend dependency `get_current_user`:
  1. Cryptographically validates token signature and unexpired state.
  2. Queries the `sessions` table in the database to verify that `revoked == False` and `expires_at > now()`.
  3. Rejects revoked tokens immediately, mitigating the standard vulnerability of purely stateless JWTs.
- **Password Hashing**: Passlib bcrypt (work cost factor 12) with random salts.
- **HMAC-SHA256 OTP Password Recovery**:
  Instead of emailing insecure raw tokens or reset links, the system issues a single-use 6-digit OTP. The database never stores plaintext OTPs; it stores `hmac.new(SECRET_KEY, code.encode(), hashlib.sha256).hexdigest()`. Brute-force attacks are thwarted by limiting attempts to 5 and expiring codes after 5 minutes.

### 6.2 Supported System Roles
- `athlete`: An individual athlete tracking their biomechanics.
- `coach`: Oversees athletic performance and movement form.
- `physiotherapist`: Assesses injury risks, rehabilitation, and joint stress.
- `sports_scientist`: Analyzes kinematic data and baseline trends.
- `administrator`: Full administrative platform management.

### 6.3 Backend Enforced Access Control & Athlete Profile Partitioning

Data isolation is strictly enforced at the database query layer in the FastAPI backend:

```
Client Request
      │
      ▼
FastAPI Route Dependency: `get_current_active_user` (Verifies JWT & Session)
      │
      ▼
Role Verification Dependency: `require_role(...)`
      │
      ▼
IDOR / Access Partitioning Check: `VideoService.check_athlete_access(user, athlete_id, db)`
      │
      ├── Case A: User is 'athlete'
      │     └── Query: `athlete.user_id == current_user.id`
      │           ├── TRUE: Allow access
      │           └── FALSE: Raise 403 Forbidden & Log Security Audit Event
      │
      ├── Case B: User is 'administrator'
      │     └── Allow access across all records
      │
      └── Case C: User is 'coach', 'physiotherapist', or 'sports_scientist'
            └── Query `access_invitations` table:
                  `athlete_id == athlete_id AND professional_user_id == current_user.id AND status == 'accepted'`
                  ├── FOUND: Allow access to athlete data & video feeds
                  └── NOT FOUND: Raise 403 Forbidden & Log Security Audit Event
```

#### Code Implementation Details
1. **Athlete Listing Query Partitioning** (`app/services/athlete_service.py`):
   When an athlete calls `GET /api/v1/athletes/`, the service does not return all rows. It executes:
   ```python
   if current_user.role == "athlete":
       return db.query(Athlete).filter(Athlete.user_id == current_user.id).all()
   ```
2. **Care Team Invitation Isolation** (`app/api/routes/invitations.py`):
   An athlete can browse active professionals (`coach`, `physiotherapist`, `sports_scientist`) and click **Invite**. An `AccessInvitation` is created in state `pending`. The professional must log in and accept the invitation before access is granted.
3. **Revocation**:
   The athlete can revoke access at any time. When revoked, the professional's queries for that athlete's videos, risk profiles, and history immediately return `403 Forbidden`.
4. **Graceful Deletion Window**:
   When an admin marks an athlete for deletion, a 30-day grace period is initiated (`deleted_at`), locking new video uploads while retaining historical records for review before permanent purge.

### 6.4 Additional Hardening Measures
- **Path Traversal & Malicious File Upload Prevention**:
  Uploaded filenames are discarded. The backend generates cryptographically secure names using `secrets.token_urlsafe(32) + validated_extension`.
- **HTTP 206 Partial Content Streaming**:
  Video streaming endpoints implement standard HTTP Byte-Range requests (`Range: bytes=start-end`), preventing memory exhaustion when users scrub through large video files.
- **In-Memory Sliding-Window Rate Limiting**:
  Applied to authentication and OTP routes (`RateLimitDependency(max_requests=5, window_seconds=60)`) to mitigate brute-force credential stuffing.
- **Security Audit Logger**:
  Events such as failed logins, privilege escalation attempts, and unauthorized access attempts are structured and piped to `security_audit` logs without logging plaintext credentials or tokens.

---

## 7. Complete System Workflows

### Workflow 1: Athlete Registration & Onboarding
1. User visits `/register` and submits account details. Public registration defaults strictly to the `athlete` role.
2. In the same transaction, an `Athlete` record is created linking `athlete.user_id = user.id` alongside physiological metadata (height, weight, sport, position).
3. The server generates a JWT session and redirects the user to `/dashboard`.

### Workflow 2: Video Upload & Asynchronous Processing
1. The user selects an athlete and an activity type (e.g., `squat`, `jump`, `running`) and uploads an MP4/MOV file.
2. The endpoint `POST /api/v1/videos` validates file headers, safe extensions, and enforces a 500 MB size cap.
3. The file is saved to the storage directory, and a `Video` record is inserted with `processing_status = 'pending'`.
4. The endpoint launches a background worker via FastAPI's `BackgroundTasks` (`_run_video_processing`) and returns `201 Created` with the video ID.
5. The frontend polls `GET /api/v1/videos/{id}`:
   - Worker updates progress in memory (`detecting` $\rightarrow$ `tracking` $\rightarrow$ `estimating_pose` $\rightarrow$ `computing_biomechanics`).
   - The browser displays real-time progress percentages and preview frames.
6. Once complete, `processing_status` transitions to `'completed'`.

### Workflow 3: Kinematic Analysis & Risk Inspection
1. The user navigates to `/videos/{id}/analysis`.
2. The page renders the synchronized dual-player view: the raw input footage and the skeleton-annotated, smart-framed overlay.
3. The Recharts component renders joint angle trajectories, rep-by-rep breakdown cards, and highlighted risk alerts (e.g., knee valgus collapse warnings, excessive forward lean).
4. Corrective drills and muscle involvement summaries are rendered directly from the explainable findings schema.

### Workflow 4: Professional Care Team Access Delegation
1. An athlete visits their Care Team management tab.
2. The athlete sends an access invitation to a verified sports scientist or physiotherapist.
3. The professional logs in, navigates to their Invitations inbox, and clicks **Accept**.
4. The professional can now view that specific athlete in their Athlete Directory and access all relevant video analyses, baseline comparisons, and risk history.

---

## 8. Technical Questions & Full-Stack / ML Interview Defense Guide

### Q1: Why use MediaPipe BlazePose instead of MoveNet Lightning?
> **Answer**: MoveNet Lightning only provides 17 COCO keypoints, omitting foot, heel, and toe landmarks. Assessing lower-extremity athletic risk (such as knee valgus, ankle pronation, and ground contact mechanics) requires foot orientation landmarks. MediaPipe BlazePose provides 33 3D/2D anatomical landmarks. Additionally, BlazePose tasks are fully compatible with modern Python 3.11/3.12 environments without legacy TensorFlow binary conflicts.

### Q2: Why run YOLO11 before running pose estimation?
> **Answer**: Standard pose estimators running on raw, wide-angle full frames often suffer from low resolution on the athlete and can mistakenly latch onto background spectators or trainers. By pairing YOLO11n person detection with ByteTrack, the pipeline extracts a tightly padded bounding box around the target athlete. MediaPipe receives a normalized Region of Interest (ROI), resulting in higher keypoint accuracy and reduced background interference.

### Q3: Why is video processing handled via FastAPI BackgroundTasks instead of Celery/Redis?
> **Answer**: For single-instance deployments, `BackgroundTasks` avoids the infrastructure overhead of managing an external message broker (RabbitMQ/Redis) and separate worker daemons. The architecture isolates the execution logic inside `VideoProcessingService`, making it simple to lift and shift the background function into a distributed task queue (such as Celery, ARQ, or AWS SQS) as scaling demands increase.

### Q4: How is Insecure Direct Object Reference (IDOR) prevented?
> **Answer**: Access checks are never delegated to the frontend or inferred from client parameters. In the backend, `VideoService.check_athlete_access()` explicitly resolves the authenticated `user.id` against `athlete.user_id`. For coaches and physiotherapists, access requires a verified record in the `access_invitations` table with status `accepted`. Any attempt to access unauthorized IDs raises an HTTP 403 and writes to the security audit log.

### Q5: How is video streaming handled without exhausting backend server RAM?
> **Answer**: Media delivery utilizes standard HTTP 206 Partial Content range requests (`app/api/media.py`). Rather than reading entire 500 MB files into memory, the backend streams only the requested byte chunk (`bytes=start-end`), supporting seek operations in the browser player with low memory overhead. Furthermore, annotated videos are encoded as fragmented MP4s (`imageio-ffmpeg`), enabling continuous streaming before encoding finishes.
