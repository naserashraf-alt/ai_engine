@echo off
title Yalla Neshtaghal AI Dashboard (Port 8501)
cd /d "%~dp0"
echo ================================================================================
echo Starting Yalla Neshtaghal (يلا نشتغل) Dashboard on http://localhost:8501
echo Opening Dashboard in your browser ...
echo ================================================================================
start http://localhost:8501
"C:\Users\ELSAKR TECH\ai_engine_venv\Scripts\python.exe" -m streamlit run app.py
pause
