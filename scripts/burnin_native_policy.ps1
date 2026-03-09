param(
	[int]$Rounds = 10,
	[int]$DelaySeconds = 0,
	[switch]$SkipPython = $true,
	[switch]$IncludePioBuilds,
	[switch]$FailOnPolicyBlock,
	[string]$HistoryPath = "reports/native_policy_probe_history.jsonl",
	[string]$ProbeJsonPath = "reports/native_policy_probe_auto.json",
	[string]$MarkdownSummaryPath = "reports/native_policy_summary.md",
	[switch]$ArchiveProbeSnapshots,
	[string]$ProbeSnapshotDir = "reports/native_policy_snapshots"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ($Rounds -lt 1) {
	throw "Invalid value for -Rounds: must be >= 1"
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$checkAll = Join-Path $PSScriptRoot "check_all.ps1"
$summarize = Join-Path $PSScriptRoot "summarize_native_policy_history.ps1"
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

	$args = @(
		"-ExecutionPolicy", "Bypass",
		"-File", $checkAll,
		"-AllowNativePolicyBlock",
		"-NativePolicyHistoryJsonl", $HistoryPath,
		"-NativePolicyProbeJson", $ProbeJsonPath
	)
	if ($SkipPython) {
		$args += "-SkipPython"
	}
	if (-not $IncludePioBuilds) {
		$args += "-Fast"
	}

	& powershell @args
	$exitCode = $LASTEXITCODE

	if ($ArchiveProbeSnapshots -and (Test-Path $resolvedProbeJsonPath)) {
		$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
		$snapshotPath = Join-Path $resolvedSnapshotDir ("probe_round{0:D2}_{1}.json" -f $round, $stamp)
		Copy-Item -Path $resolvedProbeJsonPath -Destination $snapshotPath -Force
		Write-Host "[INFO] Archived probe snapshot: $snapshotPath"
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
	$sumArgs = @(
		"-ExecutionPolicy", "Bypass",
		"-File", $summarize,
		"-HistoryPath", $HistoryPath,
		"-Last", ([Math]::Max($Rounds, 20))
	)
	if (-not [string]::IsNullOrWhiteSpace($MarkdownSummaryPath)) {
		$sumArgs += @("-MarkdownOut", $MarkdownSummaryPath)
	}
	& powershell @sumArgs
}

if ($failed -gt 0) {
	exit 1
}

if ($FailOnPolicyBlock -and $policyBlockRounds.Count -gt 0) {
	Write-Error "Burn-in completed, but POLICY_BLOCK was detected in round(s): $($policyBlockRounds -join ', ')"
	exit 2
}

exit 0
