# Developer Guide: Starting the Development Servers

A simple, quick-start guide to get the local development servers (Backend & Frontend) up and running on your machine.

---

## Prerequisites

- **Python**: 3.11, 3.12, or 3.13 installed
- **Node.js**: v18+ (Node 20+ recommended) and `npm`
- **PostgreSQL**: Local PostgreSQL running on port `5432` or via Docker Compose

---

## Step 1: Ensure PostgreSQL Is Running

You can use either a local native PostgreSQL instance or Docker:

### Option A: Local Native PostgreSQL (Default)
Make sure PostgreSQL service is running locally on port `5432` with database `injury_detection`.

### Option B: Using Docker (Starts Database Only)
```bash
docker compose up -d
```
*(Starts the `postgres` container in the background).*

---

## Step 2: Database Setup (First Time Only)

From the project root:

```bash
# 1. Run migrations
cd backend
python -m alembic upgrade head

# 2. Seed demo accounts and movement registry
python -m app.seed
cd ..
```

*This creates 5 demo accounts (all with password `demo123`):*
- Admin: `admin@demo.com`
- Coach: `coach@demo.com`
- Athlete: `athlete@demo.com`
- Physiotherapist: `physio@demo.com`
- Sports Scientist: `scientist@demo.com`

---

## Step 3: Start the Backend Server

Open a terminal in the project root:

### Windows (PowerShell):
```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### macOS / Linux (Bash):
```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Health check**: [http://localhost:8000/health](http://localhost:8000/health)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Step 4: Start the Frontend Dev Server

Open a **separate** terminal window in the project root:

### Windows (PowerShell) / macOS / Linux:
```bash
cd frontend
npm run dev
```

- **Web App**: [http://localhost:3000](http://localhost:3000)

---

## Step 5: Log In and Test

1. Open your browser to **[http://localhost:3000](http://localhost:3000)**.
2. Sign in with one of the demo accounts:
   - Email: `coach@demo.com` (or `athlete@demo.com`)
   - Password: `demo123`
3. Navigate to **Videos** to upload or inspect analyzed movement clips.

---

## Quick Reference / Troubleshooting

### Ports In Use
- **Frontend**: Port `3000`
- **Backend API**: Port `8000`
- **PostgreSQL**: Port `5432` (or `5433` for test DB)

### Killing Orphaned Node or Python Processes (Windows PowerShell)
If a previous server didn't shut down and holds a port:
```powershell
# Find process using port 8000 or 3000
Get-NetTCPConnection -LocalPort 8000, 3000 -ErrorAction SilentlyContinue | Select-Object LocalPort, OwningProcess

# Terminate process by PID
Stop-Process -Id <PID> -Force
```

### Running Backend Tests
```bash
cd backend
python -m pytest tests/test_risk_scoring.py tests/test_auto_gemini_baseline.py
```

### Running Frontend Checks
```bash
cd frontend
npx tsc --noEmit
npx eslint src
```

