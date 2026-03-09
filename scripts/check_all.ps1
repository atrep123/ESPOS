param(
  [switch]$SkipPython,
  [switch]$SkipPio,
  [switch]$Fast,
  [string]$Design = "main_scene.json"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Run-Step([string]$Name, [string]$Command) {
  Write-Host ""
  Write-Host "== $Name =="
  Write-Host $Command
  Invoke-Expression $Command
  if ($LASTEXITCODE -ne 0) {
    throw "Step '$Name' failed with exit code $LASTEXITCODE"
  }
}

if (-not $SkipPython) {
  Run-Step "ruff" "python -m ruff check ."
  Run-Step "pytest" "python -m pytest -q"
}

if (Test-Path "tools\\validate_design.py") {
  Run-Step "validate_design" "python tools\\validate_design.py $Design"
}

if (Test-Path "tools\\check_demo_scene_strict.py") {
  Run-Step "demo_scene strict gate" "python tools\\check_demo_scene_strict.py"
}

if (-not $SkipPio) {
  Run-Step "pio native tests" "pio test -e native"
  if (-not $Fast) {
    Run-Step "pio build (arduino_nano_esp32-nohw)" "pio run -e arduino_nano_esp32-nohw"
    Run-Step "pio build (esp32-s3-devkitm-1-nohw)" "pio run -e esp32-s3-devkitm-1-nohw"
  }
}

Write-Host ""
Write-Host "[OK] All requested checks completed."
