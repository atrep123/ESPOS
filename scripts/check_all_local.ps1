param(
  [switch]$SkipPython,
  [switch]$SkipPio,
  [switch]$Fast,
  [switch]$StrictArtifacts,
  [switch]$StrictTriageCsv,
  [switch]$StrictTriageDeltaCsv,
  [string]$Design = "main_scene.json",
  [string]$NativePolicyProbeJson = "reports/native_policy_probe_auto.json",
  [string]$NativePolicyHistoryJsonl = "reports/native_policy_probe_history.jsonl",
  [string]$NativePolicySummaryMarkdown = "reports/native_policy_summary.md",
  [string]$NativePolicyHistoryCsv = "reports/native_policy_history.csv",
  [string]$NativePolicyTriageCsv = "",
  [string]$NativePolicyTriageDeltaCsv = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ((-not $StrictArtifacts) -and ($StrictTriageCsv -or $StrictTriageDeltaCsv)) {
  throw "-StrictTriageCsv/-StrictTriageDeltaCsv require -StrictArtifacts"
}

$msysGccDir = "C:\msys64\ucrt64\bin"
$msysGccExe = Join-Path $msysGccDir "gcc.exe"
if ((-not (Get-Command gcc -ErrorAction SilentlyContinue)) -and (Test-Path $msysGccExe)) {
  $env:Path = "$msysGccDir;$env:Path"
  Write-Host "[INFO] Added MSYS2 gcc path for current run: $msysGccDir"
}

$prev = $env:ESP32OS_ALLOW_NATIVE_POLICY_BLOCK
$env:ESP32OS_ALLOW_NATIVE_POLICY_BLOCK = "1"

try {
  if ($StrictTriageCsv -and [string]::IsNullOrWhiteSpace($NativePolicyTriageCsv)) {
    $NativePolicyTriageCsv = "reports/native_policy_triage.csv"
    Write-Host "[INFO] Using default triage CSV path: $NativePolicyTriageCsv"
  }

  if ($StrictTriageDeltaCsv -and [string]::IsNullOrWhiteSpace($NativePolicyTriageDeltaCsv)) {
    $NativePolicyTriageDeltaCsv = "reports/native_policy_triage_delta.only.csv"
    Write-Host "[INFO] Using default delta triage CSV path: $NativePolicyTriageDeltaCsv"
  }

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
    -NativePolicyProbeJson $NativePolicyProbeJson `
    -NativePolicyHistoryJsonl $NativePolicyHistoryJsonl `
    -AllowNativePolicyBlock

  if ($StrictArtifacts) {
    $artifactCheck = Join-Path $PSScriptRoot "check_native_policy_artifacts.ps1"
    if (-not (Test-Path $artifactCheck)) {
      throw "Missing script: $artifactCheck"
    }

    Write-Host "[INFO] Running strict native policy artifact check..."
    $artifactParams = @{
      ProbeJson = $NativePolicyProbeJson
      HistoryJsonl = $NativePolicyHistoryJsonl
      SummaryMarkdown = $NativePolicySummaryMarkdown
      HistoryCsv = $NativePolicyHistoryCsv
      RequireMarkdown = $true
      RequireCsv = $true
    }

    if ($StrictTriageCsv) {
      $artifactParams.RequireTriageCsv = $true
    }
    if ($StrictTriageDeltaCsv) {
      $artifactParams.RequireTriageDeltaCsv = $true
    }

    if ($StrictTriageCsv -and -not [string]::IsNullOrWhiteSpace($NativePolicyTriageCsv)) {
      $artifactParams.TriageCsv = $NativePolicyTriageCsv
    }
    if ($StrictTriageDeltaCsv -and -not [string]::IsNullOrWhiteSpace($NativePolicyTriageDeltaCsv)) {
      $artifactParams.TriageDeltaCsv = $NativePolicyTriageDeltaCsv
    }

    & $artifactCheck @artifactParams
  }
}
finally {
  if ($null -eq $prev) {
    Remove-Item Env:ESP32OS_ALLOW_NATIVE_POLICY_BLOCK -ErrorAction SilentlyContinue
  } else {
    $env:ESP32OS_ALLOW_NATIVE_POLICY_BLOCK = $prev
  }
}
