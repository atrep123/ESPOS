param(
    [switch]$SkipBuild,
    [int]$GuiTimeoutSec = 25
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $repoRoot

$python = ".\.venv\Scripts\python.exe"
$pyinstaller = ".\.venv\Scripts\pyinstaller.exe"
if (-not (Test-Path $python)) {
    throw "Python not found at $python. Activate/create .venv first."
}
if (-not (Test-Path $pyinstaller)) {
    throw "PyInstaller not found at $pyinstaller. Install requirements-dev.txt first."
}

$workDir = Join-Path $repoRoot "reports\smoke_app"
$distDir = Join-Path $repoRoot "dist"
$buildDir = Join-Path $repoRoot "build"
New-Item -ItemType Directory -Force -Path $workDir | Out-Null
$logFile = Join-Path $workDir "smoke_app.log"

# Move timeout multiplier definition before first use
$script:timeoutMultiplier = 1.0
if ($env:ESP32OS_TEST_TIMEOUT_MULTIPLIER) {
    try { $script:timeoutMultiplier = [double]$env:ESP32OS_TEST_TIMEOUT_MULTIPLIER } catch { }
    if ($script:timeoutMultiplier -le 0) { $script:timeoutMultiplier = 1.0 }
}

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$timestamp] $Message" | Tee-Object -FilePath $logFile -Append
}

$exeDir = Join-Path $distDir "ESP32OS_UI_Designer"
$exePath = Join-Path $exeDir "ESP32OS_UI_Designer.exe"

function Run-Checked {
    param([string]$Cmd, [string[]]$Arguments, [int]$TimeoutSec = 600)
    Write-Log ">>> $Cmd $($Arguments -join ' ')"
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Cmd
    $psi.Arguments = ($Arguments -join " ")
    $psi.WorkingDirectory = $repoRoot
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $p = New-Object System.Diagnostics.Process
    $p.StartInfo = $psi
    if (-not $p.Start()) { throw "Failed to start $Cmd" }
    $waitMs = [int]($TimeoutSec * $script:timeoutMultiplier * 1000)
    if (-not $p.WaitForExit($waitMs)) {
        try { $p.Kill() } catch {}
        throw "$Cmd timed out after ${TimeoutSec}s (multiplier $($script:timeoutMultiplier))"
    }
    $out = $p.StandardOutput.ReadToEnd()
    $err = $p.StandardError.ReadToEnd()
    if ($out) { Write-Log "[stdout] $out" }
    if ($err) { Write-Log "[stderr] $err" }
    if ($p.ExitCode -ne 0) {
        throw "$Cmd failed (exit $($p.ExitCode)): $err $out"
    }
    return @{ StdOut = $out; StdErr = $err }
}

function Stop-Simulators {
    param([string]$Reason = "")
    try {
        $procs = Get-Process python*, py -ErrorAction SilentlyContinue | Where-Object {
            try {
                $wmi = Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue
                $wmi -and $wmi.CommandLine -match "sim_run\.py"
            }
            catch { $false }
        }
        if ($procs) {
            Write-Log "[cleanup] stopping $($procs.Count) sim_run.py process(es) $Reason"
            foreach ($p in $procs) {
                Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
            }
        }
    }
    catch {
        Write-Log "[cleanup] simulator cleanup failed: $_"
    }
}

if (-not $SkipBuild) {
    Run-Checked -Cmd $pyinstaller -Arguments @(
        "ui_designer.spec",
        "--noconfirm",
        "--distpath", $distDir,
        "--workpath", $buildDir
    ) | Out-Null
}

if (-not (Test-Path $exePath)) {
    $fallback = Join-Path $repoRoot "dist\ESP32OS_UI_Designer\ESP32OS_UI_Designer.exe"
    if (Test-Path $fallback) {
        $exePath = $fallback
        Write-Host "Using existing EXE at $exePath"
    }
    else {
        throw "EXE not found at $exePath"
    }
}

# 1) EXE help
Run-Checked -Cmd $exePath -Arguments @("--help") | Out-Null

