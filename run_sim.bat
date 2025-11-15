@echo off
REM Launch UI Simulator in new window with optional args
REM Usage: run_sim.bat [fps] [port] [width] [height]

cd /d "%~dp0"

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python not found!
    pause
    exit /b 1
)

set FPS=%1
if "%FPS%"=="" set FPS=144
set PORT=%2
if "%PORT%"=="" set PORT=8765
set WIDTH=%3
if "%WIDTH%"=="" set WIDTH=64
set HEIGHT=%4
if "%HEIGHT%"=="" set HEIGHT=16

start "ESP32 UI Simulator" cmd /k "python sim_run.py --fps %FPS% --rpc-port %PORT% --width %WIDTH% --height %HEIGHT%"

echo UI Simulator started in new window on port %PORT% (FPS %FPS%)
