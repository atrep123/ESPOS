#!/usr/bin/env bash
set -euo pipefail

DESIGN="${1:-main_scene.json}"

python -m ruff check .
python -m pytest -q --ignore=output/buildprobe/tests

if [[ -f "tools/validate_design.py" ]]; then
  python tools/validate_design.py "${DESIGN}"
fi

if [[ -f "tools/check_demo_scene_strict.py" ]]; then
  python tools/check_demo_scene_strict.py
fi

pio test -e native
pio run -e arduino_nano_esp32-nohw
pio run -e esp32-s3-devkitm-1-nohw

echo "[OK] All checks completed."

