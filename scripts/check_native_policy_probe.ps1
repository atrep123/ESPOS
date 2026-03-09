param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Try-AddMsysGccToPath {
  $msysGccDir = "C:\msys64\ucrt64\bin"
  $msysGccExe = Join-Path $msysGccDir "gcc.exe"
  if ((-not (Get-Command gcc -ErrorAction SilentlyContinue)) -and (Test-Path $msysGccExe)) {
    $env:Path = "$msysGccDir;$env:Path"
    Write-Host "[INFO] Added MSYS2 gcc path for current run: $msysGccDir"
  }
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$testRoot = Join-Path $repoRoot "test"

Write-Host "== Native Policy Probe (Windows) =="
Write-Host "Repo: $repoRoot"

if (-not (Get-Command pio -ErrorAction SilentlyContinue)) {
  throw "PlatformIO CLI missing: 'pio' not found in PATH"
}

Try-AddMsysGccToPath
if (-not (Get-Command gcc -ErrorAction SilentlyContinue)) {
  throw "Native toolchain missing: 'gcc' not found in PATH"
}

if (-not (Test-Path $testRoot)) {
  throw "Test directory not found: $testRoot"
}

$testSuites = @(Get-ChildItem -Path $testRoot -Directory -Filter "test_*" | Sort-Object Name | Select-Object -ExpandProperty Name)
if ($testSuites.Count -eq 0) {
  throw "No test suites found under $testRoot"
}

$results = @()

foreach ($suite in $testSuites) {
  Write-Host ""
  Write-Host "== Probe $suite =="

  $cmdOutput = & cmd /c "pio test -e native -f $suite 2>&1"
  $exitCode = $LASTEXITCODE
  $outText = ($cmdOutput | Out-String)

  # Echo command output so this script is useful directly in terminal.
  $cmdOutput | Out-Host

  $isPolicyBlock = ($outText -match 'WinError\s*4551') -or
                   ($outText -match 'application control policy') -or
                   ($outText -match 'Zásada řízení aplikací') -or
                   ($outText -match 'Z.sada .* aplikac.') -or
                   ($outText -match 'zablokovala')

  $status = "PASSED"
  if ($exitCode -ne 0 -and $isPolicyBlock) {
    $status = "POLICY_BLOCK"
  } elseif ($exitCode -ne 0) {
    $status = "FAILED"
  }

  $results += [pscustomobject]@{
    Suite = $suite
    Status = $status
    ExitCode = $exitCode
  }
}

Write-Host ""
Write-Host "== Probe Summary =="
$results | Format-Table -AutoSize

$policyCount = @($results | Where-Object { $_.Status -eq "POLICY_BLOCK" }).Count
$failCount = @($results | Where-Object { $_.Status -eq "FAILED" }).Count

if ($failCount -gt 0) {
  Write-Host ""
  Write-Host "[FAIL] Found $failCount suite(s) with non-policy failures."
  exit 1
}

if ($policyCount -gt 0) {
  Write-Host ""
  Write-Warning "Detected $policyCount suite(s) blocked by host policy (WinError 4551)."
  Write-Host "Use scripts/list_native_whitelist_targets.ps1 to prepare App Control allow-list targets."
  exit 2
}

Write-Host ""
Write-Host "[OK] All native suites passed without policy blocking."
exit 0
