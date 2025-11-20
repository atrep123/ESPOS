# Start all ESP32OS Web Designer servers
$rootPath = "C:\Users\atrep\Desktop\ESP32OS"

Write-Host ""
Write-Host "=== Starting ESP32OS Web Designer Servers ===" -ForegroundColor Cyan
Write-Host ""

# 1. HTTP Server
Write-Host "[1/3] HTTP server (port 8080)..." -ForegroundColor Yellow
Start-Job -ScriptBlock {
    param($path)
    Set-Location "$path\web_designer_frontend"
    python -m http.server 8080
} -ArgumentList $rootPath -Name "HTTPServer" | Out-Null

# 2. WebSocket Backend
Write-Host "[2/3] WebSocket backend (port 8000)..." -ForegroundColor Yellow
Start-Job -ScriptBlock {
    param($path)
    Set-Location $path
    python web_designer_backend_server.py
} -ArgumentList $rootPath -Name "BackendServer" | Out-Null

# 3. ESP32 Simulator
Write-Host "[3/3] ESP32 simulator (port 8765)..." -ForegroundColor Yellow
Start-Job -ScriptBlock {
    param($path)
    Set-Location $path
    python sim_run.py --rpc-port 8765 --auto-size
} -ArgumentList $rootPath -Name "SimulatorServer" | Out-Null

Write-Host ""
Write-Host "Waiting 3 seconds for servers to start..." -ForegroundColor Gray
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "=== Server Status ===" -ForegroundColor Cyan
Get-Job | Format-Table Name, State -AutoSize

Write-Host "=== Port Status ===" -ForegroundColor Cyan
$ports = @(8080, 8000, 8765)
foreach ($port in $ports) {
    $listening = netstat -ano | Select-String ":$port" | Select-String "LISTENING" | Select-Object -First 1
    if ($listening) {
        Write-Host "Port $port : RUNNING" -ForegroundColor Green
    } else {
        Write-Host "Port $port : NOT RUNNING" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Web Designer: http://localhost:8080" -ForegroundColor Yellow
Write-Host ""
Write-Host "To stop: Get-Job | Stop-Job" -ForegroundColor Gray
Write-Host ""
