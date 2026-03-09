param(
  [string]$HistoryPath = "reports/native_policy_probe_history.jsonl",
  [int]$Top = 5,
  [string]$MarkdownOut = "reports/native_policy_triage.md"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ($Top -lt 1) {
  throw "Invalid value for -Top: must be >= 1"
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$resolvedHistoryPath = Join-Path $repoRoot $HistoryPath
$resolvedMarkdownPath = Join-Path $repoRoot $MarkdownOut

if (-not (Test-Path $resolvedHistoryPath)) {
  throw "History file not found: $resolvedHistoryPath"
}

$rows = @()
foreach ($line in (Get-Content -Path $resolvedHistoryPath)) {
  if ([string]::IsNullOrWhiteSpace($line)) {
    continue
  }
  $rows += ($line | ConvertFrom-Json)
}

if ($rows.Count -eq 0) {
  throw "History file is empty: $resolvedHistoryPath"
}

$totalRuns = [double]$rows.Count
$stats = @{}

function Ensure-Suite([string]$suiteName) {
  if ([string]::IsNullOrWhiteSpace($suiteName)) {
    return $null
  }

  if (-not $stats.ContainsKey($suiteName)) {
    $stats[$suiteName] = [pscustomobject]@{
      Suite = $suiteName
      PolicyHits = 0
      TransientHits = 0
    }
  }

  return $stats[$suiteName]
}

foreach ($row in $rows) {
  $blockedSuites = @()
  $transientSuites = @()

  if ($row.PSObject.Properties.Name -contains "BlockedSuites") {
    $blockedSuites = @($row.BlockedSuites)
  }
  if ($row.PSObject.Properties.Name -contains "TransientSuites") {
    $transientSuites = @($row.TransientSuites)
  }

  foreach ($suite in $blockedSuites) {
    $entry = Ensure-Suite ([string]$suite)
    if ($null -ne $entry) {
      $entry.PolicyHits++
    }
  }

  foreach ($suite in $transientSuites) {
    $entry = Ensure-Suite ([string]$suite)
    if ($null -ne $entry) {
      $entry.TransientHits++
    }
  }
}

$ranked = @(
  $stats.Values |
    ForEach-Object {
      $policyRate = [Math]::Round((100.0 * $_.PolicyHits / $totalRuns), 1)
      $transientRate = [Math]::Round((100.0 * $_.TransientHits / $totalRuns), 1)
      # Persistent blocks are weighted higher than transient ones.
      $score = (2 * $_.PolicyHits) + $_.TransientHits
      [pscustomobject]@{
        Suite = $_.Suite
        Score = $score
        PolicyHits = $_.PolicyHits
        PolicyRunRatePercent = $policyRate
        TransientHits = $_.TransientHits
        TransientRunRatePercent = $transientRate
      }
    } |
    Sort-Object @{Expression = 'Score'; Descending = $true}, @{Expression = 'PolicyHits'; Descending = $true}, @{Expression = 'TransientHits'; Descending = $true}, @{Expression = 'Suite'; Descending = $false}
)

$topRanked = @($ranked | Select-Object -First $Top)

Write-Host "== Native Policy Blocker Triage =="
Write-Host "History: $resolvedHistoryPath"
Write-Host "Runs: $($rows.Count)"
Write-Host "Top: $Top"

if ($topRanked.Count -eq 0) {
  Write-Host "No blocked or transient suites found in history."
} else {
  Write-Host ""
  Write-Host "== Top Suites For Allow-List Priority =="
  $topRanked | Format-Table -AutoSize
}

$outDir = Split-Path -Parent $resolvedMarkdownPath
if (-not [string]::IsNullOrWhiteSpace($outDir) -and -not (Test-Path $outDir)) {
  New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}

$md = @()
$md += "# Native Policy Blocker Triage"
$md += ""
$md += ('- Generated: ' + (Get-Date).ToString('o'))
$md += ('- History: ' + $resolvedHistoryPath)
$md += ('- Runs: ' + $rows.Count)
$md += ('- Top: ' + $Top)
$md += "- Score formula: 2 * PolicyHits + TransientHits"
$md += ""

if ($topRanked.Count -eq 0) {
  $md += "No blocked or transient suites found in history."
} else {
  $md += "## Top Suites For Allow-List Priority"
  $md += ""
  $md += "| Rank | Suite | Score | PolicyHits | PolicyRunRate% | TransientHits | TransientRunRate% |"
  $md += "|---:|---|---:|---:|---:|---:|---:|"

  $rank = 1
  foreach ($suite in $topRanked) {
    $md += "| $rank | $($suite.Suite) | $($suite.Score) | $($suite.PolicyHits) | $($suite.PolicyRunRatePercent) | $($suite.TransientHits) | $($suite.TransientRunRatePercent) |"
    $rank++
  }

  $md += ""
  $md += "## Recommended Next Action"
  $md += ""
  $md += "1. Prioritize allow-list requests for the top-ranked suites above."
  $md += "2. Re-run scripts/burnin_native_policy.ps1 -Rounds 10 -DelaySeconds 2 after policy changes."
  $md += "3. Compare triage reports before/after to verify rate reduction."
}

Set-Content -Path $resolvedMarkdownPath -Value $md -Encoding UTF8
Write-Host ""
Write-Host "[INFO] Wrote triage report: $resolvedMarkdownPath"
