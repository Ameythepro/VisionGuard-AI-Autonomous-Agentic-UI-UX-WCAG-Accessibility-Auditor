@echo off
title VisionGuard AI - Frontend UI (:5173)
echo ===================================================
echo Starting VisionGuard AI Frontend on http://localhost:5173...
echo ===================================================
cd /d "%~dp0"
set "PATH=%~dp0node-v22.14.0-win-x64;%PATH%"
cd frontend_ui\visionguard-ui
npm run dev
pause
