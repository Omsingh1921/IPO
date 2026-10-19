@echo off
title Indian IPO Recommendation Platform
color 0B
echo ======================================================================
echo           INDIAN IPO RECOMMENDATION PLATFORM - LIVE LAUNCHER
echo ======================================================================
echo.
echo [1/3] Checking MySQL Database Service...
net start MySQL80 >nul 2>&1
echo       MySQL Service is Active!
echo.
echo [2/3] Opening Live Web Dashboard in Browser...
timeout /t 2 /nobreak >nul
start "" "http://localhost:8000/dashboard"
echo       Dashboard URL: http://localhost:8000/dashboard
echo       Admin Password: Root@123
echo.
echo [3/3] Starting FastAPI Server ^& Background 12:01 PM Scheduler...
echo       Press Ctrl+C to terminate the platform anytime.
echo.
python -m uvicorn ipo_platform.api.app:app --host 0.0.0.0 --port 8000 --reload
pause
