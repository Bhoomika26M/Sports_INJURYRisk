# ROLES_AND_PERMISSIONS.md — Multi-Tenant Access Control & User Roles

This document defines the Role-Based Access Control (RBAC), multi-tenant data boundaries, permission matrix, and role-specific dashboard capabilities of the Sports Injury Risk Detection Platform.

---

## 1. Role Overview & Philosophy

The platform supports 5 distinct user roles (`UserRole` in [models.py](file:///c:/Users/USER/Desktop/injury%20detection/backend/app/modules/users/models.py)):

1. **`athlete`** — The performer. Complete data privacy. May view and manage only their own personal assessments, training load, and injury records.
2. **`coach`** — Team / squad manager. Responsible for an assigned roster of athletes (`athlete.coach_id == user.id`). Can upload videos for squad members, monitor workload spikes, and review risk summaries.
3. **`physiotherapist`** — Clinical specialist. Cross-squad clinical visibility. Logs medical history, reviews bilateral asymmetry (LSI), evaluates joint angles against recovery milestones, and tracks rehab progression.
4. **`sports_scientist`** — Biomechanist and workload analyst. Deep-dive analytical access. Inspects raw kinematic waveforms, population baseline distributions, fatigue drift metrics, and exports datasets for research.
5. **`admin`** — System administrator. User lifecycle management, baseline recalibration triggers, audit logging, and platform health oversight.

---

## 2. Access Control Matrix

| Feature / Resource | Athlete | Coach | Physiotherapist | Sports Scientist | Admin |
|---|:---:|:---:|:---:|:---:|:---:|
| **View Personal Dashboard** | Self only | Team Roster | Clinical Overview | Research Overview | System Overview |
| **View Athlete Profiles** | Self only | Assigned squad | All athletes | All athletes | All athletes |
| **Upload Videos** | Self only | Assigned squad | All athletes | All athletes | All athletes |
| **View Video Biomechanics & Overlays** | Self only | Assigned squad | All athletes | All athletes | All athletes |
| **View Risk Scores & Recommendations** | Self only | Assigned squad | All athletes | All athletes | All athletes |
| **Download Reports (PDF / Excel / CSV)** | Self only | Assigned squad | All athletes | All athletes | All athletes |
| **Log Training Load (RPE / Duration)** | Self only | Assigned squad | Read-only | Read-only | Manage all |
| **Log Injury History (Medical records)** | View self | View squad | Create / Update | View all | Manage all |
| **Trigger Baseline Recomputation** | No | No | No | Read/Inspect | Yes |
| **Manage Users & Role Assignment** | No | No | No | No | Yes |

---

## 3. Dedicated Dashboard Capabilities

### Athlete (`athlete@demo.com`)
- **Focus**: Personal readiness, self-monitoring, injury prevention tips.
- **Key Views**:
  - **Readiness Card**: Current risk status (Low / Moderate / High) and acute:chronic workload balance (ACWR).
  - **My Recent Sessions**: Recent video uploads with thumbnail, movement type, and processing status.
  - **Symmetry & Mechanics**: Easy-to-understand left/right balance percentage and joint range of motion.
  - **Action Items**: Plain-language preventive recommendations (e.g. hamstring eccentric strengthening, landing soft).

### Coach (`coach@demo.com`)
- **Focus**: Squad readiness, availability, and training session planning.
- **Key Views**:
  - **Team Roster Grid**: Real-time status cards for each assigned athlete with risk badges.
  - **High-Risk Alerts**: Immediate visual flag for athletes entering high/critical risk zones or load spikes.
  - **Batch Video Ingestion**: Fast upload workflow allowing coaches to upload training clips for any squad member.
  - **Squad Workload Overview**: Group ACWR trend tracking to adjust weekly practice intensity.

### Physiotherapist (`physio@demo.com`)
- **Focus**: Injury rehabilitation, screening flags, bilateral symmetry.
- **Key Views**:
  - **Clinical Screening Panel**: Dedicated filters for ACL, hamstring, ankle, shoulder, and back vulnerability.
  - **Medical History Ledger**: Form to document past injuries, severity, recovery dates, and unresolved conditions.
  - **Limb Symmetry Index (LSI)**: Objective comparison of left vs. right peak joint angles with literature context.
  - **Clinical Export**: One-click generation of PDF clinical reports for medical consultations.

### Sports Scientist (`scientist@demo.com`)
- **Focus**: Quantitative biomechanics, baseline anomaly modeling, fatigue mechanics.
- **Key Views**:
  - **Multi-Angle Waveforms**: Interactive frame-by-frame joint angle graphs (flexion, extension, trunk lean, rotation).
  - **Population Baseline Explorer**: Visual distribution of population baselines, Isolation Forest scores, and robust-z deviations.
  - **Fatigue & Consistency Tracking**: Repetition coefficient of variation (CV %) and kinematic drift direction/percentage.
  - **Raw Data Export**: Direct download of raw frame-level CSVs and Excel multi-sheet analytical workbooks.

### Admin (`admin@demo.com`)
- **Focus**: Platform integrity, tenant management, baseline governance.
- **Key Views**:
  - **User & Roster Provisioning**: Create accounts, assign athletes to coaches, configure role permissions.
  - **Baseline Governance**: Monitor baseline video counts per movement type and trigger recalibration debounced jobs.
  - **System Health**: Worker queue health, model pipeline latency, storage volume status.

---

## 4. Enforcement Architecture

### Backend Enforcement (FastAPI + SQLAlchemy)
- Every request passes through authentication dependencies (`get_current_user` in [auth.py](file:///c:/Users/USER/Desktop/injury%20detection/backend/app/modules/users/auth.py)).
- Router-level permission gates verify role scope before executing queries:
  ```python
  def _can_access_athlete(user: User, athlete: Athlete) -> bool:
      if user.role in (UserRole.admin, UserRole.physiotherapist, UserRole.sports_scientist):
          return True
      if user.role == UserRole.coach and athlete.coach_id == user.id:
          return True
      if user.role == UserRole.athlete and athlete.user_id == user.id:
          return True
      return False
  ```
- If an unauthorized user attempts to view or upload for an athlete outside their scope, the backend immediately raises:
  `HTTP 403 Forbidden: {"code": "INSUFFICIENT_PERMISSIONS", "message": "Access denied"}`.

### Frontend Enforcement (Next.js 16 App Router)
- **Edge Routing & Middleware**: Inspects `session_hint` cookie and user token to guard authenticated routes.
- **Role-Aware Shell**: The navigation bar, header avatar, and page elements adapt based on `user.role`.
- **Query Gating**: TanStack Query hooks fetch only role-accessible data, handling 403 responses gracefully with clear user guidance.

### Security Guarantees
- **No Token Storage in LocalStorage**: JWT refresh tokens are stored in `httpOnly`, `Secure`, `SameSite=Lax` cookies.
- **Password Protection**: Passwords hashed with `Argon2id` (memory-hard, resistant to GPU attacks).
- **Tenant Isolation**: Athlete data is strictly isolated by foreign key relationships in PostgreSQL.
