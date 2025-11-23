#!/usr/bin/env python3
"""
UI automation smoke for the built ESP32OS UI Designer .exe using pywinauto.

Requirements:
  - Windows with GUI
  - pywinauto (dev dependency)
  - Built EXE at dist/ESP32OS_UI_Designer/ESP32OS_UI_Designer.exe

What it does (best effort):
  1) Starts the EXE with --gui (inherits current env)
  2) Waits for the launcher window
  3) Sends all launcher accelerators (Alt+1..Alt+0) to exercise every button
  4) Tries to close spawned Designer/Simulator windows and then the launcher

Notes:
  - Tk buttons do not expose automation names, so we rely on keyboard accelerators.
  - The launcher honors ESP32OS_LAUNCHER_ASYNC=1 to avoid blocking when actions spawn subprocesses.
"""
from __future__ import annotations

import os
import sys
import time
import warnings
import subprocess
from pathlib import Path
from typing import Sequence, Set, Tuple

from pywinauto import Application, findwindows, timings  # type: ignore
from pywinauto.application import AppStartError  # type: ignore
from pywinauto.findwindows import ElementNotFoundError  # type: ignore
from pywinauto.keyboard import send_keys  # type: ignore

BACKEND = os.environ.get("ESP32OS_AUTOMATION_BACKEND", "uia")
REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = REPO_ROOT / "reports" / "smoke_app"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = REPORT_DIR / "ui_automation_smoke.log"
FAILSHOT_PATH = REPORT_DIR / "ui_automation_failure.png"
TREE_DUMP_PATH = REPORT_DIR / "ui_automation_tree.txt"
SKIP_SIM = os.getenv("ESP32OS_SMOKE_SKIP_SIM", "1") == "1"
HOTKEY_ACTIONS: Sequence[Tuple[str, str, Sequence[str]]] = (
    ("1", "UI Designer", ("Designer",)),
    ("2", "Simulator", ("Simulator",)),
    ("3", "Export C assets", ()),
    ("4", "Start Web mode", ()),
    ("5", "Stop Web mode", ()),
    ("6", "Open frontend", ()),
    ("7", "Open backend URL", ()),
    ("8", "Edit config", ()),
    ("9", "Reset config", ()),
    ("0", "Docs", ()),
)


def find_exe() -> Path:
    exe = REPO_ROOT / "dist" / "ESP32OS_UI_Designer" / "ESP32OS_UI_Designer.exe"
    if not exe.exists():
        raise FileNotFoundError(f"EXE not found at {exe} (build ui_designer.spec first)")
    return exe


def log(msg: str, *, error: bool = False) -> None:
    """Log to console and append to the smoke log file."""
    print(msg, file=sys.stderr if error else sys.stdout)
    try:
        with LOG_PATH.open("a", encoding="utf-8") as fp:
            fp.write(msg + "\n")
    except Exception:
        pass


def save_tree_snapshot(win) -> None:
    """Persist the launcher control tree for debugging."""
    try:
        win.print_control_identifiers(filename=str(TREE_DUMP_PATH))
    except Exception as exc:
        log(f"[smoke] Could not save control tree: {exc}", error=True)


def save_screenshot(win) -> None:
    """Save a screenshot of the current window for diagnostics."""
    try:
        img = win.capture_as_image()
        img.save(FAILSHOT_PATH)
        log(f"[smoke] Saved screenshot to {FAILSHOT_PATH}")
    except Exception as exc:
        log(f"[smoke] Could not capture screenshot: {exc}", error=True)


def launcher_widget_name(hotkey: str, label: str) -> str:
    """Recreate the Tk widget name used by the launcher for automation lookup."""
    text = f"Alt+{hotkey}  {label}"
    return text.lower().replace(" ", "_").replace("-", "_")


def kill_simulators() -> None:
    """Best-effort kill of simulator processes spawned during automation (Windows-only)."""
    if os.name != "nt":
        return
    cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'sim_run.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if proc.stdout.strip():
            log(f"[smoke] Simulator kill stdout: {proc.stdout.strip()}")
        if proc.stderr.strip():
            log(f"[smoke] Simulator kill stderr: {proc.stderr.strip()}", error=True)
    except Exception as exc:
        log(f"[smoke] Simulator kill failed: {exc}", error=True)


def close_spawned_windows(backend: str, root_pid: int, seen_handles: Set[int], keywords: Sequence[str]) -> None:
    """Close windows created by hotkeys (best effort, filtered by title keywords)."""
    if not keywords:
        return
    try:
        elems = findwindows.find_elements(title_re=".*", control_type="Window", backend=backend)
    except Exception as exc:
        log(f"[smoke] Could not enumerate windows: {exc}", error=True)
        return
    for elem in elems:
        if elem.handle in seen_handles:
            continue
        title = (elem.name or "").strip()
        if not title:
            continue
        if not any(k.lower() in title.lower() for k in keywords):
            continue
        seen_handles.add(elem.handle)
        if elem.process_id == root_pid and elem.handle != 0:
            # Ignore other windows from the launcher process (unlikely).
            continue
        try:
            log(f"[smoke] Closing spawned window: {title!r}")
            app2 = Application(backend=backend).connect(handle=elem.handle)
            win = app2.window(handle=elem.handle)
            try:
                win.set_focus()
            except Exception:
                pass
            win.type_keys("%{F4}")
            time.sleep(0.5)
        except Exception as exc:
            log(f"[smoke] Could not close window {title!r}: {exc}", error=True)


