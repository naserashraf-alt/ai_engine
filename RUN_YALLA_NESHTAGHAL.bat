@echo off
title Yalla Neshtaghal AI Suite Launcher
cd /d "%~dp0"
cls
echo ================================================================================
echo         YALLA NESHTAGHAL (يلا نشتغل) - GRADUATION PROJECT LAUNCHER
echo ================================================================================
echo.
echo   [1] Launch Web Dashboard (Streamlit UI on http://localhost:8501)
echo   [2] Launch Backend API Microservice (FastAPI on http://localhost:8000/docs)
echo   [3] Launch BOTH (Full Stack: Dashboard + Backend API)
echo   [4] Run Full Test Suite (Verify 100%% Health)
echo   [0] Exit
echo.
echo ================================================================================
set /p opt="Enter your choice (1, 2, 3, or 4): "

if "%opt%"=="1" goto run_ui
if "%opt%"=="2" goto run_api
if "%opt%"=="3" goto run_both
if "%opt%"=="4" goto run_tests
if "%opt%"=="0" exit
goto exit

:run_ui
echo.
echo Launching Yalla Neshtaghal Streamlit Web Dashboard...
start http://localhost:8501
"C:\Users\ELSAKR TECH\ai_engine_venv\Scripts\python.exe" -m streamlit run app.py
goto end

:run_api
echo.
echo Launching Yalla Neshtaghal FastAPI Microservice...
start http://localhost:8000/docs
"C:\Users\ELSAKR TECH\ai_engine_venv\Scripts\python.exe" run_api.py
goto end

:run_both
echo.
echo Launching Full Stack (Dashboard + Backend API)...
start "Yalla Neshtaghal API Server (:8000)" cmd /c "cd /d "%~dp0" && "C:\Users\ELSAKR TECH\ai_engine_venv\Scripts\python.exe" run_api.py"
start http://localhost:8000/docs
start http://localhost:8501
"C:\Users\ELSAKR TECH\ai_engine_venv\Scripts\python.exe" -m streamlit run app.py
goto end

:run_tests
echo.
echo Running Full Test Suite via PyTest...
"C:\Users\ELSAKR TECH\ai_engine_venv\Scripts\python.exe" -m pytest tests/ -v
echo.
echo All tests finished.
pause
goto end

:end
pause
:exit
