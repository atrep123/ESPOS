#!/usr/bin/env python3
"""
ESP32OS self-check utility.

Provádí základní kontroly:
  - dostupnost klíčových Python balíků,
  - spuštění sim_run.py --help,
  - headless náhled přes ui_designer_preview.py,
  - rychlý pytest smoke test.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


ROOT = Path(__file__).resolve().parent.parent

# Ensure project root is on sys.path for imports like state_inspector.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str = ""


def check_imports() -> List[CheckResult]:
    """Zkontroluje přítomnost základních Python modulů."""
    modules = [
        ("Pillow (PIL)", "PIL"),
        ("watchdog", "watchdog"),
        ("websockets", "websockets"),
    ]
    results: List[CheckResult] = []
    for label, mod in modules:
        try:
            __import__(mod)
        except Exception as e:  # pragma: no cover - konkrétní text chyby není důležitý
            results.append(CheckResult(label, False, str(e)))
        else:
            results.append(CheckResult(label, True))
    return results


def check_sim_help() -> CheckResult:
    """Ověří, že sim_run.py jde spustit s --help."""
    script = ROOT / "sim_run.py"
    if not script.exists():
        return CheckResult("sim_run.py --help", False, "sim_run.py not found")
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "--help"],
            cwd=str(ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        ok = proc.returncode == 0
        return CheckResult("sim_run.py --help", ok, f"exit {proc.returncode}")
    except Exception as e:  # pragma: no cover - ochrana v produkci
        return CheckResult("sim_run.py --help", False, str(e))


def check_preview_headless() -> CheckResult:
    """Spustí ui_designer_preview.py v headless režimu na demo scéně."""
    script = ROOT / "ui_designer_preview.py"
    demo_json = ROOT / "examples" / "demo_scene.json"
    if not script.exists():
        return CheckResult("ui_designer_preview headless", False, "ui_designer_preview.py not found")
    if not demo_json.exists():
        return CheckResult("ui_designer_preview headless", False, "examples/demo_scene.json not found")
    with tempfile.TemporaryDirectory() as td:
        out_png = Path(td) / "preview.png"
        out_html = Path(td) / "preview.html"
        cmd = [
            sys.executable,
            str(script),
            "--headless-preview",
            "--in-json",
            str(demo_json),
            "--out-png",
            str(out_png),
            "--out-html",
            str(out_html),
        ]
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if proc.returncode != 0:
                return CheckResult("ui_designer_preview headless", False, f"exit {proc.returncode}")
            if not out_png.exists():
                return CheckResult("ui_designer_preview headless", False, "PNG not created")
            return CheckResult("ui_designer_preview headless", True)
        except Exception as e:  # pragma: no cover
            return CheckResult("ui_designer_preview headless", False, str(e))


def check_pytest_smoke() -> CheckResult:
    """Spustí rychlý pytest smoke test.

    Používá --capture=no kvůli známému problému s některými prostředími.
    """
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "--capture=no"],
            cwd=str(ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        ok = proc.returncode == 0
        return CheckResult("pytest -q", ok, f"exit {proc.returncode}")
    except Exception as e:  # pragma: no cover
        return CheckResult("pytest -q", False, str(e))


def _find_free_tcp_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def check_sim_rpc_get_state(timeout_sec: float = 5.0) -> CheckResult:
    """Spustí sim_run.py s RPC a ověří RPC get_state přes StateInspector."""
    from state_inspector import StateInspector  # type: ignore[import-not-found]
    import time

    script = ROOT / "sim_run.py"
    if not script.exists():
        return CheckResult("sim_run RPC get_state", False, "sim_run.py not found")

    port = _find_free_tcp_port()
    cmd = [
        sys.executable,
        str(script),
        "--rpc-port",
        str(port),
        "--fps",
        "30",
        "--width",
        "60",
        "--height",
        "16",
        "--no-color",
        "--no-unicode",
    ]
    proc: Optional[subprocess.Popen] = None
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Počkáme krátce, než simulátor naběhne
        start = time.time()
        connected = False
        insp = StateInspector(host="127.0.0.1", port=port)
        while time.time() - start < timeout_sec:
            try:
                if insp.connect():
                    connected = True
                    break
            except Exception:
                pass
            time.sleep(0.2)
        if not connected:
            return CheckResult("sim_run RPC get_state", False, "cannot connect to RPC")

        snap = insp.get_state()
        if not snap:
            return CheckResult("sim_run RPC get_state", False, "get_state returned no data")
        return CheckResult("sim_run RPC get_state", True)
    except Exception as e:  # pragma: no cover
        return CheckResult("sim_run RPC get_state", False, str(e))
    finally:
        if proc is not None:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass


def run_all_checks() -> List[CheckResult]:
    results: List[CheckResult] = []
    results.extend(check_imports())
    results.append(check_sim_help())
    results.append(check_preview_headless())
    results.append(check_pytest_smoke())
    return results


def main() -> int:
    print("=== ESP32OS Self-check ===")
    results = run_all_checks()
    # Přidej integrační kontrolu RPC get_state
    results.append(check_sim_rpc_get_state())
    all_ok = True
    for res in results:
        mark = "✅" if res.ok else "❌"
        extra = ""
        if res.detail and not res.ok:
            extra = f" ({res.detail})"
        print(f"{mark} {res.name}{extra}")
        if not res.ok:
            all_ok = False

    if all_ok:
        print("\nVše vypadá v pořádku.")
        return 0
    print("\nNěkteré kontroly selhaly – zkontroluj detaily výše.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
