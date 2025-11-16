param(
    [string]$Extras = "ui,web,hw,metrics,input,dev"
)
$ErrorActionPreference = 'Stop'
Write-Host "[setup] Creating .venv and installing extras: $Extras"

# Create venv
if (-not (Test-Path ".venv")) {
    py -3 -m venv .venv
}

# Activate
$venvActivate = ".venv\\Scripts\\Activate.ps1"
. $venvActivate

# Upgrade pip and install
python -m pip install --upgrade pip
if (Test-Path "pyproject.toml") {
    python -m pip install ".[${Extras}]"
} elseif (Test-Path "requirements.txt") {
    python -m pip install -r requirements.txt
}

# Optional: pre-commit
if (Get-Command pre-commit -ErrorAction SilentlyContinue) {
    pre-commit install
}

Write-Host "[setup] Done. Activate with:`n`n    . .venv\\Scripts\\Activate.ps1`n"
