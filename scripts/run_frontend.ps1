# Runs backend server and serves the web frontend
# Usage: .\run_frontend.ps1 [-Port 8080]
param(
    [int]$Port = 8080
)

$ErrorActionPreference = "Stop"

# Resolve paths
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontendDir = Join-Path $repoRoot "web_designer_frontend"
$indexHtml = Join-Path $frontendDir "index.html"

Write-Host "[run_frontend] Repo root: $repoRoot"

# Start backend (new PowerShell window)
Write-Host "[run_frontend] Starting backend (python web_designer_backend.py)"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Push-Location `"$repoRoot`"; python web_designer_backend.py"

# Start static server for frontend
Write-Host "[run_frontend] Serving frontend on http://localhost:$Port"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Push-Location `"$frontendDir`"; python -m http.server $Port"

# Open browser to index.html via static server
$uri = "http://localhost:$Port/index.html"
Write-Host "[run_frontend] Opening $uri"
Start-Process $uri

Write-Host "[run_frontend] Done. Close the spawned PowerShell windows to stop servers."