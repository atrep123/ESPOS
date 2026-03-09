param(
  [string]$HistoryPath = "reports/native_policy_probe_history.jsonl",
  [int]$Last = 20,
  [string]$MarkdownOut = ""
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
    ForEach-Object { [pscustomobject]@{ Suite = $_.Key; Hits = $_.Value } } |
    Format-Table -AutoSize
}

if ($transientSuiteFreq.Count -gt 0) {
  Write-Host ""
  Write-Host "== Transient Suite Frequency =="
  $transientSuiteFreq.GetEnumerator() |
    Sort-Object Value -Descending |
    ForEach-Object { [pscustomobject]@{ Suite = $_.Key; Hits = $_.Value } } |
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
    $md += "| Suite | Hits |"
    $md += "|---|---:|"
    foreach ($pair in ($blockedSuiteFreq.GetEnumerator() | Sort-Object Value -Descending)) {
      $md += "| $($pair.Key) | $($pair.Value) |"
    }
  }

  if ($transientSuiteFreq.Count -gt 0) {
    $md += ""
    $md += "## Transient Suite Frequency"
    $md += ""
    $md += "| Suite | Hits |"
    $md += "|---|---:|"
    foreach ($pair in ($transientSuiteFreq.GetEnumerator() | Sort-Object Value -Descending)) {
      $md += "| $($pair.Key) | $($pair.Value) |"
    }
  }

  Set-Content -Path $mdPath -Value $md -Encoding UTF8
  Write-Host ""
  Write-Host "[INFO] Wrote Markdown summary: $mdPath"
}
