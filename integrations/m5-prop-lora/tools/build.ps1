[CmdletBinding()]
param(
    [switch]$Release,
    [switch]$ReleaseGatesOnly
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PioCoreRoot = Join-Path ([System.IO.Path]::GetPathRoot($RepoRoot)) ".pio-m5-prop-lora"
$HadFailure = $false
$RequireFirmwareToolchains = ($Release -or ($env:CI -eq "true")) -and -not $ReleaseGatesOnly

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

function Get-FirmwareBuildDefineArgs {
    if ($Release -or $ReleaseGatesOnly -or ($env:CI -eq "true")) {
        return @(
            "-DPROP_ALLOW_DRY_SMOKE_RUNTIME_KEY=0",
            "-DPROP_TX_ALLOW_SELFTEST_FIRE=0",
            "-DSELFTEST_FIRE=0",
            "-DDEBUG_HUD=0"
        )
    }

    return @()
}

function Set-ReleaseBuildFlagsEnv {
    $firmwareDefines = Get-FirmwareBuildDefineArgs
    if ($firmwareDefines.Count -eq 0) {
        return $null
    }

    $previous = $env:PROP_RELEASE_BUILD_FLAGS
    $env:PROP_RELEASE_BUILD_FLAGS = ($firmwareDefines -join " ")
    Write-Host "Firmware C/C++ defines: $env:PROP_RELEASE_BUILD_FLAGS"
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

function Get-ReleaseBuildDefineMap {
    param([AllowNull()][string]$Flags)

    $defines = @{}
    $duplicates = New-Object System.Collections.Generic.List[string]
    if ([string]::IsNullOrWhiteSpace($Flags)) {
        return [pscustomobject]@{
            Defines = $defines
            Duplicates = $duplicates
        }
    }

    foreach ($match in [regex]::Matches($Flags, '(?:^|\s)-D([A-Za-z_][A-Za-z0-9_]*)(?:=([^\s]+))?')) {
        $name = $match.Groups[1].Value
        $value = "1"
        if ($match.Groups[2].Success) {
            $value = $match.Groups[2].Value
        }
        if ($defines.ContainsKey($name)) {
            $duplicates.Add($name)
        }
        $defines[$name] = $value
    }

    return [pscustomobject]@{
        Defines = $defines
        Duplicates = $duplicates
    }
}

function Test-ReleaseDefineIsExactlyZero {
    param(
        [Parameter(Mandatory = $true)]$ParsedDefines,
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Message
    )

    if ($ParsedDefines.Duplicates -contains $Name) {
        Write-Error "Release build define $Name is set more than once." -ErrorAction Continue
        $script:HadFailure = $true
        return
    }
    if (-not $ParsedDefines.Defines.ContainsKey($Name) -or $ParsedDefines.Defines[$Name] -ne "0") {
        Write-Error $Message -ErrorAction Continue
        $script:HadFailure = $true
    }
}

function Test-RuntimeKeyAtRestPolicy {
    $sdkconfigPath = Join-Path $RepoRoot "firmware/dial-tx/sdkconfig"
    $partitionsPath = Join-Path $RepoRoot "firmware/dial-tx/partitions.csv"
    $dinPlatformioPath = Join-Path $RepoRoot "firmware/din-rx/platformio.ini"
    $sdkconfig = Get-Content -Raw -Path $sdkconfigPath
    $partitions = Get-Content -Raw -Path $partitionsPath
    $dinPlatformio = Get-Content -Raw -Path $dinPlatformioPath

    $dialProtectionMissing = (
        $sdkconfig -match "# CONFIG_SECURE_BOOT is not set" -or
        $sdkconfig -match "# CONFIG_SECURE_FLASH_ENC_ENABLED is not set" -or
        $sdkconfig -match "# CONFIG_FLASH_ENCRYPTION_ENABLED is not set"
    )
    $dinProtectionNotProven = (
        $dinPlatformio -notmatch "board_build\.partitions" -or
        $dinPlatformio -notmatch "flash_encrypt|secure_boot|nvs_encrypt"
    )
    $dialNvsPlain = $partitions -match "nvs,\s*data,\s*nvs,\s*0x9000,\s*0x6000"

    if (-not ($dialProtectionMissing -or $dinProtectionNotProven -or $dialNvsPlain)) {
        return
    }

    $decisionPath = $env:PROP_RUNTIME_KEY_AT_REST_DECISION
    if ([string]::IsNullOrWhiteSpace($decisionPath)) {
        $decisionPath = Join-Path $RepoRoot "docs/runtime_key_at_rest_decision.json"
    }
    if (-not (Test-Path $decisionPath)) {
        Write-Error "Runtime key-at-rest policy decision is required: $decisionPath" -ErrorAction Continue
        $script:HadFailure = $true
        return
    }

    try {
        $decisionText = Get-Content -Raw -Path $decisionPath
        $decision = $decisionText | ConvertFrom-Json
    }
    catch {
        Write-Error "Runtime key-at-rest policy decision is invalid JSON: $decisionPath" -ErrorAction Continue
        $script:HadFailure = $true
        return
    }

    if ($decision.schema -ne "prop-runtime-key-at-rest-decision-v1") {
        Write-Error "Runtime key-at-rest policy decision schema mismatch." -ErrorAction Continue
        $script:HadFailure = $true
    }
    if ($decision.status -notin @("accepted-with-waiver", "protected-and-verified")) {
        Write-Error "Runtime key-at-rest policy decision status is not accepted." -ErrorAction Continue
        $script:HadFailure = $true
    }
    if ($decision.raw_key_bytes_allowed_in_repo -ne $false) {
        Write-Error "Runtime key-at-rest policy must forbid raw key bytes in repo." -ErrorAction Continue
        $script:HadFailure = $true
    }
    if ([string]::IsNullOrWhiteSpace([string]$decision.rationale) -or
        [string]::IsNullOrWhiteSpace([string]$decision.reviewer)) {
        Write-Error "Runtime key-at-rest policy decision must include rationale and reviewer." -ErrorAction Continue
        $script:HadFailure = $true
    }
    if ($decisionText -match "00112233445566778899aabbccddeeff") {
        Write-Error "Runtime key-at-rest policy decision must not contain raw key bytes." -ErrorAction Continue
        $script:HadFailure = $true
    }
}

function Invoke-ReleaseGates {
    if (-not ($Release -or $ReleaseGatesOnly -or ($env:CI -eq "true"))) {
        return
    }

    $providerPath = Join-Path $RepoRoot "shared/protocol/prop_runtime_key.h"
    $txPath = Join-Path $RepoRoot "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp"
    $rxPath = Join-Path $RepoRoot "firmware/din-rx/src/prop_rx.cpp"
    $provider = Get-Content -Raw -Path $providerPath
    $tx = Get-Content -Raw -Path $txPath
    $rx = Get-Content -Raw -Path $rxPath
    if ($provider -notmatch "RuntimeKey" -or
        $provider -notmatch "NVS_NAMESPACE" -or
        $provider -notmatch "NVS_KEY" -or
        $provider -notmatch "isKnownDrySmokeKey" -or
        $provider -notmatch "PROP_ALLOW_DRY_SMOKE_RUNTIME_KEY") {
        Write-Error "Runtime HMAC key provider is incomplete." -ErrorAction Continue
        $script:HadFailure = $true
    }
    $releaseFlags = $env:PROP_RELEASE_BUILD_FLAGS
    if ([string]::IsNullOrWhiteSpace($releaseFlags)) {
        $releaseFlags = (Get-FirmwareBuildDefineArgs) -join " "
    }
    $parsedReleaseDefines = Get-ReleaseBuildDefineMap $releaseFlags
    Test-ReleaseDefineIsExactlyZero `
        -ParsedDefines $parsedReleaseDefines `
        -Name "PROP_ALLOW_DRY_SMOKE_RUNTIME_KEY" `
        -Message "Release builds must reject the dry-smoke runtime HMAC key."
    Test-ReleaseDefineIsExactlyZero `
        -ParsedDefines $parsedReleaseDefines `
        -Name "DEBUG_HUD" `
        -Message "Release builds must disable receiver debug HUD/serial diagnostics."
    Test-ReleaseDefineIsExactlyZero `
        -ParsedDefines $parsedReleaseDefines `
        -Name "PROP_TX_ALLOW_SELFTEST_FIRE" `
        -Message "Release builds must disable bench self-test fire override."
    Test-ReleaseDefineIsExactlyZero `
        -ParsedDefines $parsedReleaseDefines `
        -Name "SELFTEST_FIRE" `
        -Message "Release builds must keep bench auto-fire disabled."
    if ($tx -notmatch 'prop_runtime_key\.h' -or
        $rx -notmatch 'prop_runtime_key\.h' -or
        $tx -notmatch "load_runtime_key_from_nvs" -or
        $rx -notmatch "loadRuntimeKeyFromPreferences") {
        Write-Error "C++ firmware must use the runtime HMAC key provider." -ErrorAction Continue
        $script:HadFailure = $true
    }
    if ($tx -match "SHARED_KEY\s*\[\]" -or
        $rx -match "SHARED_KEY\s*\[\]" -or
        $tx -match "sizeof\s*\(\s*SHARED_KEY\s*\)" -or
        $rx -match "sizeof\s*\(\s*SHARED_KEY\s*\)") {
        Write-Error "C++ firmware still uses a source-embedded HMAC key." -ErrorAction Continue
        $script:HadFailure = $true
    }
    if ($tx -match "#define\s+SELFTEST_FIRE\s+1") {
        Write-Error "SELFTEST_FIRE is enabled; release builds must keep bench auto-fire disabled." -ErrorAction Continue
        $script:HadFailure = $true
    }
    Test-RuntimeKeyAtRestPolicy
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
        if ($RequireFirmwareToolchains) {
            Write-Error "$Target project was not found at $ProjectPath; required in CI/release mode." -ErrorAction Continue
            $script:HadFailure = $true
        }
        else {
            Write-Warning "$Target project was not found at $ProjectPath; skipping."
        }
        return
    }

    if (-not (Test-Path (Join-Path $ProjectPath "platformio.ini"))) {
        if ($RequireFirmwareToolchains) {
            Write-Error "$Target has no platformio.ini at $ProjectPath; required in CI/release mode." -ErrorAction Continue
            $script:HadFailure = $true
        }
        else {
            Write-Warning "$Target has no platformio.ini at $ProjectPath; skipping."
        }
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
if ($HadFailure -and ($Release -or $ReleaseGatesOnly -or ($env:CI -eq "true"))) {
    Write-Error "Release gates failed."
    exit 1
}
if ($ReleaseGatesOnly) {
    Write-Host "Release gates completed."
    exit 0
}
Invoke-PythonTests
Invoke-PlatformIOBuild -Target "c6l-modem" -ProjectPath (Join-Path $FirmwareRoot "c6l-modem")
Invoke-PlatformIOBuild -Target "sticks3-terminal" -ProjectPath (Join-Path $FirmwareRoot "sticks3-terminal")
Invoke-PlatformIOBuild -Target "din-rx" -ProjectPath (Join-Path $FirmwareRoot "din-rx")
Invoke-EspIdfBuild -Target "dial-tx" -ProjectPath (Join-Path $FirmwareRoot "dial-tx")

if ($HadFailure) {
    Write-Error "Build helper completed with failures."
    exit 1
}

Write-Host "Build helper completed."
