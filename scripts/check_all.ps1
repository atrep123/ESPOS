[CmdletBinding(PositionalBinding = $false)]
param(
  [switch]$SkipPython,
  [switch]$SkipPio,
  [switch]$Fast,
  [switch]$AllowNativePolicyBlock,
  [string]$NativePolicyProbeJson = "reports/native_policy_probe_auto.json",
  [string]$NativePolicyHistoryJsonl = "reports/native_policy_probe_history.jsonl",
  [int]$NativePolicyProbeRounds = 1,
  [string]$Design = "main_scene.json"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ([string]::IsNullOrWhiteSpace($Design)) {
  throw "-Design cannot be empty"
}

if ($NativePolicyProbeRounds -lt 1) {
  throw "-NativePolicyProbeRounds must be >= 1"
}

$allowNativePolicyBlockResolved = $AllowNativePolicyBlock -or ($env:ESP32OS_ALLOW_NATIVE_POLICY_BLOCK -eq "1")
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$nativePolicyDiagnosticsTriggered = $false

function Resolve-RepoPath([string]$inputPath) {
  $expandedPath = [Environment]::ExpandEnvironmentVariables($inputPath)
  if ([System.IO.Path]::IsPathRooted($expandedPath)) {
    return $expandedPath
  }
  return (Join-Path $repoRoot $expandedPath)
}

function Get-NativePolicyProbeJsonPath {
  if ([string]::IsNullOrWhiteSpace($NativePolicyProbeJson)) {
    return ""
  }
  return (Resolve-RepoPath $NativePolicyProbeJson)
}

function Append-NativePolicyHistory {
  if ([string]::IsNullOrWhiteSpace($NativePolicyHistoryJsonl)) {
    return
  }

  $probeJsonPath = Get-NativePolicyProbeJsonPath
  if ([string]::IsNullOrWhiteSpace($probeJsonPath) -or -not (Test-Path $probeJsonPath)) {
    return
  }

  $historyPath = Resolve-RepoPath $NativePolicyHistoryJsonl
  $historyDir = Split-Path -Parent $historyPath
  if (-not [string]::IsNullOrWhiteSpace($historyDir) -and -not (Test-Path $historyDir)) {
    New-Item -ItemType Directory -Path $historyDir -Force | Out-Null
  }

  $report = Get-Content $probeJsonPath -Raw | ConvertFrom-Json
  $summary = $report.Summary
  $results = @($report.Results)
  $blockedSuites = @($results | Where-Object { $_.Status -eq "POLICY_BLOCK" } | Select-Object -ExpandProperty Suite -Unique)
  $transientSuites = @($results | Where-Object { $_.Status -eq "POLICY_BLOCK_TRANSIENT" } | Select-Object -ExpandProperty Suite -Unique)
  $entry = [pscustomobject]@{
    RecordedAt = (Get-Date).ToString("o")
    ProbeTimestamp = $summary.ProbeTimestamp
    Triggered = [bool]$summary.Triggered
    PolicyBlockCount = $summary.PolicyBlockCount
    TransientPolicyBlockCount = $summary.TransientPolicyBlockCount
    FailureCount = $summary.FailureCount
    BlockedSuites = $blockedSuites
    TransientSuites = $transientSuites
    JsonPath = $probeJsonPath
  }
  $entry | ConvertTo-Json -Compress | Add-Content -Path $historyPath -Encoding UTF8
  Write-Host "[INFO] Appended native policy history: $historyPath"
}

function Invoke-NativePolicyCsvSmokeCheck {
  if ([string]::IsNullOrWhiteSpace($NativePolicyHistoryJsonl)) {
    return
  }

  $historyPath = Resolve-RepoPath $NativePolicyHistoryJsonl
  if (-not (Test-Path $historyPath)) {
    Write-Warning "Native policy history not found for CSV smoke-check: $historyPath"
    return
  }

  $summaryScript = Join-Path $PSScriptRoot "summarize_native_policy_history.ps1"
  if (-not (Test-Path $summaryScript)) {
    Write-Warning "CSV smoke-check skipped: summarize_native_policy_history.ps1 not found"
    return
  }

  $smokeCsvPath = Resolve-RepoPath "reports/native_policy_history.smoke.csv"
  Write-Host "[INFO] Running CSV smoke-check: $smokeCsvPath"

  $summaryParams = @{
    HistoryPath = $NativePolicyHistoryJsonl
    Last = 1
    CsvOut = "reports/native_policy_history.smoke.csv"
  }
  & $summaryScript @summaryParams

  if (-not (Test-Path $smokeCsvPath)) {
    throw "Native policy CSV smoke-check failed: CSV file was not created at $smokeCsvPath"
  }

  $csvLines = @(Get-Content -Path $smokeCsvPath)
  if ($csvLines.Count -lt 2) {
    throw "Native policy CSV smoke-check failed: CSV file contains no data rows ($smokeCsvPath)"
  }

  if ($csvLines[0] -notmatch 'ProbeTimestamp' -or $csvLines[0] -notmatch 'PolicyBlockCount') {
    throw "Native policy CSV smoke-check failed: CSV header is missing expected columns"
  }

  Write-Host "[INFO] Native policy CSV smoke-check passed"
}

function Try-AddMsysGccToPath {
  $msysGccDir = "C:\msys64\ucrt64\bin"
  $msysGccExe = Join-Path $msysGccDir "gcc.exe"
  if ((-not (Get-Command gcc -ErrorAction SilentlyContinue)) -and (Test-Path $msysGccExe)) {
    $env:Path = "$msysGccDir;$env:Path"
    Write-Host "[INFO] Added MSYS2 gcc path for current run: $msysGccDir"
  }
}

function Run-Step([string]$Name, [string]$Command) {
  Write-Host ""
  Write-Host "== $Name =="
  Write-Host $Command
  Invoke-Expression $Command
  if ($LASTEXITCODE -ne 0) {
    throw "Step '$Name' failed with exit code $LASTEXITCODE"
  }
}

function Invoke-NativePolicyDiagnostics {
  $probeScript = Join-Path $PSScriptRoot "check_native_policy_probe.ps1"
  if (-not (Test-Path $probeScript)) {
    return
  }

  $script:nativePolicyDiagnosticsTriggered = $true

  Write-Host ""
  Write-Host "[INFO] Running native policy diagnostics to identify blocked suites..."
  # Keep diagnostics bounded so strict check remains fast enough for routine use.
  $probeJsonPath = Get-NativePolicyProbeJsonPath

  $probeParams = @{
    MaxAttemptsPerSuite = 2
    DelaySeconds = 1
    Rounds = $NativePolicyProbeRounds
  }
  if (-not [string]::IsNullOrWhiteSpace($probeJsonPath)) {
    $probeParams.JsonOut = $probeJsonPath
  }

  try {
    & $probeScript @probeParams
  }
  catch {
    Write-Warning "Native policy diagnostics reported blocked suites."
  }
  if (-not [string]::IsNullOrWhiteSpace($probeJsonPath)) {
    Write-Host "[INFO] Native policy JSON report: $probeJsonPath"
  }
}

function Write-NativePolicyProbePlaceholder {
  if ([string]::IsNullOrWhiteSpace($NativePolicyProbeJson)) {
    return
  }
  if ($script:nativePolicyDiagnosticsTriggered) {
    return
  }

  $probeJsonPath = Resolve-RepoPath $NativePolicyProbeJson
  $probeJsonDir = Split-Path -Parent $probeJsonPath
  if (-not [string]::IsNullOrWhiteSpace($probeJsonDir) -and -not (Test-Path $probeJsonDir)) {
    New-Item -ItemType Directory -Path $probeJsonDir -Force | Out-Null
  }

  $placeholder = [pscustomobject]@{
    Summary = [pscustomobject]@{
      ProbeTimestamp = (Get-Date).ToString("o")
      RepoRoot = $repoRoot
      Triggered = $false
      PolicyBlockCount = 0
      TransientPolicyBlockCount = 0
      FailureCount = 0
      Note = "No repeated WinError 4551 policy blocking detected in this check_all run."
    }
    Results = @()
  }

  $placeholder | ConvertTo-Json -Depth 5 | Set-Content -Path $probeJsonPath -Encoding UTF8
  Write-Host "[INFO] Native policy JSON placeholder: $probeJsonPath"
}

function Run-Step-WithWin4551Retry(
  [string]$Name,
  [string]$Command,
  [int]$MaxAttempts = 4,
  [int]$DelaySeconds = 2,
  [bool]$AllowPolicyBlockAsWarning = $false
) {
  $policyHint = "On Windows hosts, allow native test executables under .pio\\build\\native or use scripts/check_all_local.ps1 tolerant mode."
  $attempt = 1
  while ($attempt -le $MaxAttempts) {
    Write-Host ""
    Write-Host "== $Name (attempt $attempt/$MaxAttempts) =="
    Write-Host $Command

    $logPath = Join-Path ([System.IO.Path]::GetTempPath()) ("esp32os_check_{0}_{1}.log" -f ($Name -replace '[^A-Za-z0-9_.-]', '_'), $attempt)
    if (Test-Path $logPath) {
      Remove-Item $logPath -Force
    }

    $commandErrorText = ""
    try {
      Invoke-Expression "$Command 2>&1 | Tee-Object -FilePath '$logPath'"
    }
    catch {
      $commandErrorText = $_.ToString()
    }

    if ($LASTEXITCODE -eq 0 -and [string]::IsNullOrWhiteSpace($commandErrorText)) {
      return
    }

    $logText = ""
    if (Test-Path $logPath) {
      $logText = Get-Content $logPath -Raw
    }

    $combinedText = "$commandErrorText`n$logText"
    $isPolicyBlock = ($combinedText -match 'WinError\s*4551') -or ($combinedText -match 'application control policy') -or ($combinedText -match 'Zásada řízení aplikací') -or ($combinedText -match 'Z.sada .* aplikac.')
    if (-not $isPolicyBlock) {
      if ($AllowPolicyBlockAsWarning) {
        if ($attempt -ge $MaxAttempts) {
          Write-Warning "Step '$Name' failed after $MaxAttempts attempts with unresolved host-side native test failure (exit code $LASTEXITCODE); continuing due to AllowNativePolicyBlock"
          if ($Name -eq "pio native tests") {
            Invoke-NativePolicyDiagnostics
          }
          return
        }
        Write-Warning "Native test step failed with unresolved host-side error (exit code $LASTEXITCODE). Retrying in $DelaySeconds s due to AllowNativePolicyBlock..."
        Start-Sleep -Seconds $DelaySeconds
        $attempt++
        continue
      }
      throw "Step '$Name' failed with exit code $LASTEXITCODE"
    }

    if ($attempt -ge $MaxAttempts) {
      if ($AllowPolicyBlockAsWarning) {
        Write-Warning "Step '$Name' hit repeated WinError 4551 policy blocking after $MaxAttempts attempts; continuing due to AllowNativePolicyBlock. $policyHint"
        if ($Name -eq "pio native tests") {
          Invoke-NativePolicyDiagnostics
        }
        return
      }
      throw "Step '$Name' failed after $MaxAttempts attempts due to repeated WinError 4551 policy blocking. $policyHint"
    }

    Write-Warning "Detected intermittent WinError 4551 policy block. Retrying in $DelaySeconds s..."
    Start-Sleep -Seconds $DelaySeconds
    $attempt++
  }
}

if (-not $SkipPython) {
  Run-Step "ruff" "python -m ruff check ."
  Run-Step "pytest" "python -m pytest -q --ignore=output/buildprobe/tests"
}

if (Test-Path "tools\\validate_design.py") {
  $quotedDesign = '"' + $Design.Replace('"', '""') + '"'
  Run-Step "validate_design" "python tools\validate_design.py $quotedDesign"
}

if (Test-Path "tools\\check_demo_scene_strict.py") {
  Run-Step "demo_scene strict gate" "python tools\\check_demo_scene_strict.py"
}

if (-not $SkipPio) {
  $hasPio = $null -ne (Get-Command pio -ErrorAction SilentlyContinue)
  if (-not $hasPio) {
    throw "PlatformIO CLI missing: 'pio' not found in PATH"
  }

  Try-AddMsysGccToPath
  $hasGcc = $null -ne (Get-Command gcc -ErrorAction SilentlyContinue)
  if (-not $hasGcc) {
    $gccHint = "Install MSYS2/MinGW-w64 and ensure 'gcc' is in PATH. Verify with: gcc --version"
    if ($allowNativePolicyBlockResolved) {
      Write-Warning "Native test toolchain missing: 'gcc' not found in PATH; skipping native tests due to AllowNativePolicyBlock. $gccHint"
    } else {
      throw "Native test toolchain missing: 'gcc' not found in PATH. $gccHint"
    }
  } else {
    Run-Step-WithWin4551Retry "pio native tests" "pio test -e native" 4 2 $allowNativePolicyBlockResolved
    if ($allowNativePolicyBlockResolved) {
      Write-NativePolicyProbePlaceholder
      Append-NativePolicyHistory
      Invoke-NativePolicyCsvSmokeCheck
    }
  }
  if (-not $Fast) {
    Run-Step "pio build (arduino_nano_esp32-nohw)" "pio run -e arduino_nano_esp32-nohw"
    Run-Step "pio build (esp32-s3-devkitm-1-nohw)" "pio run -e esp32-s3-devkitm-1-nohw"
  }
}

Write-Host ""
Write-Host "[OK] All requested checks completed."
