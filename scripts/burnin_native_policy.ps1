param(
	[int]$Rounds = 10,
	[int]$DelaySeconds = 0,
	[switch]$SkipPython = $true,
	[switch]$IncludePioBuilds,
	[string]$HistoryPath = "reports/native_policy_probe_history.jsonl",
	[string]$ProbeJsonPath = "reports/native_policy_probe_auto.json",
	[string]$MarkdownSummaryPath = "reports/native_policy_summary.md"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ($Rounds -lt 1) {
	throw "Invalid value for -Rounds: must be >= 1"
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$checkAll = Join-Path $PSScriptRoot "check_all.ps1"
$summarize = Join-Path $PSScriptRoot "summarize_native_policy_history.ps1"

if (-not (Test-Path $checkAll)) {
	throw "Missing script: $checkAll"
}

$passed = 0
$failed = 0
$failRounds = @()

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
if ($failRounds.Count -gt 0) {
	Write-Host "Failed rounds: $($failRounds -join ', ')"
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

exit 0
