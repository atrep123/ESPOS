#!/usr/bin/env python3
import sys
from typing import List

try:
    from serial.tools import list_ports
except Exception:  # pragma: no cover
    list_ports = None

ESPRESSIF_VID = 0x303A
ESP32S3_PIDS: List[int] = [0x1001, 0x1002, 0x1004]  # common S3 JTAG/USB serial PIDs


def has_esp32s3() -> bool:
    if list_ports is None:
        return False
    devices = list(list_ports.comports())
    for dev in devices:
        try:
            if dev.vid == ESPRESSIF_VID and (dev.pid in ESP32S3_PIDS or dev.pid is not None):
                return True
            desc = (dev.description or "").lower()
            if "esp32-s3" in desc or "espressif" in desc or "usb jtag" in desc:
                return True
        except Exception:
            continue
    return False


def main() -> int:
    # We intentionally always "succeed" but explain what happened.
    want = sys.argv[1] if len(sys.argv) > 1 else "test"
    board_present = has_esp32s3()

    if not board_present:
        print(
            f"INFO: No ESP32-S3 board detected. Skipping '{want}' stage.\n"
            "To run hardware tests, connect your board and use:\n"
            "  pio test -e esp32-s3-devkitm-1"
        )
        return 0

    # Board is present: suggest using the real HW env for full test execution.
    print(
        f"INFO: ESP32-S3 board detected, but this '-nohw' environment auto-skips "
        f"'{want}' stage to avoid conflicts. For full hardware test execution, use:\n"
        "  pio test -e esp32-s3-devkitm-1"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
