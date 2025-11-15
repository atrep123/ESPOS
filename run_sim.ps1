# Launch UI Simulator in new window
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path

# Check if Python is available
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Python not found!" -ForegroundColor Red
    exit 1
}

# Launch in new Windows Terminal if available, otherwise use standard PowerShell window
if (Get-Command wt.exe -ErrorAction SilentlyContinue) {
    # Use Windows Terminal
    Start-Process wt.exe -ArgumentList "python `"$scriptPath\sim_run.py`""
} else {
    # Fallback to standard PowerShell window
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptPath'; python sim_run.py"
}

Write-Host "UI Simulator started in new window" -ForegroundColor Green
