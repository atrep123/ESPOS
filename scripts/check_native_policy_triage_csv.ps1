[CmdletBinding(PositionalBinding = $false)]
param(
  [string]$CombinedCsv = "reports/native_policy_triage.csv",
  [string]$DeltaCsv = "",
  [switch]$RequireCombined,
  [switch]$RequireDelta,
  [switch]$Help
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ($Help) {
  Write-Host "Usage: .\scripts\check_native_policy_triage_csv.ps1 [-Help]"
  Write-Host "  -CombinedCsv <path>    Combined triage CSV (default: reports/native_policy_triage.csv)"
  Write-Host "  -DeltaCsv <path>       Delta triage CSV"
  Write-Host "  -RequireCombined       Require combined CSV exists"
  Write-Host "  -RequireDelta          Require delta CSV exists"
  exit 0
}

$combinedCsvSpecified = $PSBoundParameters.ContainsKey("CombinedCsv")
$deltaCsvSpecified = $PSBoundParameters.ContainsKey("DeltaCsv")

if ($combinedCsvSpecified -and [string]::IsNullOrWhiteSpace($CombinedCsv)) {
  throw "-CombinedCsv was provided but is empty. Provide a CSV path or omit the parameter."
}

if ($deltaCsvSpecified -and [string]::IsNullOrWhiteSpace($DeltaCsv)) {
  throw "-DeltaCsv was provided but is empty. Provide a CSV path or omit the parameter."
}

if ($RequireDelta -and -not $deltaCsvSpecified -and [string]::IsNullOrWhiteSpace($DeltaCsv)) {
  $DeltaCsv = "reports/native_policy_triage_delta.only.csv"
  Write-Host "[INFO] Using default delta triage CSV path: $DeltaCsv"
}

$shouldCheckCombined = $RequireCombined -or $combinedCsvSpecified
$shouldCheckDelta = $RequireDelta -or $deltaCsvSpecified
if (-not $shouldCheckCombined -and -not $shouldCheckDelta) {
  throw "No triage CSV target selected. Use -RequireCombined and/or -RequireDelta (or provide -CombinedCsv/-DeltaCsv)."
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Resolve-RepoPath([string]$relativePath) {
  if ([string]::IsNullOrWhiteSpace($relativePath)) {
    return ""
  }

  $expandedPath = [Environment]::ExpandEnvironmentVariables($relativePath)
  if ([System.IO.Path]::IsPathRooted($expandedPath)) {
    return $expandedPath
  }

  return (Join-Path $repoRoot $expandedPath)
}

function Assert-FileExists([string]$path, [string]$label) {
  if (-not (Test-Path $path)) {
    throw "$label missing: $path"
  }
}

function Assert-Columns([object[]]$rows, [string[]]$requiredColumns, [string]$label) {
  if ($rows.Count -lt 1) {
    throw "$label has no data rows"
  }

  $columnNames = @($rows[0].PSObject.Properties.Name)
  foreach ($column in $requiredColumns) {
    if ($columnNames -notcontains $column) {
      throw "$label missing expected column '$column'"
    }
  }
}

$combinedPath = Resolve-RepoPath $CombinedCsv
$deltaPath = Resolve-RepoPath $DeltaCsv

Write-Host "== Native Policy Triage CSV Check =="

if ($shouldCheckCombined) {
  Assert-FileExists $combinedPath "Combined triage CSV"
  $combinedRows = @(Import-Csv -Path $combinedPath)
  Assert-Columns -rows $combinedRows -requiredColumns @(
    "RowType",
    "Rank",
    "Suite",
    "DeltaScore",
    "DeltaWindow",
    "OnlyWorsening",
    "IncludeAllDeltaRows",
    "MinAbsDeltaScore",
    "DeltaSortBy"
  ) -label "Combined triage CSV"

  Write-Host "[OK] Combined triage CSV rows: $($combinedRows.Count)"
}

if ($shouldCheckDelta) {
  Assert-FileExists $deltaPath "Delta triage CSV"
  $deltaRows = @(Import-Csv -Path $deltaPath)

  $requiredDeltaColumns = @(
    "Rank",
    "Suite",
    "DeltaScore",
    "DeltaPolicyHits",
    "DeltaTransientHits",
    "RecentScore",
    "PreviousScore",
    "DeltaWindow",
    "OnlyWorsening",
    "IncludeAllDeltaRows",
    "MinAbsDeltaScore",
    "DeltaSortBy"
  )

  if ($deltaRows.Count -eq 0) {
    $headerLine = Get-Content -Path $deltaPath -TotalCount 1
    if ([string]::IsNullOrWhiteSpace($headerLine)) {
      throw "Delta triage CSV has empty header: $deltaPath"
    }

    # Support both Export-Csv quoted headers and plain comma-separated headers.
    $headerColumns = @($headerLine -split ',' | ForEach-Object { $_.Trim().Trim('"') })
    foreach ($column in $requiredDeltaColumns) {
      if ($headerColumns -notcontains $column) {
        throw "Delta triage CSV missing expected column '$column'"
      }
    }

    Write-Host "[OK] Delta triage CSV has header only (0 rows): $deltaPath"
  } else {
    Assert-Columns -rows $deltaRows -requiredColumns $requiredDeltaColumns -label "Delta triage CSV"
    Write-Host "[OK] Delta triage CSV rows: $($deltaRows.Count)"
  }
}

Write-Host "[OK] Native policy triage CSV check passed"
