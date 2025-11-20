# Start ESP32OS Web Designer Servers
Write-Host "Starting servers..." -ForegroundColor Cyan

# HTTP Server
Start-Job -ScriptBlock {
    Set-Location "C:\Users\atrep\Desktop\ESP32OS\web_designer_frontend\dist"
    python -m http.server 8080
} -Name "HTTP" | Out-Null

# Backend
Start-Job -ScriptBlock {
    Set-Location "C:\Users\atrep\Desktop\ESP32OS"
    python web_designer_backend_server.py
} -Name "Backend" | Out-Null

# Simulator
Start-Job -ScriptBlock {
    Set-Location "C:\Users\atrep\Desktop\ESP32OS"
    python sim_run.py --rpc-port 8765 --auto-size
} -Name "Simulator" | Out-Null

Start-Sleep -Seconds 2
Write-Host "Servers started!" -ForegroundColor Green
Write-Host "Web Designer: http://localhost:8080/index.html" -ForegroundColor Yellow
Write-Host "To stop: Get-Job | Remove-Job -Force" -ForegroundColor Gray
Get-Job
