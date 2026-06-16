<#
.SYNOPSIS
    Build-matrix runner for the M5 prop-lora stack: compiles EVERY PlatformIO
    environment across the firmware projects, prints a pass/fail/skip scoreboard,
    writes per-env logs + a machine-readable JSON summary, and returns a non-zero
    exit code if anything failed (CI-friendly).

.DESCRIPTION
    This institutionalises the one-off "debug all sestavy" sweep. Environments are
    DISCOVERED from each platformio.ini at runtime (no hard-coded env lists), so new
    envs are picked up automatically. Each monorepo project builds in its isolated
    PlatformIO core (C:\.pio-m5-prop-lora\<project>) and is run through the Arduino
    framework integrity gate (self-heal of truncated package extractions) before
    building. Logs land under build/logs/build_matrix_<timestamp>/ and a summary.json
    captures per-env status, duration, flash/RAM usage and error excerpts.

.PARAMETER Projects
    Optional filter: only build these project names (e.g. din-rx, dualkey-tx).
    Default: all monorepo firmware projects.

.PARAMETER IncludeExternalRepos
    Also build the standalone xiao + terminal repos if found on disk.

.PARAMETER XiaoRepo / TerminalRepo
    Override paths to the standalone repos (default: <UserProfile>\Desktop\...).

.PARAMETER IncludeDial
    Also build the ESP-IDF dial-tx firmware (requires idf.py on PATH or -IdfExport).

.PARAMETER IdfExport
    Path to ESP-IDF export.ps1 to dot-source before building dial-tx.

.PARAMETER WithTests
    Also run the Python pytest suite(s) and include them in the scoreboard.

.PARAMETER DebugBuild
    Stream full build output to the console and KEEP every per-env log (otherwise
    only failed-env logs are retained; the JSON summary is always written).

.PARAMETER FailFast
    Stop at the first failing environment instead of building the whole matrix.

.EXAMPLE
    pwsh tools/build_matrix.ps1
.EXAMPLE
    pwsh tools/build_matrix.ps1 -Projects din-rx,dualkey-tx -DebugBuild
.EXAMPLE
    pwsh tools/build_matrix.ps1 -IncludeExternalRepos -WithTests
#>
[CmdletBinding()]
param(
    [string[]]$Projects,
    [switch]$IncludeExternalRepos,
    [string]$XiaoRepo,
    [string]$TerminalRepo,
    [switch]$IncludeDial,
    [string]$IdfExport,
    [switch]$WithTests,
    [switch]$DebugBuild,
    [switch]$FailFast
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PioCoreRoot = Join-Path ([System.IO.Path]::GetPathRoot($RepoRoot)) ".pio-m5-prop-lora"
$FirmwareRoot = Join-Path $RepoRoot "firmware"
$HadFailure = $false   # set by the integrity gate in build_common.ps1
. (Join-Path $PSScriptRoot "build_common.ps1")

$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$logRoot = Join-Path $RepoRoot ("build/logs/build_matrix_" + $timestamp)
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null

$results = New-Object System.Collections.Generic.List[object]
$pio = Find-Command "pio"
# Capture the system python NOW, before the optional ESP-IDF dial step dot-sources
# export.ps1 and prepends the IDF venv python (which has no pytest) to PATH.
$pythonAtStart = Find-Command "python"

function Get-PioEnvs {
    param([Parameter(Mandatory = $true)][string]$ProjectDir)
    $ini = Join-Path $ProjectDir "platformio.ini"
    if (-not (Test-Path $ini)) { return @() }
    $envs = @()
    foreach ($line in Get-Content -Path $ini) {
        $m = [regex]::Match($line, '^\s*\[env:(.+?)\]\s*$')
        if ($m.Success) { $envs += $m.Groups[1].Value }
    }
    return @($envs)
}

function Add-Result {
    param($Project, $EnvName, $Kind, $Status, $DurationSec, $FlashPct, $RamPct, $ErrorText, $LogFile)
    $results.Add([PSCustomObject]@{
        Project     = $Project
        Env         = $EnvName
        Kind        = $Kind
        Status      = $Status
        DurationSec = $DurationSec
        FlashPct    = $FlashPct
        RamPct      = $RamPct
        Error       = $ErrorText
        Log         = $LogFile
    }) | Out-Null
}

function Get-LogTail {
    param([string]$LogFile, [int]$Count = 25)
    if (-not (Test-Path $LogFile)) { return "" }
    $lines = Get-Content -Path $LogFile | Where-Object { $_.Trim() -ne "" }
    return (($lines | Select-Object -Last $Count) -join "`n")
}

function Invoke-PioEnvBuild {
    param(
        [string]$Project,
        [string]$ProjectDir,
        [string]$EnvName,
        [string]$LogFile
    )
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        if ($DebugBuild) {
            & $pio.Source run --project-dir $ProjectDir -e $EnvName 2>&1 | Tee-Object -FilePath $LogFile | Out-Host
        }
        else {
            & $pio.Source run --project-dir $ProjectDir -e $EnvName 2>&1 | Out-File -FilePath $LogFile -Encoding utf8
        }
        $code = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $prevEAP
    }
    $sw.Stop()

    $flash = $null; $ram = $null
    $logText = ""
    if (Test-Path $LogFile) { $logText = Get-Content -Raw -Path $LogFile }
    $ramM = [regex]::Matches($logText, 'RAM:\s+\[[^\]]*\]\s+([\d.]+)%')
    if ($ramM.Count -gt 0) { $ram = [double]$ramM[$ramM.Count - 1].Groups[1].Value }
    $flashM = [regex]::Matches($logText, 'Flash:\s+\[[^\]]*\]\s+([\d.]+)%')
    if ($flashM.Count -gt 0) { $flash = [double]$flashM[$flashM.Count - 1].Groups[1].Value }

    $status = if ($code -eq 0) { 'PASS' } else { 'FAIL' }
    $err = if ($code -eq 0) { "" } else { Get-LogTail -LogFile $LogFile }
    Add-Result -Project $Project -EnvName $EnvName -Kind 'pio' -Status $status `
        -DurationSec ([math]::Round($sw.Elapsed.TotalSeconds, 1)) -FlashPct $flash -RamPct $ram `
        -ErrorText $err -LogFile $LogFile
    return $status
}

