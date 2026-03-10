#!/usr/bin/env python3
import os
import sys
from typing import List

try:
    from serial.tools import list_ports
except Exception:  # pragma: no cover
    list_ports = None

ESPRESSIF_VID = 0x303A
ESP32S3_PIDS: List[int] = [0x1001, 0x1002, 0x1004]  # common S3 JTAG/USB serial PIDs
ARDUINO_VID = 0x2341
ARDUINO_NANO_ESP32_PIDS: List[int] = [0x0070]
ALLOWED_STAGES = {"test", "upload"}


def has_esp32s3() -> bool:
    if list_ports is None:
        return False
    devices = list(list_ports.comports())
    for dev in devices:
        try:
            if dev.vid == ESPRESSIF_VID and dev.pid in ESP32S3_PIDS:
                return True
            if dev.vid == ARDUINO_VID and dev.pid in ARDUINO_NANO_ESP32_PIDS:
                return True
            desc = (dev.description or "").lower()
            if (
                "esp32-s3" in desc
                or "espressif" in desc
                or "usb jtag" in desc
                or "arduino nano esp32" in desc
                or "nora" in desc
            ):
                return True
        except Exception:
            continue
    return False


def main() -> int:
    # We intentionally always "succeed" but explain what happened.
    if len(sys.argv) > 2:
        print(f"ERROR: Unexpected arguments: {' '.join(sys.argv[2:])}", file=sys.stderr)
        return 2

    want = sys.argv[1] if len(sys.argv) > 1 else "test"
    normalized_want = want.strip().lower()
    if not normalized_want:
        print("ERROR: Stage argument cannot be empty", file=sys.stderr)
        return 2
    if normalized_want not in ALLOWED_STAGES:
        allowed = ", ".join(sorted(ALLOWED_STAGES))
        print(f"ERROR: Unsupported stage '{want}'. Allowed: {allowed}", file=sys.stderr)
        return 2
    want = normalized_want

    board_present = has_esp32s3()
    env = (os.getenv("PIOENV") or "").strip()
    hw_env = env[:-5] if env.endswith("-nohw") else env
    if not hw_env:
        hw_env = "esp32-s3-devkitm-1"
    suggested_cmd = (
        f"pio run -t upload -e {hw_env}"
        if want == "upload"
        else f"pio test -e {hw_env}"
    )

    if not board_present:
        print(
            f"INFO: No compatible board detected. Skipping '{want}' stage.\n"
            "To run hardware tests, connect your board and use:\n"
            f"  {suggested_cmd}"
        )
        return 0

    # Board is present: suggest using the real HW env for full test execution.
    print(
        f"INFO: Board detected, but this '-nohw' environment auto-skips "
        f"'{want}' stage to avoid conflicts. For full hardware test execution, use:\n"
        f"  {suggested_cmd}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
