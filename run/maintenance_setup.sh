#!/usr/bin/env bash
set -euo pipefail

# Maintenance setup script for warmed containers.
# - Reuses existing .venv if present
# - Updates Python dependencies
# - Ensures PlatformIO is available
# - Runs self-check to validate environment

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

echo "[maintenance] Root: ${ROOT}"

if [ -d ".venv" ]; then
  echo "[maintenance] Activating existing .venv"
  # shellcheck source=/dev/null
  source .venv/bin/activate
elif command -v python3 >/dev/null 2>&1; then
  echo "[maintenance] No .venv, creating one"
  python3 -m venv .venv
  # shellcheck source=/dev/null
  source .venv/bin/activate
else
  echo "[maintenance] ERROR: python3 not found in PATH." >&2
  exit 1
fi

echo "[maintenance] Upgrading pip"
python -m pip install --upgrade pip

if [ -f "pyproject.toml" ]; then
  echo "[maintenance] Re-installing project extras (ui,web,hw,metrics,input,dev)"
  python -m pip install ".[ui,web,hw,metrics,input,dev]"
elif [ -f "requirements.txt" ]; then
  echo "[maintenance] Re-installing requirements.txt"
  python -m pip install -r requirements.txt
  if [ -f "requirements-dev.txt" ]; then
    echo "[maintenance] Re-installing requirements-dev.txt"
    python -m pip install -r requirements-dev.txt
  fi
fi

if ! command -v pio >/dev/null 2>&1; then
  echo "[maintenance] Installing PlatformIO via pip"
  python -m pip install platformio || echo "[maintenance] Warning: PlatformIO install failed"
fi

echo "[maintenance] Running self-check (non-fatal)…"
if [ -f "tools/self_check.py" ]; then
  python tools/self_check.py || echo "[maintenance] Self-check reported issues (see log above)"
fi

echo "[maintenance] Done."

