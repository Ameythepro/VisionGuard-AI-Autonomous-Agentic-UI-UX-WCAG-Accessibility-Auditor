@echo off
set "PATH=C:\Windows\System32;%~dp0node-v22.14.0-win-x64;%PATH%"
title VisionGuard AI - Frontend UI (:5173)
echo ===================================================
echo Starting VisionGuard AI Frontend on http://localhost:5173...
echo ===================================================
cd /d "%~dp0"
cd frontend_ui\visionguard-ui
npm.cmd run dev
pause
