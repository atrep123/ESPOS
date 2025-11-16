param(
    [switch]$UI,
    [switch]$HW,
    [switch]$WEB,
    [switch]$METRICS,
    [switch]$Dev
)
$ErrorActionPreference = 'Stop'

Write-Host "Creating virtual environment in .venv" -ForegroundColor Cyan
if (-not (Test-Path .venv)) {
    python -m venv .venv
}
$activate = ".venv\Scripts\Activate.ps1"
if (-not (Test-Path $activate)) { throw "Virtualenv activation script not found: $activate" }
. $activate

Write-Host "Upgrading pip" -ForegroundColor Cyan
python -m pip install -U pip

$extras = @()
if ($UI) { $extras += "ui" }
if ($HW) { $extras += "hw" }
if ($WEB) { $extras += "web" }
if ($METRICS) { $extras += "metrics" }

if ($extras.Count -gt 0) {
    $spec = ".[" + ($extras -join ",") + "]"
    Write-Host "Installing project with extras: $spec" -ForegroundColor Cyan
    python -m pip install -e $spec
} else {
    Write-Host "Installing base project (no extras)" -ForegroundColor Cyan
    python -m pip install -e .
}

if ($Dev) {
    Write-Host "Installing dev tools" -ForegroundColor Cyan
    python -m pip install -r requirements-dev.txt
    pre-commit install
}

Write-Host "Done. Activate with: ``. .venv\Scripts\Activate.ps1``" -ForegroundColor Green
