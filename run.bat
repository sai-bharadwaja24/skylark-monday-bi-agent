@echo off
title Skylark Drones - Monday.com BI Agent
echo ========================================================
echo Starting Skylark Drones Monday.com BI Agent...
echo Opening in your browser at http://localhost:8501
echo ========================================================

set UV_PATH=%LOCALAPPDATA%\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\uv.exe

if exist "%UV_PATH%" (
    start http://localhost:8501
    "%UV_PATH%" run python web_server.py
) else (
    start http://localhost:8501
    python web_server.py
)
pause
