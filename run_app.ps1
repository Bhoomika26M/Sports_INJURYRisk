Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Starting Sports Injury Risk Detection Platform (M1-M3)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$backendPath = Join-Path $PSScriptRoot "backend"
$frontendPath = Join-Path $PSScriptRoot "frontend"

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backendPath'; python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
Start-Sleep -Seconds 3
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontendPath'; npm run dev -- --host 127.0.0.1 --port 3000"

Write-Host "`nPlatform running:" -ForegroundColor Green
Write-Host " - Frontend:   http://localhost:3000" -ForegroundColor Yellow
Write-Host " - Backend:    http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
