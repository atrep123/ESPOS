# ESP32 UI Simulator Build Script for Windows
# This script compiles and runs the UI simulator using MSVC or MinGW

Write-Host "`n=== ESP32 UI Simulator Build ===" -ForegroundColor Cyan
Write-Host "Looking for C compiler...`n" -ForegroundColor Gray

# Try to find a C compiler
$compiler = $null
$compilerName = ""

# Check for cl.exe (MSVC)
if (Get-Command cl.exe -ErrorAction SilentlyContinue) {
    $compiler = "cl.exe"
    $compilerName = "MSVC"
    Write-Host "✓ Found: Microsoft Visual C++ Compiler" -ForegroundColor Green
}
# Check for gcc (MinGW)
elseif (Get-Command gcc.exe -ErrorAction SilentlyContinue) {
    $compiler = "gcc.exe"
    $compilerName = "GCC"
    Write-Host "✓ Found: GCC (MinGW)" -ForegroundColor Green
}
# Check for clang
elseif (Get-Command clang.exe -ErrorAction SilentlyContinue) {
    $compiler = "clang.exe"
    $compilerName = "Clang"
    Write-Host "✓ Found: Clang" -ForegroundColor Green
}
else {
    Write-Host "✗ No C compiler found!" -ForegroundColor Red
    Write-Host "`nPlease install one of the following:" -ForegroundColor Yellow
    Write-Host "  1. Visual Studio Build Tools (MSVC)" -ForegroundColor Gray
    Write-Host "  2. MinGW-w64 (GCC)" -ForegroundColor Gray
    Write-Host "  3. LLVM (Clang)" -ForegroundColor Gray
    Write-Host "`nOr use WSL for Linux environment.`n" -ForegroundColor Gray
    exit 1
}

# Create build directory
$buildDir = "build_sim"
if (-not (Test-Path $buildDir)) {
    New-Item -ItemType Directory -Path $buildDir | Out-Null
}

$sourceFiles = @("sim\main.c", "src\services\ui\ui_core.c")
$outputExe = "$buildDir\ui_simulator.exe"

Write-Host "`nCompiling $sourceFile with $compilerName..." -ForegroundColor Cyan

# Compile based on compiler type
$success = $false

if ($compilerName -eq "MSVC") {
    # MSVC compilation
    & cl.exe /nologo /W3 /O2 /D_WIN32 /I src /Fe:$outputExe $sourceFiles
    $success = $LASTEXITCODE -eq 0
}
elseif ($compilerName -eq "GCC") {
    # GCC compilation
    & gcc.exe -std=c11 -O2 -Wall -D_WIN32 -Isrc -o $outputExe $sourceFiles
    $success = $LASTEXITCODE -eq 0
}
elseif ($compilerName -eq "Clang") {
    # Clang compilation
    & clang.exe -std=c11 -O2 -Wall -D_WIN32 -Isrc -o $outputExe $sourceFiles
    $success = $LASTEXITCODE -eq 0
}

if ($success) {
    Write-Host "`n✓ Compilation successful!" -ForegroundColor Green
    Write-Host "`n=== Running UI Simulator ===" -ForegroundColor Cyan
    Write-Host "Press Q to quit, or use other keys for interaction`n" -ForegroundColor Gray
    
    # Run the simulator
    & $outputExe
    
    Write-Host "`n=== Simulator Finished ===" -ForegroundColor Cyan
} else {
    Write-Host "`n✗ Compilation failed!" -ForegroundColor Red
    exit 1
}
