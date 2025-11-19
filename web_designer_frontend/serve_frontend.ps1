# Serves the web_designer_frontend with a simple HTTP server and opens the browser
# Usage: .\serve_frontend.ps1 [-Port 8080]
param(
    [int]$Port = 8080
)

$ErrorActionPreference = "Stop"

$frontendDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $frontendDir

Write-Host "[serve_frontend] Serving $frontendDir on http://localhost:$Port"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Push-Location `"$frontendDir`"; python -m http.server $Port"

$uri = "http://localhost:$Port/index.html"
Write-Host "[serve_frontend] Opening $uri"
Start-Process $uri

Pop-Location
Write-Host "[serve_frontend] Done. Close the spawned PowerShell window to stop server."