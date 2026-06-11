"""Safe serial reader for the M5 bench: opens a COM port with DTR/RTS DEASSERTED so
the USB-CDC board is NOT reset on open (toggling DTR/RTS resets the ESP32-S3/C6).

Usage:  python tools/read_com.py COM7 [seconds] [baud]
Never open a second monitor on a port that's already being read during a bench run.
"""
import sys
import time

import serial


def read_port(port, baud=115200, seconds=4.0):
    s = serial.Serial()
    s.port = port
    s.baudrate = baud
    s.dtr = False   # CRITICAL: do not assert DTR -> no reset of the board on open
    s.rts = False
    s.timeout = 0.2
    s.open()
    lines = []
    end = time.monotonic() + float(seconds)
    while time.monotonic() < end:
        raw = s.readline()
        if raw:
            lines.append(raw.decode("utf-8", errors="replace").rstrip("\r\n"))
    s.close()
    return lines


def main():
    if len(sys.argv) < 2:
        print("usage: read_com.py COM<n> [seconds] [baud]")
        return 2
    port = sys.argv[1]
    seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 4.0
    baud = int(sys.argv[3]) if len(sys.argv) > 3 else 115200
    got = read_port(port, baud, seconds)
    if not got:
        print(f"[{port}] (no output in {seconds}s)")
    for line in got:
        print(f"[{port}] {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
