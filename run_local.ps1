# VisionGuard AI - PowerShell Launcher
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "Starting VisionGuard AI Local Services..." -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

$root = $PSScriptRoot
$env:PATH = "C:\Windows\System32;$root\node-v22.14.0-win-x64;" + $env:PATH

# Start backend in new window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root'; & '.\venv313\Scripts\python.exe' start_server.py"

Start-Sleep -Seconds 2

# Start frontend in new window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend_ui\visionguard-ui'; `$env:PATH = '$root\node-v22.14.0-win-x64;' + `$env:PATH; npm run dev"

Write-Host "Both services launched!" -ForegroundColor Green
Write-Host "Backend API:  http://localhost:8001" -ForegroundColor Yellow
Write-Host "Frontend UI:  http://localhost:5173" -ForegroundColor Yellow
