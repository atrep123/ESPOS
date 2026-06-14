[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("dial-tx", "din-rx", "c6l-modem", "sticks3-terminal")]
    [string]$Target,

    [Parameter(Mandatory = $true)]
    [string]$Port,

    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$FirmwareRoot = Join-Path $RepoRoot "firmware"
$ProjectPath = Join-Path $FirmwareRoot $Target
$PioCoreRoot = Join-Path ([System.IO.Path]::GetPathRoot($RepoRoot)) ".pio-m5-prop-lora"

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

if (-not (Test-Path $ProjectPath)) {
    Write-Error "$Target project was not found at $ProjectPath."
    exit 1
}

function Invoke-PlatformIOUpload {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectPath,
        [Parameter(Mandatory = $true)][string]$Environment,
        [Parameter(Mandatory = $true)][string]$Port
    )

    $pio = Find-Command "pio"
    if (-not $pio) {
        Write-Error "PlatformIO command 'pio' was not found; cannot flash $Target."
        exit 1
    }

    $oldCoreDir = $env:PLATFORMIO_CORE_DIR
    $env:PLATFORMIO_CORE_DIR = Join-Path $PioCoreRoot $Target
    try {
        $args = @("run", "--project-dir", $ProjectPath, "-e", $Environment, "--target", "upload", "--upload-port", $Port)
        if ($DryRun) {
            Write-Host "DRY RUN: $($pio.Source) $($args -join ' ')"
            return
        }
        & $pio.Source @args
        exit $LASTEXITCODE
    }
    finally {
        if ($null -eq $oldCoreDir) {
            Remove-Item Env:\PLATFORMIO_CORE_DIR -ErrorAction SilentlyContinue
        }
        else {
            $env:PLATFORMIO_CORE_DIR = $oldCoreDir
        }
    }
}

switch ($Target) {
    "c6l-modem" {
        Invoke-PlatformIOUpload -ProjectPath $ProjectPath -Environment "m5stack-c6l" -Port $Port
    }

    "sticks3-terminal" {
        if (-not (Test-Path (Join-Path $ProjectPath "platformio.ini"))) {
            Write-Error "$Target has no platformio.ini at $ProjectPath."
            exit 1
        }

        Invoke-PlatformIOUpload -ProjectPath $ProjectPath -Environment "sticks3-terminal" -Port $Port
    }

    "dial-tx" {
        $idf = Find-Command "idf.py"
        if (-not $idf) {
            if ($DryRun) {
                Write-Host "DRY RUN: idf.py -p $Port flash"
                exit 0
            }
            Write-Error "ESP-IDF command 'idf.py' was not found; cannot flash dial-tx."
            exit 1
        }

        Push-Location $ProjectPath
        try {
            $args = @("-p", $Port, "flash")
            if ($DryRun) {
                Write-Host "DRY RUN: $($idf.Source) $($args -join ' ')"
                exit 0
            }
            & $idf.Source @args
            exit $LASTEXITCODE
        }
        finally {
            Pop-Location
        }
    }

    "din-rx" {
        if (-not (Test-Path (Join-Path $ProjectPath "platformio.ini"))) {
            Write-Error "$Target has no platformio.ini at $ProjectPath."
            exit 1
        }

        Invoke-PlatformIOUpload -ProjectPath $ProjectPath -Environment "esp32-s3-devkitc-1" -Port $Port
    }
}
