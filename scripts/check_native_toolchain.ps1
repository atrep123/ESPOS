[CmdletBinding(PositionalBinding = $false)]
param(
  [switch]$Help
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ($Help) {
  Write-Host "Usage: .\\scripts\\check_native_toolchain.ps1 [-Help]"
  Write-Host "Checks whether 'pio' and 'gcc' are available in PATH."
  exit 0
}

Write-Host "== Native Toolchain Check (Windows) =="

$hasPio = $null -ne (Get-Command pio -ErrorAction SilentlyContinue)
$hasGcc = $null -ne (Get-Command gcc -ErrorAction SilentlyContinue)

if (-not $hasGcc) {
  $msysGccDir = "C:\msys64\ucrt64\bin"
  $msysGccExe = Join-Path $msysGccDir "gcc.exe"
  if (Test-Path $msysGccExe) {
    $env:Path = "$msysGccDir;$env:Path"
    $hasGcc = $null -ne (Get-Command gcc -ErrorAction SilentlyContinue)
    if ($hasGcc) {
      Write-Host "[INFO] Added MSYS2 gcc path for current run: $msysGccDir"
    }
  }
}

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
  if ($null -ne (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Host "- winget install -e --id MSYS2.MSYS2"
    Write-Host "  then in MSYS2 shell: pacman -S --needed mingw-w64-ucrt-x86_64-gcc"
  }
  if ($null -ne (Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Host "- choco install mingw -y"
  }
  Write-Host "- Add the gcc bin folder to PATH (for MSYS2: C:\\msys64\\ucrt64\\bin)"
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
