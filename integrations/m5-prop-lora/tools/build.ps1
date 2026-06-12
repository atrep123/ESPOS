[CmdletBinding()]
param(
    [switch]$Release
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PioCoreRoot = Join-Path ([System.IO.Path]::GetPathRoot($RepoRoot)) ".pio-m5-prop-lora"
$HadFailure = $false
$RequireFirmwareToolchains = $Release -or ($env:CI -eq "true")

function Find-Command {
    param([Parameter(Mandatory = $true)][string]$Name)
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd
    }
    if ($Name -eq "pio") {
        $localPio = Join-Path $env:USERPROFILE ".platformio\penv\Scripts\pio.exe"
        if (Test-Path $localPio) {
            return Get-Command $localPio
        }
    }
    return $null
}

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][scriptblock]$Action
    )

    Write-Host "==> $Name"
    try {
        & $Action
        if ($LASTEXITCODE -ne $null -and $LASTEXITCODE -ne 0) {
            Write-Error "$Name failed with exit code $LASTEXITCODE" -ErrorAction Continue
            $script:HadFailure = $true
        }
    }
    catch {
        Write-Error "$Name failed: $_" -ErrorAction Continue
        $script:HadFailure = $true
    }
}

function Invoke-PythonTests {
    $python = Find-Command "python"
    if (-not $python) {
        throw "Python was not found; cannot run tests."
    }

    Invoke-Step "Python tests" {
        Push-Location $RepoRoot
        try {
            & $python.Source -m pytest tests -v
        }
        finally {
            Pop-Location
        }
    }
}

function Get-ReleaseBuildDefineArgs {
    if (-not ($Release -or ($env:CI -eq "true"))) {
        return @()
    }

    return @(
        "-DPROP_ALLOW_PROTOTYPE_SHARED_KEY=0",
        "-DPROP_TX_ALLOW_SELFTEST_FIRE=0",
        "-DSELFTEST_FIRE=0"
    )
}

function Set-ReleaseBuildFlagsEnv {
    $releaseDefines = Get-ReleaseBuildDefineArgs
    if ($releaseDefines.Count -eq 0) {
        return $null
    }

    $previous = $env:PROP_RELEASE_BUILD_FLAGS
    $env:PROP_RELEASE_BUILD_FLAGS = ($releaseDefines -join " ")
    Write-Host "Release C/C++ defines: $env:PROP_RELEASE_BUILD_FLAGS"
    return $previous
}

function Restore-ReleaseBuildFlagsEnv {
    param([AllowNull()][string]$Previous)

    if ($null -eq $Previous) {
        Remove-Item Env:\PROP_RELEASE_BUILD_FLAGS -ErrorAction SilentlyContinue
    }
    else {
        $env:PROP_RELEASE_BUILD_FLAGS = $Previous
    }
}

function Invoke-ReleaseGates {
    if (-not ($Release -or ($env:CI -eq "true"))) {
        return
    }

    $tx = Get-Content -Raw -Path (Join-Path $RepoRoot "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp")
    $rx = Get-Content -Raw -Path (Join-Path $RepoRoot "firmware/din-rx/src/prop_rx.cpp")
    $ui = Get-Content -Raw -Path (Join-Path $RepoRoot "uiflow/dial/prop_frame.py")
    if ($tx -match "PROP_ALLOW_PROTOTYPE_SHARED_KEY" -or
        $rx -match "PROP_ALLOW_PROTOTYPE_SHARED_KEY" -or
        $ui -match 'PROTOTYPE_SHARED_KEY\s*=\s*True') {
        Write-Error "Prototype HMAC key is still compiled in; provision a release key before release builds." -ErrorAction Continue
        $script:HadFailure = $true
    }
    if ($tx -match "#define\s+SELFTEST_FIRE\s+1") {
        Write-Error "SELFTEST_FIRE is enabled; release builds must keep bench auto-fire disabled." -ErrorAction Continue
        $script:HadFailure = $true
    }
}

function Invoke-PlatformIOBuild {
    param(
        [Parameter(Mandatory = $true)][string]$Target,
        [Parameter(Mandatory = $true)][string]$ProjectPath
    )

    $pio = Find-Command "pio"
    if (-not $pio) {
        if ($RequireFirmwareToolchains) {
            Write-Error "PlatformIO command 'pio' was not found; required in CI/release mode for $Target build." -ErrorAction Continue
            $script:HadFailure = $true
        }
        else {
            Write-Warning "PlatformIO command 'pio' was not found; skipping $Target build."
        }
        return
    }

    if (-not (Test-Path $ProjectPath)) {
        Write-Warning "$Target project was not found at $ProjectPath; skipping."
        return
    }

    if (-not (Test-Path (Join-Path $ProjectPath "platformio.ini"))) {
        Write-Warning "$Target has no platformio.ini at $ProjectPath; skipping."
        return
    }

    Invoke-Step "PlatformIO build: $Target" {
        $oldCoreDir = $env:PLATFORMIO_CORE_DIR
        $oldReleaseFlags = Set-ReleaseBuildFlagsEnv
        $env:PLATFORMIO_CORE_DIR = Join-Path $PioCoreRoot $Target
        try {
            & $pio.Source run --project-dir $ProjectPath
        }
        finally {
            Restore-ReleaseBuildFlagsEnv $oldReleaseFlags
            if ($null -eq $oldCoreDir) {
                Remove-Item Env:\PLATFORMIO_CORE_DIR -ErrorAction SilentlyContinue
            }
            else {
                $env:PLATFORMIO_CORE_DIR = $oldCoreDir
            }
        }
    }
}

function Invoke-EspIdfBuild {
    param(
        [Parameter(Mandatory = $true)][string]$Target,
        [Parameter(Mandatory = $true)][string]$ProjectPath
    )

    $idf = Find-Command "idf.py"
    if (-not $idf) {
        if ($RequireFirmwareToolchains) {
            Write-Error "ESP-IDF command 'idf.py' was not found; required in CI/release mode for $Target build." -ErrorAction Continue
            $script:HadFailure = $true
        }
        else {
            Write-Warning "ESP-IDF command 'idf.py' was not found; skipping $Target build."
        }
        return
    }

    if (-not (Test-Path $ProjectPath)) {
        Write-Warning "$Target project was not found at $ProjectPath; skipping."
        return
    }

    Invoke-Step "ESP-IDF build: $Target" {
        Push-Location $ProjectPath
        $oldReleaseFlags = Set-ReleaseBuildFlagsEnv
        try {
            & $idf.Source build
        }
        finally {
            Restore-ReleaseBuildFlagsEnv $oldReleaseFlags
            Pop-Location
        }
    }
}

$FirmwareRoot = Join-Path $RepoRoot "firmware"

Invoke-ReleaseGates
if ($HadFailure -and ($Release -or ($env:CI -eq "true"))) {
    Write-Error "Release gates failed."
    exit 1
}
Invoke-PythonTests
Invoke-PlatformIOBuild -Target "c6l-modem" -ProjectPath (Join-Path $FirmwareRoot "c6l-modem")
Invoke-PlatformIOBuild -Target "din-rx" -ProjectPath (Join-Path $FirmwareRoot "din-rx")
Invoke-EspIdfBuild -Target "dial-tx" -ProjectPath (Join-Path $FirmwareRoot "dial-tx")

if ($HadFailure) {
    Write-Error "Build helper completed with failures."
    exit 1
}

Write-Host "Build helper completed."