# ----- assemble the list of PlatformIO build units (project + isolated core) -----
$units = @()
$monoProjects = @('c6l-modem', 'dualkey-tx', 'sticks3-terminal', 'din-rx')
foreach ($p in $monoProjects) {
    $units += [PSCustomObject]@{
        Name = $p; ProjectDir = (Join-Path $FirmwareRoot $p); CoreDir = (Join-Path $PioCoreRoot $p)
    }
}

if ($IncludeExternalRepos) {
    if (-not $XiaoRepo) { $XiaoRepo = Join-Path $env:USERPROFILE 'Desktop\xiao-prop-electronics-private' }
    if (-not $TerminalRepo) { $TerminalRepo = Join-Path $env:USERPROFILE 'Desktop\m5stick-terminal-private' }
    if (Test-Path (Join-Path $XiaoRepo 'platformio.ini')) {
        $units += [PSCustomObject]@{ Name = 'xiao'; ProjectDir = $XiaoRepo; CoreDir = $null }
    }
    else { Write-Warning "xiao repo not found at $XiaoRepo; skipping." }
    $termProj = Join-Path $TerminalRepo 'firmware\sticks3-terminal'
    if (Test-Path (Join-Path $termProj 'platformio.ini')) {
        $units += [PSCustomObject]@{ Name = 'terminal-std'; ProjectDir = $termProj; CoreDir = $null }
    }
    else { Write-Warning "terminal repo not found at $termProj; skipping." }
}

if ($Projects) {
    $units = $units | Where-Object { $Projects -contains $_.Name }
}

# ----- build -----
$abort = $false
if (-not $pio) {
    Write-Warning "PlatformIO 'pio' was not found; all PlatformIO builds will be skipped."
}

