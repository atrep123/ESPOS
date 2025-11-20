# ESP32OS UI Designer - Complete Launcher
# This script starts all servers and launches the Tauri desktop application

$ErrorActionPreference = "Stop"
$rootPath = "C:\Users\atrep\Desktop\ESP32OS"

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  ESP32OS UI Designer Launcher" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Stop any existing jobs
Write-Host "[Cleanup] Stopping existing jobs..." -ForegroundColor Gray
Get-Job -ErrorAction SilentlyContinue | Stop-Job -ErrorAction SilentlyContinue
Get-Job -ErrorAction SilentlyContinue | Remove-Job -ErrorAction SilentlyContinue

# Step 2: Start HTTP Server
Write-Host "[1/3] Starting HTTP server (port 8080)..." -ForegroundColor Yellow
Start-Job -ScriptBlock {
    param($path)
    Set-Location "$path\web_designer_frontend"
    python -m http.server 8080
} -ArgumentList $rootPath -Name "HTTPServer" | Out-Null
Start-Sleep -Milliseconds 500

# Step 3: Start WebSocket Backend
Write-Host "[2/3] Starting WebSocket backend (port 8000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd $rootPath; python web_designer_backend_server.py" -WindowStyle Minimized
Start-Sleep -Milliseconds 500

# Step 4: Start ESP32 Simulator
Write-Host "[3/3] Starting ESP32 simulator (port 8765)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd $rootPath; python sim_run.py --rpc-port 8765 --auto-size" -WindowStyle Minimized
Start-Sleep -Seconds 2

# Step 5: Verify servers are running
Write-Host ""
Write-Host "Verifying servers..." -ForegroundColor Cyan
$allRunning = $true
@{8080="HTTP"; 8000="Backend"; 8765="Simulator"}.GetEnumerator() | ForEach-Object {
    $port = $_.Key
    $name = $_.Value
    $listening = netstat -ano | Select-String ":$port" | Select-String "LISTENING" | Select-Object -First 1
    if ($listening) {
        Write-Host "  ✅ $name (port $port)" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $name (port $port) FAILED" -ForegroundColor Red
        $allRunning = $false
    }
}

if (-not $allRunning) {
    Write-Host ""
    Write-Host "ERROR: Not all servers started successfully!" -ForegroundColor Red
    Write-Host "Please check the logs and try again." -ForegroundColor Yellow
    exit 1
}

# Step 6: Launch Tauri Desktop Application
Write-Host ""
Write-Host "Launching desktop application..." -ForegroundColor Green
Write-Host ""

Set-Location "$rootPath\web_designer_frontend"
npx tauri dev

# Cleanup on exit
Write-Host ""
Write-Host "Application closed. Cleaning up..." -ForegroundColor Gray
Get-Job -ErrorAction SilentlyContinue | Stop-Job -ErrorAction SilentlyContinue
Get-Job -ErrorAction SilentlyContinue | Remove-Job -ErrorAction SilentlyContinue
Write-Host "Done!" -ForegroundColor Green
