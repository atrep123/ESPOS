#!/usr/bin/env python3
"""
ESP32OS Dev Hub - jednoduché "command center" pro běžné úkony.

Funkce:
  1) Spustit UI Designer (základní / Pro)
  2) Spustit simulátor (sim_run.py) s rozumnými defaulty
  3) Spustit rychlý self-check (pytest)
  4) Spustit ESP32 hardware bridge
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def _run_python(script: Path, *args: str) -> int:
    """Spustí Python skript v kořeni projektu a předá mu argumenty."""
    cmd = [sys.executable, str(script), *args]
    proc = subprocess.run(cmd, cwd=str(ROOT))
    return proc.returncode


def _run_shell(cmd: list[str]) -> int:
    proc = subprocess.run(cmd, cwd=str(ROOT))
    return proc.returncode


def action_ui_designer() -> None:
    print("\n=== UI Designer ===")
    print("1) Základní designer (ui_designer.py)")
    print("2) UI Designer Pro (ui_designer_pro.py)")
    choice = input("Vyber (1/2, Enter=2): ").strip() or "2"

    script = ROOT / ("ui_designer.py" if choice == "1" else "ui_designer_pro.py")
    if not script.exists():
        print(f"❌ Skript {script.name} nebyl nalezen.")
        return
    print(f"▶ Spouštím {script.name}… (ukonči v jeho okně)")
    _run_python(script)


def action_simulator() -> None:
    print("\n=== Simulátor (sim_run.py) ===")
    port = input("RPC port [8765]: ").strip() or "8765"
    width = input("Šířka znaků [100]: ").strip() or "100"
    height = input("Výška řádků [24]: ").strip() or "24"

    script = ROOT / "sim_run.py"
    if not script.exists():
        print("❌ sim_run.py nebyl nalezen.")
        return

    args = [
        "--rpc-port",
        port,
        "--width",
        width,
        "--height",
        height,
        "--auto-size",
    ]
    print(f"▶ Spouštím simulátor na portu {port}… (q = konec)")
    _run_python(script, *args)


def action_self_check() -> None:
    print("\n=== Self-check (pytest) ===")
    print("▶ Spouštím tools/self_check.py …")
    script = ROOT / "tools" / "self_check.py"
    if not script.exists():
        print("❌ tools/self_check.py nebyl nalezen.")
        return
    code = _run_python(script)
    if code == 0:
        print("✅ Self-check OK.")
    else:
        print("⚠ Self-check našel problémy – viz výpis výše.")


def action_hw_bridge() -> None:
    print("\n=== ESP32 Hardware Bridge ===")
    serial = input("Serial port (např. COM3 nebo /dev/ttyUSB0): ").strip()
    if not serial:
        print("❌ Serial port je povinný.")
        return
    port = input("RPC port simulátoru [8765]: ").strip() or "8765"

    script = ROOT / "esp32_hardware_bridge.py"
    if not script.exists():
        print("❌ esp32_hardware_bridge.py nebyl nalezen.")
        return

    args = [
        "--serial-port",
        serial,
        "--sim-port",
        port,
    ]
    print(f"▶ Spouštím HW bridge ({serial} → 127.0.0.1:{port})…")
    _run_python(script, *args)


def main() -> int:
    while True:
        print("\n================ ESP32OS Dev Hub ================")
        print("1) Spustit UI Designer")
        print("2) Spustit simulátor (sim_run.py)")
        print("3) Self-check (pytest)")
        print("4) ESP32 hardware bridge")
        print("0) Konec")
        choice = input("Volba: ").strip()

        if choice == "1":
            action_ui_designer()
        elif choice == "2":
            action_simulator()
        elif choice == "3":
            action_self_check()
        elif choice == "4":
            action_hw_bridge()
        elif choice == "0":
            print("Bye.")
            return 0
        else:
            print("Neplatná volba.")


if __name__ == "__main__":
    raise SystemExit(main())
