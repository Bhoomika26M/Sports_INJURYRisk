@echo off
echo ============================================================
echo   Starting Sports Injury Risk Detection Platform (M1-M3)
echo ============================================================

start "FastAPI Backend" cmd /k "cd backend && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
timeout /t 3 /nobreak > nul
start "React Frontend" cmd /k "cd frontend && npm run dev -- --host 127.0.0.1 --port 3000"

echo.
echo Platform launched:
echo  - Frontend: http://localhost:3000
echo  - Backend API: http://localhost:8000/docs
echo ============================================================
