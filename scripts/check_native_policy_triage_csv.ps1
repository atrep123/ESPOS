param(
  [string]$CombinedCsv = "reports/native_policy_triage.csv",
  [string]$DeltaCsv = "",
  [switch]$RequireCombined,
  [switch]$RequireDelta
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Resolve-RepoPath([string]$relativePath) {
  if ([string]::IsNullOrWhiteSpace($relativePath)) {
    return ""
  }

  return (Join-Path $repoRoot $relativePath)
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

if ($RequireCombined -or -not [string]::IsNullOrWhiteSpace($combinedPath)) {
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

if ($RequireDelta -or -not [string]::IsNullOrWhiteSpace($deltaPath)) {
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

    $headerColumns = @($headerLine.Trim('"') -split '","')
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
