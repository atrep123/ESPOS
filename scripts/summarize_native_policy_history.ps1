param(
  [string]$HistoryPath = "reports/native_policy_probe_history.jsonl",
  [int]$Last = 20
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$resolvedHistoryPath = Join-Path $repoRoot $HistoryPath

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

$rows = @($rows | Sort-Object ProbeTimestamp)
$take = [Math]::Min($Last, $rows.Count)
$recent = @($rows | Select-Object -Last $take)

$triggeredCount = @($rows | Where-Object { $_.Triggered }).Count
$policyBlockedRuns = @($rows | Where-Object { $_.PolicyBlockCount -gt 0 }).Count
$transientRuns = @($rows | Where-Object { $_.TransientPolicyBlockCount -gt 0 }).Count
$failureRuns = @($rows | Where-Object { $_.FailureCount -gt 0 }).Count

Write-Host "== Native Policy History Summary =="
Write-Host "File: $resolvedHistoryPath"
Write-Host "Entries: $($rows.Count)"
Write-Host "Triggered diagnostics: $triggeredCount"
Write-Host "Runs with POLICY_BLOCK > 0: $policyBlockedRuns"
Write-Host "Runs with transient blocks > 0: $transientRuns"
Write-Host "Runs with non-policy failures > 0: $failureRuns"

Write-Host ""
Write-Host "== Recent Entries (last $take) =="
$recent |
  Select-Object ProbeTimestamp, Triggered, PolicyBlockCount, TransientPolicyBlockCount, FailureCount |
  Format-Table -AutoSize
