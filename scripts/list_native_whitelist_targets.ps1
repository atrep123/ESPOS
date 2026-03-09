param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ($args.Count -gt 0) {
  throw "Unexpected argument(s): $($args -join ', ')"
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$nativeBuildDir = Join-Path $repoRoot ".pio\build\native"

Write-Host "== Native Whitelist Targets (Windows) =="
Write-Host "Repo: $repoRoot"
Write-Host ""

if (-not (Test-Path $nativeBuildDir)) {
  Write-Warning "Native build directory not found: $nativeBuildDir"
  Write-Host "Run 'pio test -e native' once, then rerun this script."
  exit 1
}

$exeFiles = @(Get-ChildItem -Path $nativeBuildDir -Recurse -File -Filter *.exe | Sort-Object FullName)

Write-Host "Recommended allow-list targets for App Control:"
Write-Host "- Directory: $nativeBuildDir"
Write-Host "- Pattern:   $nativeBuildDir\*.exe"

if ($exeFiles.Count -gt 0) {
  Write-Host ""
  Write-Host "Currently present executable files:"
  foreach ($exe in $exeFiles) {
    Write-Host "- $($exe.FullName)"
  }
} else {
  Write-Host ""
  Write-Host "No .exe files found yet under native build directory."
}

Write-Host ""
Write-Host "Tip: if policy still blocks runs, also allow your PlatformIO penv Python executable:"
Write-Host "- $env:USERPROFILE\.platformio\penv\Scripts\python.exe"
