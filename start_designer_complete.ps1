# Complete launcher for ESP32OS Web Designer
# Starts Backend, Simulator, and Frontend, then opens the browser.

$ErrorActionPreference = "SilentlyContinue"
$ScriptPath = $PSScriptRoot

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   ESP32OS Web Designer - Complete Start" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Cleanup old processes
Write-Host "`n[1/4] Cleaning up old processes..." -ForegroundColor Yellow

# Kill by script name (more reliable than ports for non-listening or failed processes)
$scriptsToKill = @("web_designer_backend_server.py", "web_sim_bridge.py", "sim_run.py", "http.server")
$running = Get-WmiObject Win32_Process | Where-Object { $_.Name -eq "python.exe" }
foreach ($proc in $running) {
    foreach ($script in $scriptsToKill) {
        if ($proc.CommandLine -like "*$script*") {
            Write-Host "  - Killing old instance of $script (PID: $($proc.ProcessId))" -ForegroundColor Gray
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
        }
    }
}

# Also check ports just in case
$ports = @(8000, 8080, 8765)
foreach ($port in $ports) {
    $pids_tcp = (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue).OwningProcess
    if ($pids_tcp) {
        foreach ($p in $pids_tcp) {
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
            Write-Host "  - Killed process on port $port (PID: $p)" -ForegroundColor Gray
        }
    }
    
    # Wait for port to be free
    $retries = 0
    while ((Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) -and ($retries -lt 10)) {
        Start-Sleep -Milliseconds 500
        $retries++
    }
    
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        Write-Host "  - WARNING: Port $port is still in use!" -ForegroundColor Red
    } else {
        Write-Host "  - Port $port is free" -ForegroundColor Green
    }
}

# 2. Start Backend Server (Port 8000)
Write-Host "`n[2/4] Starting Backend Server (Port 8000)..." -ForegroundColor Yellow
$backendCmd = "cd '$ScriptPath'; .\.venv\Scripts\Activate.ps1; python web_designer_backend_server.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "$backendCmd" -WindowStyle Minimized
Start-Sleep -Seconds 2
if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) {
    Write-Host "  - Backend Server is RUNNING" -ForegroundColor Green
} else {
    Write-Host "  - Backend Server FAILED to start" -ForegroundColor Red
}

# 3. Start Simulator Bridge (Port 8765) & Simulator Client
Write-Host "`n[3/4] Starting Simulator Bridge & Client..." -ForegroundColor Yellow

# 3a. Start Bridge
$bridgeCmd = "cd '$ScriptPath'; .\.venv\Scripts\Activate.ps1; python web_sim_bridge.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "$bridgeCmd" -WindowStyle Minimized
Start-Sleep -Seconds 2

if (Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue) {
    Write-Host "  - Bridge Server is RUNNING (Port 8765)" -ForegroundColor Green
    
    # 3b. Start Simulator (Connects to Bridge)
    $simCmd = "cd '$ScriptPath'; .\.venv\Scripts\Activate.ps1; python sim_run.py --bridge-url ws://localhost:8765 --auto-size"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "$simCmd" -WindowStyle Minimized
    Write-Host "  - Simulator Client Started" -ForegroundColor Green
} else {
    Write-Host "  - Bridge Server FAILED to start" -ForegroundColor Red
}

# 4. Start Frontend Server (Port 8080)
Write-Host "`n[4/4] Starting Frontend Server (Port 8080)..." -ForegroundColor Yellow
$frontendPath = Join-Path $ScriptPath "web_designer_frontend"
$frontendCmd = "cd '$frontendPath'; python -m http.server 8080"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "$frontendCmd" -WindowStyle Minimized
Start-Sleep -Seconds 1
if (Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue) {
    Write-Host "  - Frontend Server is RUNNING" -ForegroundColor Green
} else {
    Write-Host "  - Frontend Server FAILED to start" -ForegroundColor Red
}

# 5. Open Browser
Write-Host "`nAll systems go! Opening browser..." -ForegroundColor Cyan
Start-Process "http://localhost:8080"

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "   Designer is ready!" -ForegroundColor Cyan
Write-Host "   - Backend:  ws://localhost:8000" -ForegroundColor Gray
Write-Host "   - Frontend: http://localhost:8080" -ForegroundColor Gray
Write-Host "   - Simulator: ws://localhost:8765" -ForegroundColor Gray
Write-Host "==========================================" -ForegroundColor Cyan
