#!/usr/bin/env bash
set -euo pipefail

# Global setup script for fresh containers / clones.
# - Creates and activates a .venv
# - Installs project dependencies (including dev extras)
# - Optionally installs PlatformIO if missing
# - Runs a quick self-check (non-fatal on failure)

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

echo "[setup] Root: ${ROOT}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[setup] ERROR: python3 not found in PATH." >&2
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "[setup] Creating virtualenv .venv"
  python3 -m venv .venv
fi

# Activate venv (handle both Unix and Windows/Git Bash paths)
if [ -f ".venv/bin/activate" ]; then
  # shellcheck source=/dev/null
  source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
  # Windows Git Bash
  # shellcheck source=/dev/null
  source .venv/Scripts/activate
else
  echo "[setup] Warning: Could not find venv activation script"
fi

echo "[setup] Upgrading pip"
python -m pip install --upgrade pip

if [ -f "pyproject.toml" ]; then
  # Install with recommended extras for full functionality
  echo "[setup] Installing project with extras: ui,web,hw,metrics,input,dev"
  python -m pip install ".[ui,web,hw,metrics,input,dev]"
elif [ -f "requirements.txt" ]; then
  echo "[setup] Installing requirements.txt"
  python -m pip install -r requirements.txt
  if [ -f "requirements-dev.txt" ]; then
    echo "[setup] Installing requirements-dev.txt"
    python -m pip install -r requirements-dev.txt
  fi
fi

if ! command -v pio >/dev/null 2>&1; then
  echo "[setup] Installing PlatformIO via pip"
  python -m pip install platformio || echo "[setup] Warning: PlatformIO install failed"
fi

if command -v pre-commit >/dev/null 2>&1 && [ -f ".pre-commit-config.yaml" ]; then
  echo "[setup] Installing pre-commit hooks"
  pre-commit install || echo "[setup] Warning: pre-commit install failed"
fi

echo "[setup] Running self-check (non-fatal)…"
if [ -f "tools/self_check.py" ]; then
  python tools/self_check.py || echo "[setup] Self-check reported issues (see log above)"
fi

echo "[setup] Done. Activate env with: source .venv/bin/activate"

