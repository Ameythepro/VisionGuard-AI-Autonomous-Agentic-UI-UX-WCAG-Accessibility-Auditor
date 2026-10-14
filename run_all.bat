@echo off
set "PATH=C:\Windows\System32;%PATH%"
title VisionGuard AI - Launcher
echo ===================================================
echo Starting VisionGuard AI (Backend + Frontend)...
echo ===================================================
cd /d "%~dp0"
start "VisionGuard AI Backend (:8001)" "%ComSpec%" /k "run_backend.bat"
timeout /t 2 /nobreak >nul 2>&1 || ping -n 3 127.0.0.1 >nul
start "VisionGuard AI Frontend (:5173)" "%ComSpec%" /k "run_frontend.bat"
echo.
echo Both services launched in separate windows!
echo - Backend API:  http://localhost:8001
echo - API Docs:     http://localhost:8001/docs
echo - Frontend UI:  http://localhost:5173
echo.
pause
