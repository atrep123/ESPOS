#!/usr/bin/env pwsh
#Requires -Version 5.1

<#
.SYNOPSIS
    Global setup script for fresh Windows environments
.DESCRIPTION
    - Creates and activates a .venv
    - Installs project dependencies (including dev extras)
    - Optionally installs PlatformIO if missing
    - Runs a quick self-check (non-fatal on failure)
#>

$ErrorActionPreference = 'Stop'
$InformationPreference = 'Continue'

$ROOT = Split-Path -Parent $PSScriptRoot
Set-Location $ROOT

Write-Information "[setup] Root: $ROOT"

# Check Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "[setup] ERROR: python not found in PATH."
    exit 1
}

$pythonVersion = (python --version 2>&1)
Write-Information "[setup] Using: $pythonVersion"

# Create venv if missing
if (-not (Test-Path ".venv")) {
    Write-Information "[setup] Creating virtualenv .venv"
    python -m venv .venv
}

# Activate venv
$activateScript = ".venv\Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    Write-Information "[setup] Activating virtualenv"
    & $activateScript
} else {
    Write-Warning "[setup] Could not find $activateScript"
}

# Upgrade pip
Write-Information "[setup] Upgrading pip"
python -m pip install --upgrade pip --quiet

# Install dependencies
if (Test-Path "pyproject.toml") {
    Write-Information "[setup] Installing project with extras: ui,web,hw,metrics,input,dev"
    python -m pip install ".[ui,web,hw,metrics,input,dev]"
} elseif (Test-Path "requirements.txt") {
    Write-Information "[setup] Installing requirements.txt"
    python -m pip install -r requirements.txt
    if (Test-Path "requirements-dev.txt") {
        Write-Information "[setup] Installing requirements-dev.txt"
        python -m pip install -r requirements-dev.txt
    }
}

# PlatformIO (optional)
if (-not (Get-Command pio -ErrorAction SilentlyContinue)) {
    Write-Information "[setup] Installing PlatformIO via pip"
    try {
        python -m pip install platformio
    } catch {
        Write-Warning "[setup] PlatformIO install failed: $_"
    }
}

# Pre-commit hooks (optional)
if ((Get-Command pre-commit -ErrorAction SilentlyContinue) -and (Test-Path ".pre-commit-config.yaml")) {
    Write-Information "[setup] Installing pre-commit hooks"
    try {
        pre-commit install
    } catch {
        Write-Warning "[setup] pre-commit install failed: $_"
    }
}

# Self-check
Write-Information "[setup] Running self-check (non-fatal)..."
if (Test-Path "tools\self_check.py") {
    try {
        python tools\self_check.py
    } catch {
        Write-Warning "[setup] Self-check reported issues (see log above)"
    }
}

Write-Information "[setup] Done. Virtualenv is activated."
Write-Information "[setup] To activate manually: .\.venv\Scripts\Activate.ps1"
