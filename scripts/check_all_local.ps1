param(
  [switch]$SkipPython,
  [switch]$SkipPio,
  [switch]$Fast,
  [string]$Design = "main_scene.json"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$msysGccDir = "C:\msys64\ucrt64\bin"
$msysGccExe = Join-Path $msysGccDir "gcc.exe"
if ((-not (Get-Command gcc -ErrorAction SilentlyContinue)) -and (Test-Path $msysGccExe)) {
  $env:Path = "$msysGccDir;$env:Path"
  Write-Host "[INFO] Added MSYS2 gcc path for current run: $msysGccDir"
}

$prev = $env:ESP32OS_ALLOW_NATIVE_POLICY_BLOCK
$env:ESP32OS_ALLOW_NATIVE_POLICY_BLOCK = "1"

try {
  if (-not $SkipPio) {
    $preflight = Join-Path $PSScriptRoot "check_native_toolchain.ps1"
    if (Test-Path $preflight) {
      try {
        & $preflight
      }
      catch {
        Write-Warning "Native preflight reported missing prerequisites; continuing with tolerant local checks."
      }
    }
  }

  & "$PSScriptRoot\check_all.ps1" `
    -SkipPython:$SkipPython `
    -SkipPio:$SkipPio `
    -Fast:$Fast `
    -Design $Design `
    -AllowNativePolicyBlock
}
finally {
  if ($null -eq $prev) {
    Remove-Item Env:ESP32OS_ALLOW_NATIVE_POLICY_BLOCK -ErrorAction SilentlyContinue
  } else {
    $env:ESP32OS_ALLOW_NATIVE_POLICY_BLOCK = $prev
  }
}