foreach ($unit in $units) {
    if ($abort) { break }
    Write-Host ""
    Write-Host ("===== {0} =====" -f $unit.Name) -ForegroundColor Cyan

    if (-not (Test-Path (Join-Path $unit.ProjectDir 'platformio.ini'))) {
        Add-Result -Project $unit.Name -EnvName '(project)' -Kind 'pio' -Status 'SKIP' -DurationSec 0 -FlashPct $null -RamPct $null -ErrorText 'no platformio.ini' -LogFile ''
        continue
    }
    if (-not $pio) {
        Add-Result -Project $unit.Name -EnvName '(project)' -Kind 'pio' -Status 'SKIP' -DurationSec 0 -FlashPct $null -RamPct $null -ErrorText 'pio not found' -LogFile ''
        continue
    }

    $oldCore = $env:PLATFORMIO_CORE_DIR
    try {
        if ($unit.CoreDir) {
            $env:PLATFORMIO_CORE_DIR = $unit.CoreDir
            # self-heal a truncated Arduino framework before building this project's envs
            Confirm-ArduinoFrameworkVariants -Target $unit.Name -ProjectPath $unit.ProjectDir -CoreDir $unit.CoreDir
        }
        else {
            Remove-Item Env:\PLATFORMIO_CORE_DIR -ErrorAction SilentlyContinue
        }

        $envs = Get-PioEnvs -ProjectDir $unit.ProjectDir
        if ($envs.Count -eq 0) {
            Add-Result -Project $unit.Name -EnvName '(no envs)' -Kind 'pio' -Status 'SKIP' -DurationSec 0 -FlashPct $null -RamPct $null -ErrorText 'no [env:] sections' -LogFile ''
            continue
        }

        foreach ($e in $envs) {
            $logFile = Join-Path $logRoot ("{0}__{1}.log" -f $unit.Name, $e)
            Write-Host ("  building {0} ..." -f $e) -NoNewline
            $status = Invoke-PioEnvBuild -Project $unit.Name -ProjectDir $unit.ProjectDir -EnvName $e -LogFile $logFile
            if ($status -eq 'PASS') { Write-Host " PASS" -ForegroundColor Green }
            else { Write-Host " FAIL" -ForegroundColor Red }
            if ($status -eq 'FAIL' -and $FailFast) { $abort = $true; break }
        }
    }
    finally {
        if ($null -eq $oldCore) { Remove-Item Env:\PLATFORMIO_CORE_DIR -ErrorAction SilentlyContinue }
        else { $env:PLATFORMIO_CORE_DIR = $oldCore }
    }
}

# ----- optional: ESP-IDF dial-tx -----
if ($IncludeDial -and -not $abort) {
    Write-Host ""
    Write-Host "===== dial-tx (ESP-IDF) =====" -ForegroundColor Cyan
    $dialDir = Join-Path $FirmwareRoot 'dial-tx'
    $dialLog = Join-Path $logRoot 'dial-tx__idf.log'
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $status = 'SKIP'; $err = ''
    $prevEAP = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    try {
        if ($IdfExport -and (Test-Path $IdfExport)) {
            Write-Host "  loading ESP-IDF env from $IdfExport ..."
            . $IdfExport *> $dialLog
        }
        # After export.ps1, idf.py may be a function (its .Source is empty), so invoke
        # by name rather than via $idf.Source.
        $idf = Find-Command "idf.py"
        if (-not $idf) {
            $status = 'SKIP'; $err = 'idf.py not found (pass -IdfExport)'
            Write-Host "  SKIP (idf.py not found)" -ForegroundColor Yellow
        }
        else {
            & idf.py -C $dialDir build 2>&1 | Out-File -FilePath $dialLog -Append -Encoding utf8
            if ($LASTEXITCODE -eq 0) { $status = 'PASS' }
            else { $status = 'FAIL'; $err = Get-LogTail -LogFile $dialLog }
        }
    }
    catch {
        $status = 'FAIL'; $err = $_.Exception.Message
    }
    finally {
        $ErrorActionPreference = $prevEAP
    }
    $sw.Stop()
    if ($status -ne 'SKIP') {
        Add-Result -Project 'dial-tx' -EnvName 'idf-build' -Kind 'esp-idf' -Status $status -DurationSec ([math]::Round($sw.Elapsed.TotalSeconds, 1)) -FlashPct $null -RamPct $null -ErrorText $err -LogFile $dialLog
        $col = if ($status -eq 'PASS') { 'Green' } else { 'Red' }
        Write-Host ("  {0}" -f $status) -ForegroundColor $col
    }
    else {
        Add-Result -Project 'dial-tx' -EnvName 'idf-build' -Kind 'esp-idf' -Status 'SKIP' -DurationSec 0 -FlashPct $null -RamPct $null -ErrorText $err -LogFile ''
    }
}

