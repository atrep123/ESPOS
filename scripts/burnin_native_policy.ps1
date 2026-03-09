param(
	[int]$Rounds = 10,
	[int]$DelaySeconds = 0,
	[switch]$SkipPython = $true,
	[switch]$IncludePioBuilds,
	[switch]$FailOnPolicyBlock,
	[string]$HistoryPath = "reports/native_policy_probe_history.jsonl",
	[string]$ProbeJsonPath = "reports/native_policy_probe_auto.json",
	[string]$MarkdownSummaryPath = "reports/native_policy_summary.md",
	[string]$CsvSummaryPath = "reports/native_policy_history.csv",
	[string]$TriageReportPath = "reports/native_policy_triage.md",
	[string]$TriageCsvPath = "reports/native_policy_triage.csv",
	[string]$TriageDeltaCsvPath = "",
	[int]$TriageTop = 5,
	[int]$TriageDeltaWindow = 0,
	[int]$TriageMinAbsDeltaScore = 0,
	[string]$TriageDeltaSortBy = "abs-delta",
	[switch]$TriageOnlyWorsening,
	[switch]$TriageIncludeAllDeltaRows,
	[switch]$SkipTriage,
	[switch]$SkipTriageCsvCheck,
	[switch]$SkipArtifactCheck,
	[switch]$ArchiveProbeSnapshots,
	[string]$ProbeSnapshotDir = "reports/native_policy_snapshots",
	[int]$MaxSnapshotFiles = 50
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ($Rounds -lt 1) {
	throw "Invalid value for -Rounds: must be >= 1"
}

if ($MaxSnapshotFiles -lt 1) {
	throw "Invalid value for -MaxSnapshotFiles: must be >= 1"
}

if ($TriageTop -lt 1) {
	throw "Invalid value for -TriageTop: must be >= 1"
}

if ($TriageDeltaWindow -lt 0) {
	throw "Invalid value for -TriageDeltaWindow: must be >= 0"
}

if ($TriageMinAbsDeltaScore -lt 0) {
	throw "Invalid value for -TriageMinAbsDeltaScore: must be >= 0"
}

$triageOnlyRequiresDeltaWindow = @()
if ($TriageOnlyWorsening) {
	$triageOnlyRequiresDeltaWindow += "-TriageOnlyWorsening"
}
if ($TriageIncludeAllDeltaRows) {
	$triageOnlyRequiresDeltaWindow += "-TriageIncludeAllDeltaRows"
}
if ($TriageMinAbsDeltaScore -gt 0) {
	$triageOnlyRequiresDeltaWindow += "-TriageMinAbsDeltaScore"
}
if ($PSBoundParameters.ContainsKey("TriageDeltaSortBy")) {
	$triageOnlyRequiresDeltaWindow += "-TriageDeltaSortBy"
}
if (-not [string]::IsNullOrWhiteSpace($TriageDeltaCsvPath)) {
	$triageOnlyRequiresDeltaWindow += "-TriageDeltaCsvPath"
}

if ($TriageDeltaWindow -le 0 -and $triageOnlyRequiresDeltaWindow.Count -gt 0) {
	throw "Delta triage options require -TriageDeltaWindow > 0: $($triageOnlyRequiresDeltaWindow -join ', ')"
}

if ($SkipTriage) {
	$triageFlagsWhenSkipped = @(
		"TriageReportPath",
		"TriageCsvPath",
		"TriageDeltaCsvPath",
		"TriageTop",
		"TriageDeltaWindow",
		"TriageMinAbsDeltaScore",
		"TriageDeltaSortBy",
		"TriageOnlyWorsening",
		"TriageIncludeAllDeltaRows",
		"SkipTriageCsvCheck"
	)
	$invalidWhenSkipTriage = @($triageFlagsWhenSkipped | Where-Object { $PSBoundParameters.ContainsKey($_) })
	if ($invalidWhenSkipTriage.Count -gt 0) {
		throw "-SkipTriage cannot be combined with explicit triage options: $($invalidWhenSkipTriage -join ', ')"
	}
}

$allowedDeltaSortModes = @("abs-delta", "delta", "suite")
if (-not ($allowedDeltaSortModes -contains $TriageDeltaSortBy)) {
	throw "Invalid value for -TriageDeltaSortBy: must be one of abs-delta, delta, suite"
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$checkAll = Join-Path $PSScriptRoot "check_all.ps1"
$summarize = Join-Path $PSScriptRoot "summarize_native_policy_history.ps1"
$triage = Join-Path $PSScriptRoot "triage_native_policy_blockers.ps1"
$triageCsvCheck = Join-Path $PSScriptRoot "check_native_policy_triage_csv.ps1"
$artifactCheck = Join-Path $PSScriptRoot "check_native_policy_artifacts.ps1"
$resolvedProbeJsonPath = Join-Path $repoRoot $ProbeJsonPath
$resolvedSnapshotDir = Join-Path $repoRoot $ProbeSnapshotDir

if ($ArchiveProbeSnapshots -and -not (Test-Path $resolvedSnapshotDir)) {
	New-Item -ItemType Directory -Path $resolvedSnapshotDir -Force | Out-Null
}

if (-not (Test-Path $checkAll)) {
	throw "Missing script: $checkAll"
}

$passed = 0
$failed = 0
$failRounds = @()
$policyBlockRounds = @()
$transientPolicyRounds = @()

for ($round = 1; $round -le $Rounds; $round++) {
	Write-Host ""
	Write-Host "== Burn-in round $round/$Rounds =="

	$checkAllParams = @{
		AllowNativePolicyBlock = $true
		NativePolicyHistoryJsonl = $HistoryPath
		NativePolicyProbeJson = $ProbeJsonPath
	}
	if ($SkipPython) {
		$checkAllParams.SkipPython = $true
	}
	if (-not $IncludePioBuilds) {
		$checkAllParams.Fast = $true
	}

	$exitCode = 0
	try {
		& $checkAll @checkAllParams
	}
	catch {
		$exitCode = 1
	}

	if ($ArchiveProbeSnapshots -and (Test-Path $resolvedProbeJsonPath)) {
		$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
		$snapshotPath = Join-Path $resolvedSnapshotDir ("probe_round{0:D2}_{1}.json" -f $round, $stamp)
		Copy-Item -Path $resolvedProbeJsonPath -Destination $snapshotPath -Force
		Write-Host "[INFO] Archived probe snapshot: $snapshotPath"

		$allSnapshots = @(Get-ChildItem -Path $resolvedSnapshotDir -Filter "*.json" | Sort-Object LastWriteTime -Descending)
		if ($allSnapshots.Count -gt $MaxSnapshotFiles) {
			$toDelete = @($allSnapshots | Select-Object -Skip $MaxSnapshotFiles)
			foreach ($old in $toDelete) {
				Remove-Item -Path $old.FullName -Force
			}
			Write-Host "[INFO] Pruned $($toDelete.Count) old snapshot(s); kept latest $MaxSnapshotFiles"
		}
	}

	if (Test-Path $resolvedProbeJsonPath) {
		try {
			$probe = Get-Content $resolvedProbeJsonPath -Raw | ConvertFrom-Json
			$summary = $probe.Summary
			$policyCount = [int]$summary.PolicyBlockCount
			$transientCount = [int]$summary.TransientPolicyBlockCount

			if ($policyCount -gt 0) {
				$policyBlockRounds += $round
				Write-Warning "Round $round recorded POLICY_BLOCK count: $policyCount"
			} elseif ($transientCount -gt 0) {
				$transientPolicyRounds += $round
				Write-Warning "Round $round recorded transient policy blocks: $transientCount"
			}
		}
		catch {
			Write-Warning "Round ${round}: unable to parse probe JSON at $resolvedProbeJsonPath"
		}
	}

	if ($exitCode -eq 0) {
		$passed++
	} else {
		$failed++
		$failRounds += $round
		Write-Warning "Round $round failed with exit code $exitCode"
	}

	if ($round -lt $Rounds -and $DelaySeconds -gt 0) {
		Start-Sleep -Seconds $DelaySeconds
	}
}

Write-Host ""
Write-Host "== Burn-in Summary =="
Write-Host "Rounds: $Rounds"
Write-Host "Passed: $passed"
Write-Host "Failed: $failed"
Write-Host "Rounds with POLICY_BLOCK: $($policyBlockRounds.Count)"
Write-Host "Rounds with transient policy block only: $($transientPolicyRounds.Count)"
if ($failRounds.Count -gt 0) {
	Write-Host "Failed rounds: $($failRounds -join ', ')"
}
if ($policyBlockRounds.Count -gt 0) {
	Write-Host "POLICY_BLOCK rounds: $($policyBlockRounds -join ', ')"
}
if ($transientPolicyRounds.Count -gt 0) {
	Write-Host "Transient-only rounds: $($transientPolicyRounds -join ', ')"
}

if (Test-Path $summarize) {
	Write-Host ""
	$sumParams = @{
		HistoryPath = $HistoryPath
		Last = [Math]::Max($Rounds, 20)
	}
	if (-not [string]::IsNullOrWhiteSpace($MarkdownSummaryPath)) {
		$sumParams.MarkdownOut = $MarkdownSummaryPath
	}
	if (-not [string]::IsNullOrWhiteSpace($CsvSummaryPath)) {
		$sumParams.CsvOut = $CsvSummaryPath
	}
	& $summarize @sumParams
}

if (-not $SkipTriage -and (Test-Path $triage)) {
	Write-Host ""
	$triageParams = @{
		HistoryPath = $HistoryPath
		Top = $TriageTop
	}

	if ($TriageDeltaWindow -gt 0) {
		$triageParams.DeltaWindow = $TriageDeltaWindow
	}

	if ($TriageOnlyWorsening) {
		$triageParams.OnlyWorsening = $true
	}

	if ($TriageIncludeAllDeltaRows) {
		$triageParams.IncludeAllDeltaRows = $true
	}

	if ($TriageMinAbsDeltaScore -gt 0) {
		$triageParams.MinAbsDeltaScore = $TriageMinAbsDeltaScore
	}

	if (-not [string]::IsNullOrWhiteSpace($TriageDeltaSortBy)) {
		$triageParams.DeltaSortBy = $TriageDeltaSortBy
	}

	if (-not [string]::IsNullOrWhiteSpace($TriageReportPath)) {
		$triageParams.MarkdownOut = $TriageReportPath
	}

	if (-not [string]::IsNullOrWhiteSpace($TriageCsvPath)) {
		$triageParams.CsvOut = $TriageCsvPath
	}

	if (-not [string]::IsNullOrWhiteSpace($TriageDeltaCsvPath)) {
		$triageParams.DeltaCsvOut = $TriageDeltaCsvPath
	}

	& $triage @triageParams

	if (-not $SkipTriageCsvCheck -and (Test-Path $triageCsvCheck)) {
		$triageCheckParams = @{}

		if (-not [string]::IsNullOrWhiteSpace($TriageCsvPath)) {
			$triageCheckParams.CombinedCsv = $TriageCsvPath
			$triageCheckParams.RequireCombined = $true
		}
		if (-not [string]::IsNullOrWhiteSpace($TriageDeltaCsvPath)) {
			$triageCheckParams.DeltaCsv = $TriageDeltaCsvPath
			$triageCheckParams.RequireDelta = $true
		}

		if ($triageCheckParams.Count -gt 0) {
			& $triageCsvCheck @triageCheckParams
		} else {
			Write-Host "[INFO] Triage CSV check skipped (no triage CSV outputs requested)."
		}
	}
}

if (-not $SkipArtifactCheck -and (Test-Path $artifactCheck)) {
	Write-Host ""
	$artifactParams = @{
		ProbeJson = $ProbeJsonPath
		HistoryJsonl = $HistoryPath
	}

	if (-not [string]::IsNullOrWhiteSpace($MarkdownSummaryPath)) {
		$artifactParams.SummaryMarkdown = $MarkdownSummaryPath
		$artifactParams.RequireMarkdown = $true
	}
	if (-not [string]::IsNullOrWhiteSpace($CsvSummaryPath)) {
		$artifactParams.HistoryCsv = $CsvSummaryPath
		$artifactParams.RequireCsv = $true
	}

	& $artifactCheck @artifactParams
}

if ($failed -gt 0) {
	exit 1
}

if ($FailOnPolicyBlock -and $policyBlockRounds.Count -gt 0) {
	Write-Error "Burn-in completed, but POLICY_BLOCK was detected in round(s): $($policyBlockRounds -join ', ')"
	exit 2
}

exit 0
