@echo off
title Yalla Neshtaghal AI Engine Microservice (Port 8000)
cd /d "%~dp0"
echo ================================================================================
echo Starting Yalla Neshtaghal (يلا نشتغل) AI Engine on http://localhost:8000
echo Opening API Documentation at http://localhost:8000/docs ...
echo ================================================================================
start http://localhost:8000/docs
"C:\Users\ELSAKR TECH\ai_engine_venv\Scripts\python.exe" run_api.py
pause
