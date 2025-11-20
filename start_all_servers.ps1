# Start all required servers for ESP32OS Web Designer
$rootPath = "C:\Users\atrep\Desktop\ESP32OS"

Write-Host "`n=== Starting ESP32OS Web Designer Servers ===" -ForegroundColor Cyan

# 1. HTTP Server (port 8080)
Write-Host "`n[1/3] Starting HTTP server on port 8080..." -ForegroundColor Yellow
Start-Job -ScriptBlock {
    param($path)
    Set-Location $path\web_designer_frontend
    python -m http.server 8080
} -ArgumentList $rootPath -Name "HTTPServer" | Out-Null

# 2. WebSocket Backend (port 8000)
Write-Host "[2/3] Starting WebSocket backend on port 8000..." -ForegroundColor Yellow
Start-Job -ScriptBlock {
    param($path)
    Set-Location $path
    python web_designer_backend_server.py
} -ArgumentList $rootPath -Name "BackendServer" | Out-Null

# 3. ESP32 Simulator (port 8765)
Write-Host "[3/3] Starting ESP32 simulator on port 8765..." -ForegroundColor Yellow
Start-Job -ScriptBlock {
    param($path)
    Set-Location $path
    python sim_run.py --rpc-port 8765 --auto-size
} -ArgumentList $rootPath -Name "SimulatorServer" | Out-Null

# Wait for servers to start
Write-Host "`nWaiting for servers to initialize..." -ForegroundColor Gray
Start-Sleep -Seconds 3

# Check status
Write-Host "`n=== Server Status ===" -ForegroundColor Cyan
Get-Job | Format-Table Name, State -AutoSize

Write-Host "`n=== Port Status ===" -ForegroundColor Cyan
@(8080, 8000, 8765) | ForEach-Object {
    $port = $_
    $listening = netstat -ano | Select-String ":$port" | Select-String "LISTENING" | Select-Object -First 1
    if ($listening) {
        Write-Host "✅ Port $port : RUNNING" -ForegroundColor Green
    } else {
        Write-Host "❌ Port $port : NOT RUNNING" -ForegroundColor Red
    }
}

Write-Host "`n=== Access Points ===" -ForegroundColor Cyan
Write-Host "🌐 Web Designer:  http://localhost:8080" -ForegroundColor Yellow
Write-Host "🔌 WebSocket:     ws://localhost:8000" -ForegroundColor Yellow
Write-Host "🎮 Simulator:     ws://localhost:8765" -ForegroundColor Yellow

Write-Host "`n=== Commands ===" -ForegroundColor Cyan
Write-Host "View job status:  Get-Job" -ForegroundColor Gray
Write-Host "View job output:  Receive-Job -Name JobName" -ForegroundColor Gray
Write-Host "Stop all servers: Get-Job | Stop-Job" -ForegroundColor Gray
Write-Host ""
