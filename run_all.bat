@echo off
title VisionGuard AI - Launcher
echo ===================================================
echo Starting VisionGuard AI (Backend + Frontend)...
echo ===================================================
cd /d "%~dp0"
start "VisionGuard AI Backend (:8001)" cmd /k "run_backend.bat"
timeout /t 2 /nobreak >nul
start "VisionGuard AI Frontend (:5173)" cmd /k "run_frontend.bat"
echo.
echo Both services launched in separate windows!
echo - Backend API:  http://localhost:8001
echo - API Docs:     http://localhost:8001/docs
echo - Frontend UI:  http://localhost:5173
echo.
pause