# 2) EXE GUI launch smoke (start/stop)
Write-Log ">>> $exePath --gui (smoke)"
$proc = Start-Process -FilePath $exePath -ArgumentList "--gui" -WorkingDirectory $repoRoot -PassThru
if (-not $proc) { throw "Failed to start $exePath" }
$deadline = (Get-Date).AddSeconds($GuiTimeoutSec * $script:timeoutMultiplier)
while (-not $proc.HasExited -and (Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 300
}
if ($proc.HasExited) {
    if ($proc.ExitCode -ne 0) {
        throw "GUI process exited early with code $($proc.ExitCode)"
    }
    Write-Log "[gui] exited quickly with code 0"
}
else {
    Write-Log "[gui] attempting graceful close..."
    $closed = $false
    try {
        $closed = $proc.CloseMainWindow()
    }
    catch {
        Write-Log "[gui] CloseMainWindow failed: $_"
    }
    $deadline2 = (Get-Date).AddSeconds(6)
    while (-not $proc.HasExited -and (Get-Date) -lt $deadline2) {
        Start-Sleep -Milliseconds 300
    }
    if (-not $proc.HasExited) {
        Write-Log "[gui] forcing kill pid=$($proc.Id)"
        try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch { Write-Log "[gui] force kill failed: $_" }
        try { $proc.WaitForExit(5000) | Out-Null } catch { }
    }
    if ($proc.HasExited -and $proc.ExitCode -ne 0) {
        throw "GUI process ended with code $($proc.ExitCode)"
    }
}

# 2b) UI automation smoke (pywinauto)
# Skip simulator during automation and cap simulator frames for async launches.
try {
    $env:ESP32OS_SMOKE_SKIP_SIM = "1"
    $env:ESP32OS_AUTOMATION_SIM_FRAMES = "8"
    
    # Check if pywinauto is available
    $checkPywinauto = & $python -c "import pywinauto; print('OK')" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Warning: pywinauto not available, skipping UI automation test" -ForegroundColor Yellow
    }
    else {
        Run-Checked -Cmd $python -Arguments @("-X", "utf8", "tools/ui_automation_smoke.py") -TimeoutSec 60 | Out-Null
    }
}
finally {
    # Always clean up env vars
    Remove-Item Env:ESP32OS_SMOKE_SKIP_SIM -ErrorAction SilentlyContinue
    Remove-Item Env:ESP32OS_AUTOMATION_SIM_FRAMES -ErrorAction SilentlyContinue
}

# 3) Headless preview PNG
$previewPng = Join-Path $workDir "preview.png"
Run-Checked -Cmd $python -Arguments @("-X", "utf8", "ui_designer_preview.py", "--headless", "--width", "64", "--height", "32", "--out-png", $previewPng) | Out-Null

# 4) Guided export (JSON/HTML/PNG)
$guidedJson = Join-Path $workDir "guided.json"
$guidedHtml = Join-Path $workDir "guided.html"
$guidedPng = Join-Path $workDir "guided.png"
Run-Checked -Cmd $python -Arguments @(
    "-X", "utf8",
    "ui_designer.py",
    "--demo", "--export",
    "--out-json", $guidedJson,
    "--out-html", $guidedHtml,
    "--out-png", $guidedPng
) | Out-Null

# 5) Simulator smoke (short run) - manual launch to avoid pipe deadlocks
Write-Log "Starting simulator smoke test..."
$simOutFile = Join-Path $workDir "sim_stdout.txt"
$simErrFile = Join-Path $workDir "sim_stderr.txt"

# Use Start-Process with file redirection to avoid pipe buffer deadlocks in Run-Checked
# ArgumentList must be a single string when using -RedirectStandardOutput
$simArgs = "-X utf8 `"sim_run.py`" --auto-size --max-frames 10"
Write-Log "[sim] Launching: $python $simArgs"

try {
    $simProc = Start-Process -FilePath $python -ArgumentList $simArgs -WorkingDirectory $repoRoot -RedirectStandardOutput $simOutFile -RedirectStandardError $simErrFile -NoNewWindow -PassThru -ErrorAction Stop
}
catch {
    Write-Log "[sim] Failed to start: $_"
    throw "Failed to start simulator: $_"
}

if (-not $simProc) { 
    throw "Failed to start simulator (null process)"
}

# Give process a moment to initialize
Start-Sleep -Milliseconds 500

Write-Log "[sim] Started pid=$($simProc.Id), waiting up to 30s..."
$simStartTime = Get-Date
$simDeadline = $simStartTime.AddSeconds(30 * $script:timeoutMultiplier)
$lastProgress = $simStartTime

while (-not $simProc.HasExited -and (Get-Date) -lt $simDeadline) {
    Start-Sleep -Milliseconds 500
    
    # Progress logging every 5 seconds
    $now = Get-Date
    if (($now - $lastProgress).TotalSeconds -ge 5) {
        $elapsed = ($now - $simStartTime).TotalSeconds
        Write-Log "[sim] Still running after $([int]$elapsed)s..."
        $lastProgress = $now
    }
}

if (-not $simProc.HasExited) {
    $elapsed = ((Get-Date) - $simStartTime).TotalSeconds
    Write-Log "[sim] Timeout after $([int]$elapsed)s, forcing kill..."
    
    try { 
        Stop-Process -Id $simProc.Id -Force -ErrorAction Stop
        Start-Sleep -Seconds 1
    }
    catch {
        Write-Log "[sim] Kill failed: $_"
    }
    
    # Dump output files for debugging
    if (Test-Path $simErrFile) { 
        $errContent = Get-Content $simErrFile -Raw -ErrorAction SilentlyContinue
        if ($errContent) { Write-Log "[sim stderr] $errContent" }
    }
    if (Test-Path $simOutFile) { 
        $outContent = Get-Content $simOutFile -Raw -ErrorAction SilentlyContinue
        if ($outContent) {
            $lines = $outContent -split "`r?`n"
            $tail = $lines | Select-Object -Last 30
            Write-Log "[sim stdout tail (30 lines)]`n$($tail -join "`n")"
        }
    }
    
    Stop-Simulators -Reason "(timeout cleanup)"
    throw "Simulator timed out after $([int]$elapsed)s"
}

