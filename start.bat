@echo off
title SMART AI IoT - Dashboard & Backend
chcp 65001 >nul
cd /d "%~dp0backend"

echo ========================================================
echo   Memulai SMART AI IoT Server...
echo ========================================================
echo.
echo Membuka browser ke Dashboard UI: http://localhost:8000/ui
echo.

start http://localhost:8000/ui

venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
