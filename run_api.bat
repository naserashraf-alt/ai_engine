@echo off
title Yalla Neshtaghal AI Engine Microservice (Port 8000)
cd /d "%~dp0"
echo ================================================================================
echo Starting Yalla Neshtaghal (يلا نشتغل) AI Engine on http://localhost:8000
echo Server is initializing... Browser will open automatically once ready!
echo ================================================================================
"C:\Users\ELSAKR TECH\ai_engine_venv\Scripts\python.exe" run_api.py
pause
