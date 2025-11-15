@echo off
REM Launch UI Simulator in new window

cd /d "%~dp0"

REM Check if Python is available
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python not found!
    pause
    exit /b 1
)

REM Launch in new window
start "ESP32 UI Simulator" cmd /k "python sim_run.py"

echo UI Simulator started in new window
