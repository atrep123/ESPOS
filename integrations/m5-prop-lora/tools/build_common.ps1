# Shared build helpers for the m5-prop-lora tooling.
# Dot-sourced by tools/build.ps1 and tools/build_matrix.ps1 so the toolchain
# lookup and the Arduino-ESP32 framework integrity gate live in exactly one place.
#
# Functions that report build problems set $script:HadFailure = $true in the
# dot-sourcing script's scope; callers should initialise $HadFailure = $false.

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

function Get-MissingArduinoVariants {
    # Returns the Arduino-ESP32 board variant header(s) that the project needs but
    # are absent from the given isolated core. Empty when the core is healthy or is
    # not an Arduino-ESP32 core. Guards against a truncated/interrupted package
    # extraction that still reports a complete install via its .piopm marker.
    param(
        [Parameter(Mandatory = $true)][string]$ProjectPath,
        [Parameter(Mandatory = $true)][string]$CoreDir
    )

    $variantsDir = Join-Path $CoreDir "packages\framework-arduinoespressif32\variants"
    if (-not (Test-Path $variantsDir)) {
        return @()
    }

    $iniPath = Join-Path $ProjectPath "platformio.ini"
    if (-not (Test-Path $iniPath)) {
        return @()
    }

    $boards = @()
    foreach ($line in Get-Content -Path $iniPath) {
        $m = [regex]::Match($line, '^\s*board\s*=\s*([^\s#;]+)')
        if ($m.Success) {
            $boards += $m.Groups[1].Value
        }
    }
    $boards = @($boards | Sort-Object -Unique)

    $boardSearchRoots = @(
        (Join-Path $CoreDir "platforms\espressif32\boards"),
        (Join-Path $env:USERPROFILE ".platformio\platforms\espressif32\boards")
    )

    $missing = New-Object System.Collections.Generic.List[string]
    foreach ($board in $boards) {
        $variant = $null
        foreach ($root in $boardSearchRoots) {
            $boardJson = Join-Path $root "$board.json"
            if (Test-Path $boardJson) {
                try {
                    $variant = (Get-Content -Raw -Path $boardJson | ConvertFrom-Json).build.variant
                }
                catch {
                    $variant = $null
                }
                if ($variant) { break }
            }
        }
        if (-not $variant) {
            continue
        }
        $header = Join-Path $variantsDir "$variant\pins_arduino.h"
        if (-not (Test-Path $header)) {
            $missing.Add($variant)
        }
    }

    return @($missing | Sort-Object -Unique)
}

function Confirm-ArduinoFrameworkVariants {
    # Integrity gate: if the isolated core's Arduino-ESP32 framework is missing the
    # board variant header this project needs (a truncated extraction PlatformIO
    # trusts because the .piopm marker looks complete), self-heal by reinstalling
    # the package so the failure is loud/self-correcting instead of a cryptic
    # "pins_arduino.h: No such file" mid-compile.
    param(
        [Parameter(Mandatory = $true)][string]$Target,
        [Parameter(Mandatory = $true)][string]$ProjectPath,
        [Parameter(Mandatory = $true)][string]$CoreDir
    )

    $missing = Get-MissingArduinoVariants -ProjectPath $ProjectPath -CoreDir $CoreDir
    if ($missing.Count -eq 0) {
        return
    }

    Write-Warning ("{0}: Arduino-ESP32 framework in '{1}' is missing variant header(s): {2}. Truncated package extraction; reinstalling." -f $Target, $CoreDir, ($missing -join ", "))

    $pio = Find-Command "pio"
    if (-not $pio) {
        Write-Error "${Target}: framework variants are missing but 'pio' was not found to repair them." -ErrorAction Continue
        $script:HadFailure = $true
        return
    }

    $frameworkDir = Join-Path $CoreDir "packages\framework-arduinoespressif32"
    Remove-Item -Recurse -Force $frameworkDir -ErrorAction SilentlyContinue
    & $pio.Source pkg install --project-dir $ProjectPath
    if ($LASTEXITCODE -ne 0) {
        Write-Error "${Target}: 'pio pkg install' failed while repairing the Arduino framework (exit $LASTEXITCODE)." -ErrorAction Continue
        $script:HadFailure = $true
        return
    }

    $stillMissing = Get-MissingArduinoVariants -ProjectPath $ProjectPath -CoreDir $CoreDir
    if ($stillMissing.Count -gt 0) {
        Write-Error ("{0}: Arduino framework variant header(s) still missing after reinstall: {1}." -f $Target, ($stillMissing -join ", ")) -ErrorAction Continue
        $script:HadFailure = $true
    }
    else {
        Write-Host "${Target}: Arduino framework reinstalled; variant header(s) now present."
    }
}
