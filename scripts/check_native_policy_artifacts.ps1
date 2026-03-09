param(
  [string]$ProbeJson = "reports/native_policy_probe_auto.json",
  [string]$HistoryJsonl = "reports/native_policy_probe_history.jsonl",
  [string]$SummaryMarkdown = "reports/native_policy_summary.md",
  [string]$HistoryCsv = "reports/native_policy_history.csv",
  [switch]$RequireMarkdown,
  [switch]$RequireCsv
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

function Assert-HasProperty($obj, [string]$propertyName, [string]$label) {
  if (-not ($obj.PSObject.Properties.Name -contains $propertyName)) {
    throw "$label missing property '$propertyName'"
  }
}

$probePath = Resolve-RepoPath $ProbeJson
$historyPath = Resolve-RepoPath $HistoryJsonl
$markdownPath = Resolve-RepoPath $SummaryMarkdown
$csvPath = Resolve-RepoPath $HistoryCsv

Write-Host "== Native Policy Artifact Check =="

Assert-FileExists $probePath "Probe JSON"
$probe = Get-Content -Path $probePath -Raw | ConvertFrom-Json
Assert-HasProperty $probe "Summary" "Probe JSON"
Assert-HasProperty $probe "Results" "Probe JSON"
Assert-HasProperty $probe.Summary "ProbeTimestamp" "Probe JSON Summary"
Assert-HasProperty $probe.Summary "Triggered" "Probe JSON Summary"
Assert-HasProperty $probe.Summary "PolicyBlockCount" "Probe JSON Summary"
Assert-HasProperty $probe.Summary "TransientPolicyBlockCount" "Probe JSON Summary"
Assert-HasProperty $probe.Summary "FailureCount" "Probe JSON Summary"

Assert-FileExists $historyPath "History JSONL"
$historyLines = @(Get-Content -Path $historyPath | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
if ($historyLines.Count -lt 1) {
  throw "History JSONL has no data rows: $historyPath"
}

$historyEntries = @()
foreach ($line in $historyLines) {
  $entry = $line | ConvertFrom-Json
  Assert-HasProperty $entry "ProbeTimestamp" "History entry"
  Assert-HasProperty $entry "Triggered" "History entry"
  Assert-HasProperty $entry "PolicyBlockCount" "History entry"
  Assert-HasProperty $entry "TransientPolicyBlockCount" "History entry"
  Assert-HasProperty $entry "FailureCount" "History entry"
  $historyEntries += $entry
}

if ($RequireMarkdown) {
  Assert-FileExists $markdownPath "Summary Markdown"
  $markdown = Get-Content -Path $markdownPath -Raw
  if ($markdown -notmatch "Native Policy History Summary") {
    throw "Summary Markdown does not contain expected heading"
  }
  if ($markdown -notmatch "Blocked Suite Frequency") {
    Write-Warning "Summary Markdown missing blocked-suite section (can be valid if no blocked suites in history)"
  }
}

if ($RequireCsv) {
  Assert-FileExists $csvPath "History CSV"
  $csvRows = @(Import-Csv -Path $csvPath)
  if ($csvRows.Count -lt 1) {
    throw "History CSV has no data rows: $csvPath"
  }

  $requiredColumns = @(
    "ProbeTimestamp",
    "Triggered",
    "PolicyBlockCount",
    "TransientPolicyBlockCount",
    "FailureCount",
    "BlockedSuites",
    "TransientSuites",
    "JsonPath"
  )

  $columnNames = @($csvRows[0].PSObject.Properties.Name)
  foreach ($column in $requiredColumns) {
    if ($columnNames -notcontains $column) {
      throw "History CSV missing expected column '$column'"
    }
  }
}

$latestHistory = $historyEntries[-1]
$probeTs = [string]$probe.Summary.ProbeTimestamp
$historyTs = [string]$latestHistory.ProbeTimestamp
if (-not [string]::IsNullOrWhiteSpace($probeTs) -and -not [string]::IsNullOrWhiteSpace($historyTs)) {
  if ($probeTs -ne $historyTs) {
    Write-Warning "Latest history ProbeTimestamp does not match probe JSON (history=$historyTs, probe=$probeTs)"
  }
}

Write-Host "[OK] Probe JSON: $probePath"
Write-Host "[OK] History JSONL rows: $($historyEntries.Count)"
if ($RequireMarkdown) {
  Write-Host "[OK] Summary Markdown: $markdownPath"
}
if ($RequireCsv) {
  Write-Host "[OK] History CSV: $csvPath"
}
Write-Host "[OK] Native policy artifact check passed"
