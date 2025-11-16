#!/usr/bin/env bash
set -euo pipefail
EXTRAS=${1:-"ui,web,hw,metrics,input,dev"}
echo "[setup] Creating .venv and installing extras: ${EXTRAS}";

# Create venv
python3 -m venv .venv
# shellcheck source=/dev/null
source .venv/bin/activate

python -m pip install --upgrade pip
if [[ -f pyproject.toml ]]; then
  python -m pip install ".[${EXTRAS}]"
elif [[ -f requirements.txt ]]; then
  python -m pip install -r requirements.txt
fi

if command -v pre-commit >/dev/null 2>&1; then
  pre-commit install || true
fi

echo "[setup] Done. Activate with: source .venv/bin/activate"
