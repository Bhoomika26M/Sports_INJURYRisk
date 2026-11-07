# Production Deployment Guide — Sports Injury Risk Detection Platform

This document describes how to deploy the Sports Injury Risk Detection Platform in a hardened production environment.

---

## 1. Environment & Secrets Management

All production settings are configured via environment variables. Copy `.env.example` to `.env` on your deployment host:

```bash
cp .env.example .env
```

### Critical Production Invariants:
1. **`ENVIRONMENT=production`**:
   The backend automatically validates this flag upon boot. If `ENVIRONMENT=production` and `JWT_SECRET_KEY` is left as the default placeholder, the application refuses to start and raises an immediate `ValueError`:
   ```python
   # Verified in app/config.py
   if self.jwt_secret_key == _DEFAULT_JWT_SECRET and self.environment.lower() == "production":
       raise ValueError("JWT_SECRET_KEY is still the placeholder value: set a long random secret before running with ENVIRONMENT=production")
   ```
2. **`JWT_SECRET_KEY`**:
   Generate a 64-character high-entropy secret using OpenSSL or Python:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
3. **Database Credentials**:
   Change `POSTGRES_PASSWORD` from `changeme_in_production` to a secure password.

---

## 2. Docker Compose Production Deployment

The platform provides a dedicated production compose file: `docker-compose.prod.yml`.

### Step 1: Pre-flight Verification
Ensure required secrets are exported:
```bash
export POSTGRES_PASSWORD="your-strong-db-password"
export JWT_SECRET_KEY="your-cryptographically-random-key"
export FRONTEND_URL="https://app.injury-detection.com"
```

### Step 2: Build and Launch
```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### Step 3: Apply Migrations & Seed Admin
```bash
docker compose -f docker-compose.prod.yml exec backend python -m alembic upgrade head
docker compose -f docker-compose.prod.yml exec backend python -m app.seed
```

---

## 3. Native Host / Systemd Deployment

### Prerequisites
- Python 3.12+ with `ffmpeg`, `libgl1`, `libglib2.0-0`
- Node.js 20+
- PostgreSQL 15 or 16

### Backend Service Setup
1. Install CPU torch first (avoids several gigabytes of unnecessary CUDA dependencies):
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
   pip install -r requirements.txt
   ```
2. Run database migrations:
   ```bash
   python -m alembic upgrade head
   ```
3. Run with production ASGI server:
   ```bash
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000
   ```

### Frontend Next.js Setup
```bash
cd frontend
npm ci
npm run build
npm run start -p 3000
```

---

## 4. Verification & Health Monitoring

- **Application Health:**
  ```bash
  curl -f http://localhost:8000/health
  # {"status": "ok"}
  ```
- **Database Connectivity:**
  ```bash
  curl -f http://localhost:8000/health/db
  # {"status": "ok", "database": "connected"}
  ```
- **Pose Engine Verification:**
  Run the end-to-end check script against the running instance:
  ```bash
  python backend/scripts/e2e_http_check.py http://localhost:8000 path/to/squat.mp4 squatting sagittal
  ```
