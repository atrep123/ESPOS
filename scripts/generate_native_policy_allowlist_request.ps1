param(
    [string]$ProbeJsonPath = "reports/native_policy_probe_auto.json",
    [string]$OutputPath = "reports/native_policy_allowlist_request.md"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ([string]::IsNullOrWhiteSpace($ProbeJsonPath)) {
    throw "Invalid value for -ProbeJsonPath: cannot be empty"
}

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    throw "Invalid value for -OutputPath: cannot be empty"
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$resolvedProbePath = Join-Path $repoRoot $ProbeJsonPath
$resolvedOutputPath = Join-Path $repoRoot $OutputPath

if (-not (Test-Path $resolvedProbePath)) {
    throw "Probe JSON not found: $resolvedProbePath"
}

$probe = Get-Content $resolvedProbePath -Raw | ConvertFrom-Json
$summary = $probe.Summary
$results = @($probe.Results)

if ($null -eq $summary -or $null -eq $probe.Results) {
    throw "Probe JSON missing required fields: Summary and Results"
}

$blocked = @($results | Where-Object { $_.Status -eq "POLICY_BLOCK" } | Select-Object -ExpandProperty Suite -Unique)
$transient = @($results | Where-Object { $_.Status -eq "POLICY_BLOCK_TRANSIENT" } | Select-Object -ExpandProperty Suite -Unique)

$nativeBuildDir = Join-Path $repoRoot ".pio\build\native"
$nativeExePattern = Join-Path $nativeBuildDir "*.exe"
$pioPython = Join-Path $env:USERPROFILE ".platformio\penv\Scripts\python.exe"

$outDir = Split-Path -Parent $resolvedOutputPath
if (-not [string]::IsNullOrWhiteSpace($outDir) -and -not (Test-Path $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}

$md = @()
$md += "# Native Policy Allow-List Request"
$md += ""
$md += ("Generated: " + (Get-Date).ToString('o'))
$md += "Repository: $repoRoot"
$md += "Probe Source: $resolvedProbePath"
$md += ""
$md += "## Why This Request"
$md += ""
$md += "Native PlatformIO test runs are intermittently blocked by Windows App Control policy (WinError 4551)."
$md += "Request allow-listing for local test executables and toolchain runtime so firmware CI-like checks can run reliably on this workstation."
$md += ""
$md += "## Recommended Allow-List Targets"
$md += ""
$md += "- Directory: $nativeBuildDir"
$md += "- Pattern: $nativeExePattern"
$md += "- Python runtime: $pioPython"
$md += ""
$md += "## Current Probe Summary"
$md += ""
$md += "- Triggered: $($summary.Triggered)"
$md += "- PolicyBlockCount: $($summary.PolicyBlockCount)"
$md += "- TransientPolicyBlockCount: $($summary.TransientPolicyBlockCount)"
$md += "- FailureCount: $($summary.FailureCount)"
$md += ""

if ($blocked.Count -gt 0) {
    $md += "## Suites With POLICY_BLOCK"
    $md += ""
    foreach ($suite in $blocked) {
        $md += "- $suite"
    }
    $md += ""
}

if ($transient.Count -gt 0) {
    $md += "## Suites With POLICY_BLOCK_TRANSIENT"
    $md += ""
    foreach ($suite in $transient) {
        $md += "- $suite"
    }
    $md += ""
}

Set-Content -Path $resolvedOutputPath -Value $md -Encoding UTF8
Write-Host "[INFO] Wrote allow-list request: $resolvedOutputPath"
