# Start WebSocket backend server as background job
$scriptPath = "C:\Users\atrep\Desktop\ESP32OS\web_designer_backend_server.py"
Start-Job -ScriptBlock {
    param($path)
    python $path
} -ArgumentList $scriptPath -Name "WebSocketBackend"

Write-Host "Backend server starting..." -ForegroundColor Green
Start-Sleep -Seconds 2
Get-Job -Name "WebSocketBackend"
