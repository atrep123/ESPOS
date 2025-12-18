#!/usr/bin/env bash
set -euo pipefail

DESIGN="${1:-main_scene.json}"

python -m ruff check .
python -m pytest -q

if [[ -f "tools/validate_design.py" ]]; then
  python tools/validate_design.py "${DESIGN}"
fi

pio test -e native
pio run -e arduino_nano_esp32-nohw
pio run -e esp32-s3-devkitm-1-nohw

echo "[OK] All checks completed."

