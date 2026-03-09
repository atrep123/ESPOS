#!/usr/bin/env bash
set -euo pipefail

DESIGN="${1:-main_scene.json}"
ALLOW_NATIVE_POLICY_BLOCK="${ALLOW_NATIVE_POLICY_BLOCK:-0}"

PYTHON_CMD=""
if command -v python >/dev/null 2>&1; then
  PYTHON_CMD="python"
elif command -v python.exe >/dev/null 2>&1; then
  PYTHON_CMD="python.exe"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="python3"
else
  echo "[FAIL] No python interpreter found in PATH (python/python3/python.exe)." >&2
  exit 127
fi

PIO_CMD=""
if command -v pio >/dev/null 2>&1; then
  PIO_CMD="pio"
elif command -v pio.exe >/dev/null 2>&1; then
  PIO_CMD="pio.exe"
else
  echo "[FAIL] No PlatformIO CLI found in PATH (pio/pio.exe)." >&2
  exit 127
fi

run_pio_native_with_retry() {
  local max_attempts="${1:-4}"
  local delay_seconds="${2:-2}"
  local attempt=1

  while [[ "$attempt" -le "$max_attempts" ]]; do
    echo
    echo "== pio native tests (attempt ${attempt}/${max_attempts}) =="

    local log_file
    log_file="$(mktemp -t esp32os_native_retry.XXXXXX.log)"
    if "$PIO_CMD" test -e native 2>&1 | tee "$log_file"; then
      rm -f "$log_file"
      return 0
    fi

    if grep -Eiq "WinError[[:space:]]*4551|application control policy|policy blocked this file" "$log_file"; then
      if [[ "$attempt" -ge "$max_attempts" ]]; then
        if [[ "$ALLOW_NATIVE_POLICY_BLOCK" == "1" ]]; then
          echo "[WARN] pio native tests hit repeated WinError 4551 policy blocking after ${max_attempts} attempts; continuing due to ALLOW_NATIVE_POLICY_BLOCK=1" >&2
          rm -f "$log_file"
          return 0
        fi
        echo "[FAIL] pio native tests failed after ${max_attempts} attempts due to repeated WinError 4551 policy blocking" >&2
        rm -f "$log_file"
        return 1
      fi
      echo "[WARN] Detected intermittent WinError 4551 policy block. Retrying in ${delay_seconds}s..." >&2
      rm -f "$log_file"
      sleep "$delay_seconds"
      attempt=$((attempt + 1))
      continue
    fi

    echo "[FAIL] pio native tests failed for a non-policy reason." >&2
    rm -f "$log_file"
    return 1
  done
}

"$PYTHON_CMD" -m ruff check .
"$PYTHON_CMD" -m pytest -q --ignore=output/buildprobe/tests

if [[ -f "tools/validate_design.py" ]]; then
  "$PYTHON_CMD" tools/validate_design.py "${DESIGN}"
fi

if [[ -f "tools/check_demo_scene_strict.py" ]]; then
  "$PYTHON_CMD" tools/check_demo_scene_strict.py
fi

run_pio_native_with_retry 4 2
"$PIO_CMD" run -e arduino_nano_esp32-nohw
"$PIO_CMD" run -e esp32-s3-devkitm-1-nohw

echo "[OK] All checks completed."

