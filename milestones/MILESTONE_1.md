# Milestone 1: User Authentication, RBAC & Athlete Profiling

## 🎯 Objective
Establish secure platform foundations including multi-role authentication, role-based access control (RBAC), database schemas, and comprehensive athletic profiling with acute training load tracking.

---

## 🛠 Implemented Components

### 1. Security & Authentication Engine
- **JWT Authentication**: OAuth2 bearer token architecture with 256-bit HMAC-SHA256 signature algorithm.
- **Password Protection**: Salted bcrypt hashing via `passlib.context.CryptContext`.
- **Role-Based Access Control (RBAC)**: Strict 5-role permission framework:
  1. `ATHLETE`: Self movement scanning, personal risk reports, prescribed exercise adherence.
  2. `COACH`: Squad risk overview, team readiness index, acute training load deload triggers.
  3. `PHYSIOTHERAPIST`: Clinical joint vulnerability matrices, 4-phase rehabilitation progressions.
  4. `SPORTS_SCIENTIST`: Biomechanical laboratory analytics, kinematic benchmark distributions.
  5. `ADMINISTRATOR`: User permissions governance, platform audit logs, API latency monitoring.

### 2. Athlete Biometric Profiling
- **Profile Fields**: Unique Athlete ID (`athlete_id`), Sport Category, Playing Position, Age, Height (cm), Weight (kg), Historical Injury Records, and Training Load (0–100%).
- **Acute Training Load Monitoring**: Dynamic risk indicators (>80% acute load triggers high fatigue warnings).
- **Automated Seeding**: Pre-seeds 4 multi-sport athlete profiles (Basketball, Volleyball, Track & Field, Soccer) on startup.

---

## 📁 Source Code Mapping

| File Path | Description |
| :--- | :--- |
| [`backend/app/models/user.py`](file:///C:/Users/MARIYA%20JOHN/sports-injury-ai/backend/app/models/user.py) | SQLAlchemy User model with hashed passwords and role enum |
| [`backend/app/models/athlete.py`](file:///C:/Users/MARIYA%20JOHN/sports-injury-ai/backend/app/models/athlete.py) | Athlete profile table with biometrics and training load |
| [`backend/app/routes/auth.py`](file:///C:/Users/MARIYA%20JOHN/sports-injury-ai/backend/app/routes/auth.py) | `/auth/register` and `/auth/login` token endpoints |
| [`backend/app/routes/athletes.py`](file:///C:/Users/MARIYA%20JOHN/sports-injury-ai/backend/app/routes/athletes.py) | Athlete CRUD operations and roster querying |
| [`backend/app/utils/security.py`](file:///C:/Users/MARIYA%20JOHN/sports-injury-ai/backend/app/utils/security.py) | Cryptographic token creation and bcrypt verification |
| [`backend/app/schemas/user.py`](file:///C:/Users/MARIYA%20JOHN/sports-injury-ai/backend/app/schemas/user.py) | Pydantic v2 validation models for registration and login |
| [`backend/app/schemas/athlete.py`](file:///C:/Users/MARIYA%20JOHN/sports-injury-ai/backend/app/schemas/athlete.py) | Athlete request and response data contracts |

---

## 🧪 Verification & Tests

Run Milestone 1 automated tests:
```bash
cd backend
pytest tests/test_auth.py tests/test_athletes.py -v
```

### Test Cases Verified:
- `test_health_check`: API gateway connectivity and health status.
- `test_home_endpoint`: Root API route responsiveness.
- `test_register_and_login`: User creation, bcrypt verification, and JWT token issuance.
- `test_get_athletes`: Athlete roster retrieval and auto-seeding.
- `test_create_and_get_athlete`: Creating custom athlete profile and fetching by ID.
