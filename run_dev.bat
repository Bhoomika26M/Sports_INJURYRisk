@echo off
title Sports Injury AI Launcher
echo ========================================================
echo   Starting Sports Injury AI Platform
echo   - Backend:  http://127.0.0.1:8000 (FastAPI Docs: /docs)
echo   - Frontend: http://localhost:5173 (React Vite)
echo ========================================================

start "Sports Injury AI - Backend" cmd /k "cd /d %~dp0backend && call venv\Scripts\activate && uvicorn app.main:app --reload --port 8000"
start "Sports Injury AI - Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo Servers launched in separate windows!
echo You can open your browser at: http://localhost:5173
pause
