param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Write-Host "== Native Toolchain Check (Windows) =="

$hasPio = $null -ne (Get-Command pio -ErrorAction SilentlyContinue)
$hasGcc = $null -ne (Get-Command gcc -ErrorAction SilentlyContinue)

if ($hasPio) {
  Write-Host "[OK] pio found: $((Get-Command pio).Source)"
} else {
  Write-Host "[FAIL] pio not found in PATH"
}

if ($hasGcc) {
  Write-Host "[OK] gcc found: $((Get-Command gcc).Source)"
} else {
  Write-Host "[FAIL] gcc not found in PATH"
}

if (-not $hasGcc) {
  Write-Host ""
  Write-Host "Suggested fix:"
  Write-Host "- Install MSYS2 or MinGW-w64"
  Write-Host "- Add the gcc bin folder to PATH"
  Write-Host "- Verify with: gcc --version"
}

if ($hasPio -and $hasGcc) {
  Write-Host ""
  Write-Host "[OK] Native prerequisites look good."
  exit 0
}

Write-Host ""
Write-Host "[WARN] Native prerequisites are incomplete."
exit 1
