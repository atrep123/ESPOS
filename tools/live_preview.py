#!/usr/bin/env python3
"""
Push a design JSON to an ESP32 over serial for live preview.

Protocol: sends framed JSON as `<<UIJSON>>...<<END>>`. Device firmware must
listen on the given port/baud and handle the JSON payload.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure repository root is on sys.path so we can import run_designer
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from run_designer import send_live_preview  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Send design JSON to ESP32 for live preview")
    parser.add_argument("json", type=Path, help="Design JSON to send")
    parser.add_argument("--port", required=True, help="Serial port (e.g. COM3, /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=115200, help="Baudrate (default 115200)")
    args = parser.parse_args()

    if not args.json.exists():
        raise SystemExit(f"JSON not found: {args.json}")
    send_live_preview(args.json, args.port, args.baud)


if __name__ == "__main__":
    main()
