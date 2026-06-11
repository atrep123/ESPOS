<#
.SYNOPSIS
    Compile and run the off-target (host) C++ unit tests for the M5 prop chain.

.DESCRIPTION
    Auto-discovers firmware/tests/test_*.cpp, compiles each with a host C++17
    compiler (g++), and runs them. Exits non-zero if any test binary fails, so
    it is safe to wire into CI or a pre-flash gate.

    These tests cover the pure, target-independent logic that is too important to
    leave unverified between flashes:
      * shared/core/safety_logic.h   -- ARM/STOP/TTL fire authority + replay window
      * shared/protocol/prop_protocol.h palette encode/decode (via test_palette)

    A compile-only mbedtls stub (firmware/tests/stubs/mbedtls/md.h) lets tests
    that include prop_protocol.h build without a real mbedtls; tests that never
    call frame crypto link cleanly.

.NOTES
    Requires g++ on PATH, or the WinLibs UCRT toolchain installed via winget
    (BrechtSanders.WinLibs.POSIX.UCRT). No PlatformIO / ESP toolchain needed.
#>
[CmdletBinding()]
param(
    [string]$Compiler,                       # explicit path to g++ (optional)
    [switch]$KeepBinaries                     # keep build/hosttests/*.exe after run
)

$ErrorActionPreference = 'Stop'

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$TestDir  = Join-Path $RepoRoot 'firmware/tests'
$StubDir  = Join-Path $RepoRoot 'firmware/tests/stubs'
$OutDir   = Join-Path $RepoRoot 'build/hosttests'

function Resolve-Compiler {
    param([string]$Explicit)
    if ($Explicit) {
        if (Test-Path $Explicit) { return $Explicit }
        throw "Specified compiler not found: $Explicit"
    }
    $onPath = Get-Command g++ -ErrorAction SilentlyContinue
    if ($onPath) { return $onPath.Source }
    # Fallback: WinLibs UCRT install location (winget BrechtSanders.WinLibs.POSIX.UCRT)
    $winlibs = Join-Path $env:LOCALAPPDATA `
        'Microsoft\WinGet\Packages\BrechtSanders.WinLibs.POSIX.UCRT_Microsoft.Winget.Source_8wekyb3d8bbwe\mingw64\bin\g++.exe'
    if (Test-Path $winlibs) { return $winlibs }
    throw "g++ not found on PATH or at the WinLibs location. Install with: winget install --id BrechtSanders.WinLibs.POSIX.UCRT"
}

$gxx = Resolve-Compiler -Explicit $Compiler
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$cflags = @('-std=c++17', '-Wall', '-Wextra', '-Werror', '-O2', '-I', $StubDir)

$tests = Get-ChildItem -Path $TestDir -Filter 'test_*.cpp' -File | Sort-Object Name
if (-not $tests) { throw "No test_*.cpp found in $TestDir" }

Write-Host "Host test runner" -ForegroundColor Cyan
Write-Host "  compiler: $gxx"
Write-Host "  tests:    $($tests.Count) file(s) in firmware/tests/"
Write-Host ""

$failed = @()
foreach ($t in $tests) {
    $name = [System.IO.Path]::GetFileNameWithoutExtension($t.Name)
    $exe  = Join-Path $OutDir ($name + '.exe')

    Write-Host "[$name] compiling..." -ForegroundColor DarkGray
    & $gxx @cflags $t.FullName -o $exe
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[$name] COMPILE FAILED" -ForegroundColor Red
        $failed += $name
        continue
    }

    Write-Host "[$name] running..." -ForegroundColor DarkGray
    & $exe
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[$name] TEST FAILED (exit $LASTEXITCODE)" -ForegroundColor Red
        $failed += $name
    } else {
        Write-Host "[$name] OK" -ForegroundColor Green
    }
    Write-Host ""

    if (-not $KeepBinaries) { Remove-Item $exe -Force -ErrorAction SilentlyContinue }
}

if ($failed.Count -gt 0) {
    Write-Host "HOST TESTS FAILED: $($failed -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "ALL HOST TESTS PASSED ($($tests.Count) file(s))" -ForegroundColor Green
exit 0
