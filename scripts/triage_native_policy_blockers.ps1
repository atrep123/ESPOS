param(
  [string]$HistoryPath = "reports/native_policy_probe_history.jsonl",
  [int]$Top = 5,
  [string]$MarkdownOut = "reports/native_policy_triage.md",
  [string]$CsvOut = "reports/native_policy_triage.csv",
  [int]$DeltaWindow = 0,
  [switch]$OnlyWorsening,
  [switch]$IncludeAllDeltaRows,
  [int]$MinAbsDeltaScore = 0,
  [string]$DeltaSortBy = "abs-delta"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ($Top -lt 1) {
  throw "Invalid value for -Top: must be >= 1"
}

if ($DeltaWindow -lt 0) {
  throw "Invalid value for -DeltaWindow: must be >= 0"
}

if ($OnlyWorsening -and $DeltaWindow -le 0) {
  throw "Invalid usage: -OnlyWorsening requires -DeltaWindow > 0"
}

if ($IncludeAllDeltaRows -and $DeltaWindow -le 0) {
  throw "Invalid usage: -IncludeAllDeltaRows requires -DeltaWindow > 0"
}

if ($MinAbsDeltaScore -lt 0) {
  throw "Invalid value for -MinAbsDeltaScore: must be >= 0"
}

if ($MinAbsDeltaScore -gt 0 -and $DeltaWindow -le 0) {
  throw "Invalid usage: -MinAbsDeltaScore requires -DeltaWindow > 0"
}

$allowedDeltaSortModes = @("abs-delta", "delta", "suite")
if (-not ($allowedDeltaSortModes -contains $DeltaSortBy)) {
  throw "Invalid value for -DeltaSortBy: must be one of abs-delta, delta, suite"
}

if ($DeltaSortBy -ne "abs-delta" -and $DeltaWindow -le 0) {
  throw "Invalid usage: -DeltaSortBy requires -DeltaWindow > 0 when set to delta or suite"
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$resolvedHistoryPath = Join-Path $repoRoot $HistoryPath
$resolvedMarkdownPath = Join-Path $repoRoot $MarkdownOut
$resolvedCsvPath = ""
if (-not [string]::IsNullOrWhiteSpace($CsvOut)) {
  $resolvedCsvPath = Join-Path $repoRoot $CsvOut
}

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

function Ensure-Suite([hashtable]$StatsMap, [string]$suiteName) {
  if ([string]::IsNullOrWhiteSpace($suiteName)) {
    return $null
  }

  if (-not $StatsMap.ContainsKey($suiteName)) {
    $StatsMap[$suiteName] = [pscustomobject]@{
      Suite = $suiteName
      PolicyHits = 0
      TransientHits = 0
    }
  }

  return $StatsMap[$suiteName]
}

function New-StatsMapFromRows([object[]]$InputRows) {
  $map = @{}

  foreach ($row in $InputRows) {
    $blockedSuites = @()
    $transientSuites = @()

    if ($row.PSObject.Properties.Name -contains "BlockedSuites") {
      $blockedSuites = @($row.BlockedSuites)
    }
    if ($row.PSObject.Properties.Name -contains "TransientSuites") {
      $transientSuites = @($row.TransientSuites)
    }

    foreach ($suite in $blockedSuites) {
      $entry = Ensure-Suite -StatsMap $map -suiteName ([string]$suite)
      if ($null -ne $entry) {
        $entry.PolicyHits++
      }
    }

    foreach ($suite in $transientSuites) {
      $entry = Ensure-Suite -StatsMap $map -suiteName ([string]$suite)
      if ($null -ne $entry) {
        $entry.TransientHits++
      }
    }
  }

  return $map
}

function Convert-StatsMapToRanked([hashtable]$StatsMap, [double]$RunCount) {
  return @(
    $StatsMap.Values |
      ForEach-Object {
        $policyRate = 0.0
        $transientRate = 0.0
        if ($RunCount -gt 0) {
          $policyRate = [Math]::Round((100.0 * $_.PolicyHits / $RunCount), 1)
          $transientRate = [Math]::Round((100.0 * $_.TransientHits / $RunCount), 1)
        }

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
}

$totalRuns = [double]$rows.Count
$stats = New-StatsMapFromRows -InputRows $rows

$ranked = Convert-StatsMapToRanked -StatsMap $stats -RunCount $totalRuns
$topRanked = @($ranked | Select-Object -First $Top)

$deltaEnabled = ($DeltaWindow -gt 0)
$deltaRecentWindow = 0
$deltaPreviousWindow = 0
$deltaTop = @()

if ($deltaEnabled) {
  $deltaRecentWindow = [Math]::Min($DeltaWindow, $rows.Count)
  $recentRows = @($rows | Select-Object -Last $deltaRecentWindow)

  $previousPool = @()
  if ($rows.Count -gt $deltaRecentWindow) {
    $previousPool = @($rows | Select-Object -First ($rows.Count - $deltaRecentWindow))
  }

  if ($previousPool.Count -gt 0) {
    $deltaPreviousWindow = [Math]::Min($DeltaWindow, $previousPool.Count)
  }

  if ($deltaPreviousWindow -gt 0) {
    $previousRows = @($previousPool | Select-Object -Last $deltaPreviousWindow)
    $recentMap = New-StatsMapFromRows -InputRows $recentRows
    $previousMap = New-StatsMapFromRows -InputRows $previousRows

    $suiteNames = @($recentMap.Keys + $previousMap.Keys | Sort-Object -Unique)
    $deltaRanked = @(
      foreach ($suiteName in $suiteNames) {
        $recentPolicy = 0
        $recentTransient = 0
        $previousPolicy = 0
        $previousTransient = 0

        if ($recentMap.ContainsKey($suiteName)) {
          $recentPolicy = [int]$recentMap[$suiteName].PolicyHits
          $recentTransient = [int]$recentMap[$suiteName].TransientHits
        }
        if ($previousMap.ContainsKey($suiteName)) {
          $previousPolicy = [int]$previousMap[$suiteName].PolicyHits
          $previousTransient = [int]$previousMap[$suiteName].TransientHits
        }

        $recentScore = (2 * $recentPolicy) + $recentTransient
        $previousScore = (2 * $previousPolicy) + $previousTransient

        [pscustomobject]@{
          Suite = $suiteName
          RecentScore = $recentScore
          PreviousScore = $previousScore
          DeltaScore = ($recentScore - $previousScore)
          RecentPolicyHits = $recentPolicy
          PreviousPolicyHits = $previousPolicy
          DeltaPolicyHits = ($recentPolicy - $previousPolicy)
          RecentTransientHits = $recentTransient
          PreviousTransientHits = $previousTransient
          DeltaTransientHits = ($recentTransient - $previousTransient)
        }
      }
    )

    if ($OnlyWorsening) {
      $deltaRanked = @($deltaRanked | Where-Object { $_.DeltaScore -gt 0 })
    }

    if ($MinAbsDeltaScore -gt 0) {
      $deltaRanked = @($deltaRanked | Where-Object { [Math]::Abs([int]$_.DeltaScore) -ge $MinAbsDeltaScore })
    }

    $deltaSorted = @()
    if ($DeltaSortBy -eq "suite") {
      $deltaSorted = @(
        $deltaRanked |
          Sort-Object @{Expression = 'Suite'; Descending = $false}, @{Expression = 'DeltaScore'; Descending = $true}
      )
    } elseif ($DeltaSortBy -eq "delta") {
      $deltaSorted = @(
        $deltaRanked |
          Sort-Object @{Expression = 'DeltaScore'; Descending = $true}, @{Expression = { [Math]::Abs([double]$_.DeltaScore) }; Descending = $true}, @{Expression = 'Suite'; Descending = $false}
      )
    } else {
      $deltaSorted = @(
        $deltaRanked |
          Sort-Object @{Expression = { [Math]::Abs([double]$_.DeltaScore) }; Descending = $true}, @{Expression = 'DeltaScore'; Descending = $true}, @{Expression = 'Suite'; Descending = $false}
      )
    }

    if ($IncludeAllDeltaRows) {
      $deltaTop = $deltaSorted
    } else {
      $deltaTop = @($deltaSorted | Select-Object -First $Top)
    }
  }
}

Write-Host "== Native Policy Blocker Triage =="
Write-Host "History: $resolvedHistoryPath"
Write-Host "Runs: $($rows.Count)"
Write-Host "Top: $Top"
if ($deltaEnabled) {
  Write-Host "DeltaWindow: $DeltaWindow"
  Write-Host "OnlyWorsening: $OnlyWorsening"
  Write-Host "IncludeAllDeltaRows: $IncludeAllDeltaRows"
  Write-Host "MinAbsDeltaScore: $MinAbsDeltaScore"
  Write-Host "DeltaSortBy: $DeltaSortBy"
}

if ($topRanked.Count -eq 0) {
  Write-Host "No blocked or transient suites found in history."
} else {
  Write-Host ""
  Write-Host "== Top Suites For Allow-List Priority =="
  $topRanked | Format-Table -AutoSize
}

if ($deltaEnabled) {
  Write-Host ""
  Write-Host "== Delta Trend (Recent vs Previous) =="
  if ($deltaPreviousWindow -eq 0) {
    Write-Host "Insufficient history for delta trend. Need at least 2 runs when -DeltaWindow is used."
  } elseif ($deltaTop.Count -eq 0) {
    if ($OnlyWorsening) {
      Write-Host "No worsening suite deltas found for requested windows."
    } else {
      Write-Host "No suite deltas found for requested windows."
    }
  } else {
    Write-Host "Recent window: $deltaRecentWindow run(s); Previous window: $deltaPreviousWindow run(s)"
    $deltaTop |
      Select-Object Suite, DeltaScore, DeltaPolicyHits, DeltaTransientHits, RecentScore, PreviousScore |
      Format-Table -AutoSize
  }
}

$outDir = Split-Path -Parent $resolvedMarkdownPath
if (-not [string]::IsNullOrWhiteSpace($outDir) -and -not (Test-Path $outDir)) {
  New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}

$csvRows = @()
$priorityRank = 1
foreach ($suite in $topRanked) {
  $csvRows += [pscustomobject]@{
    RowType = "PriorityTop"
    Rank = $priorityRank
    Suite = $suite.Suite
    Score = $suite.Score
    PolicyHits = $suite.PolicyHits
    PolicyRunRatePercent = $suite.PolicyRunRatePercent
    TransientHits = $suite.TransientHits
    TransientRunRatePercent = $suite.TransientRunRatePercent
    DeltaScore = $null
    DeltaPolicyHits = $null
    DeltaTransientHits = $null
    RecentScore = $null
    PreviousScore = $null
    DeltaWindow = $DeltaWindow
    OnlyWorsening = [bool]$OnlyWorsening
    IncludeAllDeltaRows = [bool]$IncludeAllDeltaRows
    MinAbsDeltaScore = $MinAbsDeltaScore
    DeltaSortBy = $DeltaSortBy
  }
  $priorityRank++
}

if ($deltaEnabled -and $deltaTop.Count -gt 0) {
  $deltaRank = 1
  $deltaRowType = "DeltaTop"
  if ($IncludeAllDeltaRows) {
    $deltaRowType = "DeltaAll"
  }
  foreach ($entry in $deltaTop) {
    $csvRows += [pscustomobject]@{
      RowType = $deltaRowType
      Rank = $deltaRank
      Suite = $entry.Suite
      Score = $null
      PolicyHits = $null
      PolicyRunRatePercent = $null
      TransientHits = $null
      TransientRunRatePercent = $null
      DeltaScore = $entry.DeltaScore
      DeltaPolicyHits = $entry.DeltaPolicyHits
      DeltaTransientHits = $entry.DeltaTransientHits
      RecentScore = $entry.RecentScore
      PreviousScore = $entry.PreviousScore
      DeltaWindow = $DeltaWindow
      OnlyWorsening = [bool]$OnlyWorsening
      IncludeAllDeltaRows = [bool]$IncludeAllDeltaRows
      MinAbsDeltaScore = $MinAbsDeltaScore
      DeltaSortBy = $DeltaSortBy
    }
    $deltaRank++
  }
}

$md = @()
$md += "# Native Policy Blocker Triage"
$md += ""
$md += ('- Generated: ' + (Get-Date).ToString('o'))
$md += ('- History: ' + $resolvedHistoryPath)
$md += ('- Runs: ' + $rows.Count)
$md += ('- Top: ' + $Top)
$md += ('- DeltaWindow: ' + $DeltaWindow)
$md += ('- OnlyWorsening: ' + $OnlyWorsening)
$md += ('- IncludeAllDeltaRows: ' + $IncludeAllDeltaRows)
$md += ('- MinAbsDeltaScore: ' + $MinAbsDeltaScore)
$md += ('- DeltaSortBy: ' + $DeltaSortBy)
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

if ($deltaEnabled) {
  $md += ""
  $md += "## Delta Trend (Recent vs Previous)"
  $md += ""
  if ($deltaPreviousWindow -eq 0) {
    $md += 'Insufficient history for delta trend. Need at least 2 runs when `-DeltaWindow` is used.'
  } elseif ($deltaTop.Count -eq 0) {
    if ($OnlyWorsening) {
      $md += "No worsening suite deltas found for requested windows."
    } else {
      $md += "No suite deltas found for requested windows."
    }
  } else {
    $md += ('- Recent window: ' + $deltaRecentWindow)
    $md += ('- Previous window: ' + $deltaPreviousWindow)
    $md += ('- IncludeAllDeltaRows: ' + $IncludeAllDeltaRows)
    $md += ('- MinAbsDeltaScore: ' + $MinAbsDeltaScore)
    $md += ('- DeltaSortBy: ' + $DeltaSortBy)
    $md += ""
    $md += "| Rank | Suite | DeltaScore | DeltaPolicyHits | DeltaTransientHits | RecentScore | PreviousScore |"
    $md += "|---:|---|---:|---:|---:|---:|---:|"

    $rank = 1
    foreach ($entry in $deltaTop) {
      $md += "| $rank | $($entry.Suite) | $($entry.DeltaScore) | $($entry.DeltaPolicyHits) | $($entry.DeltaTransientHits) | $($entry.RecentScore) | $($entry.PreviousScore) |"
      $rank++
    }
  }
}

Set-Content -Path $resolvedMarkdownPath -Value $md -Encoding UTF8
Write-Host ""
Write-Host "[INFO] Wrote triage report: $resolvedMarkdownPath"

if (-not [string]::IsNullOrWhiteSpace($resolvedCsvPath)) {
  $csvDir = Split-Path -Parent $resolvedCsvPath
  if (-not [string]::IsNullOrWhiteSpace($csvDir) -and -not (Test-Path $csvDir)) {
    New-Item -ItemType Directory -Path $csvDir -Force | Out-Null
  }

  $columns = @(
    "RowType",
    "Rank",
    "Suite",
    "Score",
    "PolicyHits",
    "PolicyRunRatePercent",
    "TransientHits",
    "TransientRunRatePercent",
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

  if ($csvRows.Count -eq 0) {
    Set-Content -Path $resolvedCsvPath -Value ($columns -join ',') -Encoding UTF8
  } else {
    $csvRows | Select-Object $columns | Export-Csv -Path $resolvedCsvPath -NoTypeInformation -Encoding UTF8
  }

  Write-Host "[INFO] Wrote triage CSV: $resolvedCsvPath"
}