# ----- optional: pytest -----
if ($WithTests -and -not $abort) {
    Write-Host ""
    Write-Host "===== pytest =====" -ForegroundColor Cyan
    $python = $pythonAtStart
    $pyUnits = @(@{ Name = 'monorepo'; Dir = (Join-Path $RepoRoot 'tests') })
    if ($IncludeExternalRepos) {
        if ($XiaoRepo -and (Test-Path (Join-Path $XiaoRepo 'tests'))) { $pyUnits += @{ Name = 'xiao'; Dir = (Join-Path $XiaoRepo 'tests') } }
        if ($TerminalRepo -and (Test-Path (Join-Path $TerminalRepo 'tests'))) { $pyUnits += @{ Name = 'terminal-std'; Dir = (Join-Path $TerminalRepo 'tests') } }
    }
    foreach ($pu in $pyUnits) {
        $logFile = Join-Path $logRoot ("pytest__{0}.log" -f $pu.Name)
        if (-not $python) {
            Add-Result -Project 'pytest' -EnvName $pu.Name -Kind 'pytest' -Status 'SKIP' -DurationSec 0 -FlashPct $null -RamPct $null -ErrorText 'python not found' -LogFile ''
            continue
        }
        Write-Host ("  pytest {0} ..." -f $pu.Name) -NoNewline
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $prevEAP = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
        $oldEnc = $env:PYTHONIOENCODING; $env:PYTHONIOENCODING = 'utf-8'
        try {
            & $python.Source -m pytest -q $pu.Dir 2>&1 | Out-File -FilePath $logFile -Encoding utf8
            $code = $LASTEXITCODE
        }
        finally { $ErrorActionPreference = $prevEAP; $env:PYTHONIOENCODING = $oldEnc }
        $sw.Stop()
        $status = if ($code -eq 0) { 'PASS' } else { 'FAIL' }
        $err = if ($code -eq 0) { "" } else { Get-LogTail -LogFile $logFile }
        Add-Result -Project 'pytest' -EnvName $pu.Name -Kind 'pytest' -Status $status -DurationSec ([math]::Round($sw.Elapsed.TotalSeconds, 1)) -FlashPct $null -RamPct $null -ErrorText $err -LogFile $logFile
        if ($status -eq 'PASS') { Write-Host " PASS" -ForegroundColor Green } else { Write-Host " FAIL" -ForegroundColor Red }
    }
}

# ----- prune passed-env logs unless -DebugBuild -----
if (-not $DebugBuild) {
    foreach ($r in $results) {
        if ($r.Status -eq 'PASS' -and $r.Log -and (Test-Path $r.Log)) {
            Remove-Item -LiteralPath $r.Log -Force -ErrorAction SilentlyContinue
        }
    }
}

# ----- write JSON summary -----
$summaryObj = [PSCustomObject]@{
    timestamp = $timestamp
    repoRoot  = $RepoRoot
    total     = $results.Count
    pass      = (@($results | Where-Object { $_.Status -eq 'PASS' })).Count
    fail      = (@($results | Where-Object { $_.Status -eq 'FAIL' })).Count
    skip      = (@($results | Where-Object { $_.Status -eq 'SKIP' })).Count
    results   = $results
}
# UTF-8 WITHOUT BOM so jq / Python / other JSON consumers can read it
# (Out-File -Encoding utf8 emits a BOM on Windows PowerShell 5.1).
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$summaryJson = $summaryObj | ConvertTo-Json -Depth 6
$summaryPath = Join-Path $logRoot 'summary.json'
[System.IO.File]::WriteAllText($summaryPath, $summaryJson, $utf8NoBom)
$latestPath = Join-Path $RepoRoot 'build/logs/build_matrix_latest.json'
[System.IO.File]::WriteAllText($latestPath, $summaryJson, $utf8NoBom)

# ----- scoreboard -----
Write-Host ""
Write-Host "================= SCOREBOARD =================" -ForegroundColor Cyan
$byProject = $results | Group-Object Project
$rows = foreach ($g in $byProject) {
    [PSCustomObject]@{
        Project = $g.Name
        Pass    = (@($g.Group | Where-Object { $_.Status -eq 'PASS' })).Count
        Fail    = (@($g.Group | Where-Object { $_.Status -eq 'FAIL' })).Count
        Skip    = (@($g.Group | Where-Object { $_.Status -eq 'SKIP' })).Count
    }
}
$rows | Format-Table -AutoSize | Out-Host
Write-Host ("TOTAL: {0} pass / {1} fail / {2} skip  (of {3})" -f $summaryObj.pass, $summaryObj.fail, $summaryObj.skip, $summaryObj.total)

$failed = @($results | Where-Object { $_.Status -eq 'FAIL' })
if ($failed.Count -gt 0) {
    Write-Host ""
    Write-Host "----- FAILURES -----" -ForegroundColor Red
    foreach ($f in $failed) {
        Write-Host ("[{0}] {1}" -f $f.Project, $f.Env) -ForegroundColor Red
        $firstErr = ($f.Error -split "`n" | Where-Object { $_ -match 'error|Error|fatal|undefined reference|No such file|\[FAILED\]' } | Select-Object -First 4) -join "`n    "
        if ($firstErr) { Write-Host ("    " + $firstErr) }
        if ($f.Log) { Write-Host ("    log: " + $f.Log) -ForegroundColor DarkGray }
    }
}

Write-Host ""
Write-Host ("JSON summary: {0}" -f $summaryPath) -ForegroundColor DarkGray
Write-Host ("Logs:         {0}" -f $logRoot) -ForegroundColor DarkGray

if ($summaryObj.fail -gt 0) { exit 1 } else { exit 0 }
