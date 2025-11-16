#!/usr/bin/env python3
"""
Self-checker before export/flash.
- Checks Python extras (ui, web, hw, metrics) availability
- Detects multiple running simulator instances and port collisions (rpc/uart common ports)
- Verifies sim_ports.json consistency and optional ESP32 serial connectivity
- Prints actionable fixes
"""
import json
import os
import socket
import sys
from pathlib import Path

OK = "[ ok ]"
WARN = "[warn]"
ERR = "[fail]"

DEFAULT_PORTS = {"rpc": 5557, "uart": 5556}


def _check_import(name: str):
    try:
        __import__(name)
        print(f"{OK} python import: {name}")
        return True
    except Exception as e:
        print(f"{WARN} missing python import: {name} → pip install {name} ({e})")
        return False


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.25)
        try:
            s.bind(("127.0.0.1", port))
            return False
        except OSError:
            return True


def _has_multiple_sim_instances() -> bool:
    # Heuristic: presence of sim_ports.json with a different PID than current
    base = Path(__file__).resolve().parents[1]
    sp = base / 'sim_ports.json'
    if sp.exists():
        try:
            data = json.loads(sp.read_text())
            pid = int(data.get('pid') or 0)
            if pid and pid != os.getpid():
                print(f"{WARN} sim_ports.json exists for PID {pid}. Another simulator may be running.")
                return True
        except Exception:
            pass
    return False


def main():
    print("\n=== ESP32OS Self-Check ===")

    # Python package checks
    ui_ok = _check_import('PIL.Image')
    _check_import('serial')
    web_ok = _check_import('websockets')
    metrics_ok = _check_import('psutil')
    input_ok = _check_import('pygame')

    if input_ok:
        try:
            import pygame  # type: ignore
            ver = getattr(pygame, 'version', None)
            vstr = getattr(ver, 'ver', None) if ver else None
            if vstr:
                print(f"{OK} pygame version: {vstr}")
        except Exception:
            pass
        print(f"{OK} input features available: use --gamepad and/or --input-overlay in sim_run.py")
    else:
        print(f"{WARN} input extras missing: install with 'pip install pygame' or 'pip install -e .[input]'")

    # Port checks
    for name, port in DEFAULT_PORTS.items():
        if _port_in_use(port):
            print(f"{WARN} port {port} ({name}) is in use. Choose a different port or stop the process.")
        else:
            print(f"{OK} port {port} available")

    # Simulator instances
    _has_multiple_sim_instances()

    # ESP32 serial (optional)
    try:
        import serial.tools.list_ports as lp  # type: ignore
        ports = list(lp.comports())
        if ports:
            print(f"{OK} serial ports found: " + ', '.join(p.device for p in ports))
        else:
            print(f"{WARN} no serial ports found. If flashing, connect ESP32 and install drivers.")
    except Exception as e:
        print(f"{WARN} pyserial not available for port listing ({e}). Install with: pip install pyserial")

    # Summary and fixes
    print("\nSuggested fixes:")
    if not (ui_ok and web_ok and metrics_ok):
        print(" - Run tools/setup_env.ps1 (Windows) or tools/setup_env.sh (Unix) to install extras")
    print(" - If ports busy, run the simulator with --rpc-port/--uart-port to choose alternative ports")
    print(" - Close extra simulator instances; delete sim_ports.json if stale")

    # Windows-specific hint for PowerShell ExecutionPolicy
    if sys.platform == 'win32':
        print(" - If PowerShell blocks run_sim.ps1, start your session with:")
        print("   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass")
        print("   or run: powershell -ExecutionPolicy Bypass -File .\\run_sim.ps1 -AutoPorts")
        print("   alternatively, run Python directly: python sim_run.py --auto-size")

    print("\nDone.")


if __name__ == '__main__':
    sys.exit(main() or 0)
