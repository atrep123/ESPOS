param(
  [int]$MaxAttemptsPerSuite = 3,
  [int]$DelaySeconds = 2
)

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

  $attempt = 1
  $exitCode = 1
  $status = "FAILED"
  $hadPolicyBlock = $false

  while ($attempt -le $MaxAttemptsPerSuite) {
    Write-Host "-- attempt $attempt/$MaxAttemptsPerSuite --"

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

    if ($isPolicyBlock) {
      $hadPolicyBlock = $true
    }

    if ($exitCode -eq 0) {
      if ($hadPolicyBlock) {
        $status = "POLICY_BLOCK_TRANSIENT"
      } else {
        $status = "PASSED"
      }
      break
    }

    if ($isPolicyBlock -and $attempt -lt $MaxAttemptsPerSuite) {
      Write-Warning "Policy block detected for $suite, retrying in $DelaySeconds s..."
      Start-Sleep -Seconds $DelaySeconds
      $attempt++
      continue
    }

    if ($isPolicyBlock) {
      $status = "POLICY_BLOCK"
    } else {
      $status = "FAILED"
    }
    break
  }

  $results += [pscustomobject]@{
    Suite = $suite
    Status = $status
    ExitCode = $exitCode
    Attempts = $attempt
  }
}

Write-Host ""
Write-Host "== Probe Summary =="
$results | Format-Table -AutoSize

$policyCount = @($results | Where-Object { $_.Status -eq "POLICY_BLOCK" }).Count
$transientPolicyCount = @($results | Where-Object { $_.Status -eq "POLICY_BLOCK_TRANSIENT" }).Count
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

if ($transientPolicyCount -gt 0) {
  Write-Host ""
  Write-Warning "Detected $transientPolicyCount transient policy block(s) that passed after retry."
}

Write-Host ""
Write-Host "[OK] All native suites passed without policy blocking."
exit 0
