@echo off
set "PATH=C:\Windows\System32;%PATH%"
title VisionGuard AI - Backend Server (:8001)
echo ===================================================
echo Starting VisionGuard AI FastAPI Backend on port 8001...
echo ===================================================
cd /d "%~dp0"
if exist "venv313\Scripts\python.exe" (
    venv313\Scripts\python.exe start_server.py
) else if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe start_server.py
) else (
    python start_server.py
)
pause