$runTime = ((Get-Date) - $simStartTime).TotalSeconds
Write-Log "[sim] Process exited after $([math]::Round($runTime, 1))s with code $($simProc.ExitCode)"

if ($simProc.ExitCode -ne 0) {
    if (Test-Path $simErrFile) { 
        $errContent = Get-Content $simErrFile -Raw -ErrorAction SilentlyContinue
        if ($errContent) { Write-Log "[sim stderr] $errContent" }
    }
    if (Test-Path $simOutFile) { 
        $outLines = Get-Content $simOutFile -ErrorAction SilentlyContinue | Select-Object -Last 20
        if ($outLines) { Write-Log "[sim stdout tail]`n$($outLines -join "`n")" }
    }
    
    Stop-Simulators -Reason "(non-zero exit)"
    throw "Simulator failed with exit code $($simProc.ExitCode)"
}

Write-Log "[sim] Completed successfully"
if (Test-Path $simOutFile) { 
    $simSize = (Get-Item $simOutFile).Length
    Write-Log "[sim] Output size: $simSize bytes"
}

# Brief pause before cleanup
Start-Sleep -Milliseconds 500
Stop-Simulators -Reason "(cleanup after test)"

# 6) Validate artifacts
$requiredFiles = @($previewPng, $guidedJson, $guidedHtml, $guidedPng)
foreach ($f in $requiredFiles) {
    if (-not (Test-Path $f)) { throw "Missing output: $f" }
    $fileSize = (Get-Item $f).Length
    if ($fileSize -le 0) { throw "Empty output: $f" }
    Write-Log "Validated $f (size: $fileSize bytes)"
}

# PNG validation - make it optional but report clearly
$pngMinBytes = 100
foreach ($png in @($previewPng, $guidedPng)) {
    $pngSize = (Get-Item $png).Length
    if ($pngSize -lt $pngMinBytes) { 
        throw "PNG too small: $png (only $pngSize bytes)"
    }
}

# Optional PNG dimension check (may not work on all systems)
$pngDimCheckAvailable = $false
try { 
    Add-Type -AssemblyName System.Drawing -ErrorAction Stop
    $pngDimCheckAvailable = $true
}
catch { 
    Write-Log "[info] System.Drawing not available, skipping PNG dimension validation"
}

if ($pngDimCheckAvailable) {
    foreach ($png in @($previewPng, $guidedPng)) {
        try {
            $img = [System.Drawing.Image]::FromFile($png)
            try {
                if ($img.Width -ne 64 -or $img.Height -ne 32) {
                    Write-Log "[warn] PNG dimensions unexpected for $png (got $($img.Width)x$($img.Height), expected 64x32)"
                }
                else {
                    Write-Log "PNG dimensions OK for $png (64x32)"
                }
            }
            finally {
                $img.Dispose()
            }
        }
        catch {
            Write-Log "[warn] Could not check PNG dimensions for ${png}: $_"
        }
    }
}

# JSON structure validation
try {
    $jsonContent = Get-Content $guidedJson -Raw | ConvertFrom-Json
    if (-not $jsonContent.scenes) {
        throw "guided.json missing 'scenes' property"
    }
    if (-not $jsonContent.scenes.Demo) {
        throw "guided.json missing 'scenes.Demo' property"
    }
    Write-Log "JSON structure validated for $guidedJson"
}
catch {
    throw "JSON validation failed for ${guidedJson}: $_"
}

Write-Log "="*60
Write-Log "Smoke test completed successfully!"
Write-Log "Artifacts saved to: $workDir"
Write-Host "Smoke OK. Outputs in $workDir" -ForegroundColor Green