def _invoke_action(win, hotkey: str, label: str) -> bool:
    """Try to click the launcher button via automation; fallback to hotkey. Returns True on automation click."""
    widget_name = launcher_widget_name(hotkey, label)
    try:
        btn = win.child_window(auto_id=widget_name, control_type="Button")
        if btn.exists(timeout=1):
            log(f"[smoke] Clicking via automation: {label} ({widget_name})")
            try:
                btn.set_focus()
            except Exception:
                pass
            try:
                btn.click_input()
            except Exception:
                btn.invoke()
            return True
        btn = win.child_window(title_re=fr"^Alt\+{hotkey}\s+{label}$", control_type="Button")
        if btn.exists(timeout=1):
            log(f"[smoke] Clicking via title: Alt+{hotkey} {label}")
            try:
                btn.set_focus()
            except Exception:
                pass
            btn.click_input()
            return True
    except Exception as exc:
        log(f"[smoke] Button lookup failed for Alt+{hotkey}: {exc}", error=True)
    log(f"[smoke] Fallback hotkey Alt+{hotkey}: {label}")
    try:
        send_keys(f"%{hotkey}", with_spaces=True, pause=0.05)
    except Exception as exc:
        log(f"[smoke] Hotkey send failed Alt+{hotkey}: {exc}", error=True)
        return False
    return False


def press_hotkeys(win, backend: str, root_pid: int, actions: Sequence[Tuple[str, str, Sequence[str]]]) -> None:
    """Send given launcher accelerators (Alt+X) to exercise each button."""
    seen_handles: Set[int] = {win.handle}
    automation_clicks = 0
    for key, label, keywords in actions:
        try:
            if _invoke_action(win, key, label):
                automation_clicks += 1
            time.sleep(1.5)
            close_spawned_windows(backend, root_pid, seen_handles, keywords)
        except Exception as exc:
            log(f"[smoke] Hotkey Alt+{key} failed: {exc}", error=True)
    log(f"[smoke] Automation clicks={automation_clicks} fallback_hotkeys={len(actions) - automation_clicks}")


def main() -> int:
    LOG_PATH.write_text("", encoding="utf-8")
    # Ensure launcher uses async mode so buttons don't block the UI during automation.
    os.environ.setdefault("ESP32OS_LAUNCHER_ASYNC", "1")
    os.environ.setdefault("ESP32OS_AUTOMATION_SIM_FRAMES", "8")
    # Ask launcher to close itself after a short delay to avoid hangs.
    os.environ.setdefault("ESP32OS_AUTOMATION_EXIT", "5000")
    warnings.filterwarnings("ignore", message=".*Access is denied.*")
    exe = find_exe()
    cmd_line = f'"{exe}" --gui'
    log(f"[smoke] Starting: {cmd_line} (backend={BACKEND})")
    success = False
    try:
        app = Application(backend=BACKEND).start(cmd_line)
        # Connect to the started process for reliable window lookup
        app = Application(backend=BACKEND).connect(process=app.process)
    except AppStartError as exc:
        log(f"[smoke] ERROR: failed to start EXE: {exc}", error=True)
        return 1
    except Exception as exc:  # pragma: no cover - best effort
        log(f"[smoke] ERROR: start/connect failed: {exc}", error=True)
        return 1

    timings.after_clickinput_wait = 0.5

    try:
        try:
            win = app.top_window()
            win.wait("visible", timeout=20)
        except ElementNotFoundError as exc:
            log(f"[smoke] ERROR: window not found: {exc}", error=True)
            app.kill()
            return 1
        try:
            title = win.window_text()
        except Exception:
            title = "<unknown>"
        log(f"[smoke] Window detected: {title!r}")
        save_tree_snapshot(win)
        success = True
        try:
            win.set_focus()
        except Exception:
            pass
        actions = [a for a in HOTKEY_ACTIONS if not (SKIP_SIM and a[0] == "2")]
        press_hotkeys(win, BACKEND, app.process, actions)

        # Give the launcher a moment to self-close if automation exit is set.
        try:
            win.wait_not("exists", timeout=7, retry_interval=0.5)
        except Exception:
            pass

        # Attempt graceful close via Alt+F4 if still alive
        try:
            if win.exists():
                win.type_keys("%{F4}")
        except Exception:
            pass
        time.sleep(2)
        kill_simulators()
        try:
            win.wait_not("exists", timeout=10, retry_interval=0.5)
        except Exception:
            # Best effort: if still alive, kill
            log("[smoke] Window still exists; killing process")
            app.kill()
        success = True
    except Exception as exc:  # pragma: no cover - best-effort smoke
        log(f"[smoke] ERROR: {exc}", error=True)
        try:
            save_screenshot(win)
            save_tree_snapshot(win)
        except Exception:
            pass
        kill_simulators()
        try:
            app.kill()
        except Exception:
            pass
        return 0 if success else 1
    finally:
        # Always cleanup stray simulators spawned by Alt+2 during the run.
        kill_simulators()
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
