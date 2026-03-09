param(
  [string]$HistoryPath = "reports/native_policy_probe_history.jsonl",
  [int]$Last = 20,
  [string]$MarkdownOut = "",
  [string]$CsvOut = ""
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

$totalRuns = [double]$rows.Count

$triggeredCount = @($rows | Where-Object { $_.Triggered }).Count
$policyBlockedRuns = @($rows | Where-Object { $_.PolicyBlockCount -gt 0 }).Count
$transientRuns = @($rows | Where-Object { $_.TransientPolicyBlockCount -gt 0 }).Count
$failureRuns = @($rows | Where-Object { $_.FailureCount -gt 0 }).Count

$triggeredRate = [Math]::Round((100.0 * $triggeredCount / $totalRuns), 1)
$policyBlockedRate = [Math]::Round((100.0 * $policyBlockedRuns / $totalRuns), 1)
$transientRate = [Math]::Round((100.0 * $transientRuns / $totalRuns), 1)
$failureRate = [Math]::Round((100.0 * $failureRuns / $totalRuns), 1)

$blockedSuiteFreq = @{}
$transientSuiteFreq = @{}
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
      if ([string]::IsNullOrWhiteSpace([string]$suite)) {
        continue
      }
      if (-not $blockedSuiteFreq.ContainsKey($suite)) {
        $blockedSuiteFreq[$suite] = 0
      }
      $blockedSuiteFreq[$suite]++
    }

  foreach ($suite in $transientSuites) {
      if ([string]::IsNullOrWhiteSpace([string]$suite)) {
        continue
      }
      if (-not $transientSuiteFreq.ContainsKey($suite)) {
        $transientSuiteFreq[$suite] = 0
      }
      $transientSuiteFreq[$suite]++
    }
}

Write-Host "== Native Policy History Summary =="
Write-Host "File: $resolvedHistoryPath"
Write-Host "Entries: $($rows.Count)"
Write-Host "Triggered diagnostics: $triggeredCount"
Write-Host "Runs with POLICY_BLOCK > 0: $policyBlockedRuns"
Write-Host "Runs with transient blocks > 0: $transientRuns"
Write-Host "Runs with non-policy failures > 0: $failureRuns"
Write-Host "Triggered diagnostics rate: $triggeredRate%"
Write-Host "POLICY_BLOCK run rate: $policyBlockedRate%"
Write-Host "Transient run rate: $transientRate%"
Write-Host "Non-policy failure run rate: $failureRate%"

Write-Host ""
Write-Host "== Recent Entries (last $take) =="
$recent |
  Select-Object ProbeTimestamp, Triggered, PolicyBlockCount, TransientPolicyBlockCount, FailureCount |
  Format-Table -AutoSize

if ($blockedSuiteFreq.Count -gt 0) {
  Write-Host ""
  Write-Host "== Blocked Suite Frequency =="
  $blockedSuiteFreq.GetEnumerator() |
    Sort-Object Value -Descending |
    ForEach-Object {
      [pscustomobject]@{
        Suite = $_.Key
        Hits = $_.Value
        HitRatePercent = [Math]::Round((100.0 * $_.Value / $totalRuns), 1)
      }
    } |
    Format-Table -AutoSize
}

if ($transientSuiteFreq.Count -gt 0) {
  Write-Host ""
  Write-Host "== Transient Suite Frequency =="
  $transientSuiteFreq.GetEnumerator() |
    Sort-Object Value -Descending |
    ForEach-Object {
      [pscustomobject]@{
        Suite = $_.Key
        Hits = $_.Value
        HitRatePercent = [Math]::Round((100.0 * $_.Value / $totalRuns), 1)
      }
    } |
    Format-Table -AutoSize
}

if (-not [string]::IsNullOrWhiteSpace($MarkdownOut)) {
  $mdPath = Join-Path $repoRoot $MarkdownOut
  $mdDir = Split-Path -Parent $mdPath
  if (-not [string]::IsNullOrWhiteSpace($mdDir) -and -not (Test-Path $mdDir)) {
    New-Item -ItemType Directory -Path $mdDir -Force | Out-Null
  }

  $md = @()
  $md += "# Native Policy History Summary"
  $md += ""
  $md += ('- File: ' + $resolvedHistoryPath)
  $md += "- Entries: $($rows.Count)"
  $md += "- Triggered diagnostics: $triggeredCount"
  $md += "- Runs with POLICY_BLOCK > 0: $policyBlockedRuns"
  $md += "- Runs with transient blocks > 0: $transientRuns"
  $md += "- Runs with non-policy failures > 0: $failureRuns"
  $md += "- Triggered diagnostics rate: $triggeredRate%"
  $md += "- POLICY_BLOCK run rate: $policyBlockedRate%"
  $md += "- Transient run rate: $transientRate%"
  $md += "- Non-policy failure run rate: $failureRate%"
  $md += ""
  $md += "## Recent Entries (last $take)"
  $md += ""
  $md += "| ProbeTimestamp | Triggered | PolicyBlockCount | TransientPolicyBlockCount | FailureCount |"
  $md += "|---|---:|---:|---:|---:|"
  foreach ($r in $recent) {
    $md += "| $($r.ProbeTimestamp) | $($r.Triggered) | $($r.PolicyBlockCount) | $($r.TransientPolicyBlockCount) | $($r.FailureCount) |"
  }

  if ($blockedSuiteFreq.Count -gt 0) {
    $md += ""
    $md += "## Blocked Suite Frequency"
    $md += ""
    $md += "| Suite | Hits | HitRatePercent |"
    $md += "|---|---:|---:|"
    foreach ($pair in ($blockedSuiteFreq.GetEnumerator() | Sort-Object Value -Descending)) {
      $rate = [Math]::Round((100.0 * $pair.Value / $totalRuns), 1)
      $md += "| $($pair.Key) | $($pair.Value) | $rate |"
    }
  }

  if ($transientSuiteFreq.Count -gt 0) {
    $md += ""
    $md += "## Transient Suite Frequency"
    $md += ""
    $md += "| Suite | Hits | HitRatePercent |"
    $md += "|---|---:|---:|"
    foreach ($pair in ($transientSuiteFreq.GetEnumerator() | Sort-Object Value -Descending)) {
      $rate = [Math]::Round((100.0 * $pair.Value / $totalRuns), 1)
      $md += "| $($pair.Key) | $($pair.Value) | $rate |"
    }
  }

  Set-Content -Path $mdPath -Value $md -Encoding UTF8
  Write-Host ""
  Write-Host "[INFO] Wrote Markdown summary: $mdPath"
}

if (-not [string]::IsNullOrWhiteSpace($CsvOut)) {
  $csvPath = Join-Path $repoRoot $CsvOut
  $csvDir = Split-Path -Parent $csvPath
  if (-not [string]::IsNullOrWhiteSpace($csvDir) -and -not (Test-Path $csvDir)) {
    New-Item -ItemType Directory -Path $csvDir -Force | Out-Null
  }

  $rows |
    Select-Object ProbeTimestamp, Triggered, PolicyBlockCount, TransientPolicyBlockCount, FailureCount, BlockedSuites, TransientSuites, JsonPath |
    Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8

  Write-Host "[INFO] Wrote CSV summary: $csvPath"
}
