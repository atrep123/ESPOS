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
import logging
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def _run_python(script: Path, *args: str) -> int:
    """Spustí Python skript v kořeni projektu a předá mu argumenty."""
    cmd = [sys.executable, str(script), *args]
    proc = subprocess.run(cmd, cwd=str(ROOT))
    return proc.returncode


def _run_shell(cmd: list[str]) -> int:
    proc = subprocess.run(cmd, cwd=str(ROOT))
    return proc.returncode


def action_ui_designer() -> None:
    logger.info("=== UI Designer ===")
    logger.info("1) Základní designer (ui_designer.py)")
    logger.info("2) UI Designer Pro (ui_designer_pro.py)")
    choice = input("Vyber (1/2, Enter=2): ").strip() or "2"

    script = ROOT / ("ui_designer.py" if choice == "1" else "ui_designer_pro.py")
    if not script.exists():
        logger.error("Skript %s nebyl nalezen.", script.name)
        return
    logger.info("Spouštím %s… (ukonči v jeho okně)", script.name)
    _run_python(script)


def action_simulator() -> None:
    logger.info("=== Simulátor (sim_run.py) ===")
    port = input("RPC port [8765]: ").strip() or "8765"
    width = input("Šířka znaků [100]: ").strip() or "100"
    height = input("Výška řádků [24]: ").strip() or "24"

    script = ROOT / "sim_run.py"
    if not script.exists():
        logger.error("sim_run.py nebyl nalezen.")
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
    logger.info("Spouštím simulátor na portu %s… (q = konec)", port)
    _run_python(script, *args)


def action_self_check() -> None:
    logger.info("=== Self-check (pytest) ===")
    logger.info("Spouštím tools/self_check.py …")
    script = ROOT / "tools" / "self_check.py"
    if not script.exists():
        logger.error("tools/self_check.py nebyl nalezen.")
        return
    code = _run_python(script)
    if code == 0:
        logger.info("Self-check OK.")
    else:
        logger.warning("Self-check našel problémy – viz výpis výše.")


def action_hw_bridge() -> None:
    logger.info("=== ESP32 Hardware Bridge ===")
    serial = input("Serial port (např. COM3 nebo /dev/ttyUSB0): ").strip()
    if not serial:
        logger.error("Serial port je povinný.")
        return
    port = input("RPC port simulátoru [8765]: ").strip() or "8765"

    script = ROOT / "esp32_hardware_bridge.py"
    if not script.exists():
        logger.error("esp32_hardware_bridge.py nebyl nalezen.")
        return

    args = [
        "--serial-port",
        serial,
        "--sim-port",
        port,
    ]
    logger.info("Spouštím HW bridge (%s → 127.0.0.1:%s)…", serial, port)
    _run_python(script, *args)


def main() -> int:
    while True:
        logger.info("================ ESP32OS Dev Hub ================")
        logger.info("1) Spustit UI Designer")
        logger.info("2) Spustit simulátor (sim_run.py)")
        logger.info("3) Self-check (pytest)")
        logger.info("4) ESP32 hardware bridge")
        logger.info("0) Konec")
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
            logger.info("Bye.")
            return 0
        else:
            logger.warning("Neplatná volba.")


if __name__ == "__main__":
    raise SystemExit(main())
