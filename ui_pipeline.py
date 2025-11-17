#!/usr/bin/env python3
"""
UI Pipeline helper for ESP32OS.

Purpose:
- Connect UI Designer JSON exports to C firmware and PlatformIO builds.
- Provide simple CLI commands for:
  * exporting C layout from a JSON design,
  * building firmware via PlatformIO,
  * flashing firmware to an ESP32 board,
  * running the full export → build → flash pipeline,
  * watching a design file and auto-rebuilding on changes.

This script is intentionally minimal and uses existing helpers:
- UIDesigner / load_from_json from ui_designer.py
- C export from ui_export_c.py

It does not change any existing firmware APIs; it only orchestrates tools.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Optional

from ui_designer import UIDesigner
from ui_export_c import export_c

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    WATCHDOG_AVAILABLE = True
except Exception:
    WATCHDOG_AVAILABLE = False


ROOT = Path(__file__).resolve().parent


def _run_subprocess(cmd: list[str], *, cwd: Optional[Path] = None) -> int:
    """Run a subprocess and stream its output."""
    print(f"[ui-pipeline] Running: {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=str(cwd or ROOT))
    if proc.returncode != 0:
        print(f"[ui-pipeline] Command failed with code {proc.returncode}")
    return proc.returncode


def _find_pio_command() -> list[str]:
    """
    Return the base command used to invoke PlatformIO.

    We try 'pio' first (common alias), then 'platformio'.
    The chosen form is cached via a simple global attribute on the function.
    """
    if hasattr(_find_pio_command, "_cached"):
        return getattr(_find_pio_command, "_cached")  # type: ignore[no-any-return]

    candidates = ["pio", "platformio"]
    for name in candidates:
        try:
            result = subprocess.run(
                [name, "--version"],
                cwd=str(ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if result.returncode == 0:
                setattr(_find_pio_command, "_cached", [name])
                return [name]
        except FileNotFoundError:
            continue

    # Fallback – the actual command will likely fail, but we keep the message clear.
    print(
        "[ui-pipeline] Warning: PlatformIO command not found. "
        "Install PlatformIO CLI or adjust PATH."
    )
    setattr(_find_pio_command, "_cached", ["pio"])
    return ["pio"]


def cmd_export_c(args: argparse.Namespace) -> int:
    """Export C layout from a JSON design using UIDesigner + ui_export_c."""
    design_path = Path(args.design).expanduser().resolve()
    if not design_path.is_file():
        print(f"[ui-pipeline] Design JSON not found: {design_path}")
        return 1

    designer = UIDesigner()
    designer.load_from_json(str(design_path))

    if args.scene:
        if args.scene not in designer.scenes:
            print(
                f"[ui-pipeline] Scene '{args.scene}' not found in design. "
                f"Available: {', '.join(designer.scenes.keys())}"
            )
            return 1
        designer.current_scene = args.scene

    if not designer.current_scene:
        print("[ui-pipeline] No active scene to export.")
        return 1

    icon_px = getattr(args, "icon_size", 16)
    try:
        export_c(designer, base_name=args.base_name, icon_size=icon_px)
    except Exception as exc:
        print(f"[ui-pipeline] C export failed: {exc}")
        return 1

    print(
        f"[ui-pipeline] C export OK. "
        f"Generated src/{args.base_name}.h and src/{args.base_name}.c"
    )
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    """Build firmware for the selected PlatformIO environment."""
    env = args.env
    base_cmd = _find_pio_command()
    cmd = [*base_cmd, "run", "-e", env]
    return _run_subprocess(cmd, cwd=ROOT)


def cmd_flash(args: argparse.Namespace) -> int:
    """Flash firmware to ESP32 using PlatformIO."""
    env = args.env
    port = args.port
    if not port:
        print("[ui-pipeline] Flashing requires --port (e.g. COM3 or /dev/ttyUSB0).")
        return 1

    base_cmd = _find_pio_command()
    cmd = [*base_cmd, "run", "-e", env, "-t", "upload", "--upload-port", port]
    return _run_subprocess(cmd, cwd=ROOT)


def cmd_run_all(args: argparse.Namespace) -> int:
    """Run export-c → build → flash as a single pipeline."""
    if cmd_export_c(args) != 0:
        print("[ui-pipeline] Aborting pipeline due to export failure.")
        return 1
    if cmd_build(args) != 0:
        print("[ui-pipeline] Aborting pipeline due to build failure.")
        return 1
    if args.port:
        if cmd_flash(args) != 0:
            print("[ui-pipeline] Flash step failed.")
            return 1
    else:
        print("[ui-pipeline] Skipping flash (no --port specified).")
    return 0


class _DesignChangeHandler(FileSystemEventHandler):  # type: ignore[misc]
    """Watchdog handler that triggers pipeline runs on design changes."""

    def __init__(self, design_path: Path, on_change: Callable[[], None], debounce_s: float = 0.5) -> None:
        super().__init__()
        self.design_path = design_path
        self.on_change = on_change
        self.debounce_s = debounce_s
        self._last_ts: float = 0.0
        self._running = False

    def _maybe_trigger(self) -> None:
        now = time.time()
        if now - self._last_ts < self.debounce_s:
            return
        self._last_ts = now
        if self._running:
            print("[ui-pipeline] Change detected but pipeline is already running; skipping.")
            return
        self._running = True
        try:
            self.on_change()
        finally:
            self._running = False

    def on_modified(self, event):  # type: ignore[override]
        try:
            path = Path(getattr(event, "src_path", ""))
        except Exception:
            return
        if path.resolve() == self.design_path:
            print(f"[ui-pipeline] Change detected in {self.design_path.name}")
            self._maybe_trigger()

    def on_created(self, event):  # type: ignore[override]
        self.on_modified(event)

    def on_moved(self, event):  # type: ignore[override]
        self.on_modified(event)


def cmd_watch(args: argparse.Namespace) -> int:
    """Watch a design file and run export → build → (optional) flash on changes."""
    if not WATCHDOG_AVAILABLE:
        print(
            "[ui-pipeline] The 'watch' command requires watchdog. "
            "Install it via 'pip install watchdog' or requirements.txt."
        )
        return 1

    design_path = Path(args.design).expanduser().resolve()
    if not design_path.is_file():
        print(f"[ui-pipeline] Design JSON not found: {design_path}")
        return 1

    def _run_pipeline() -> None:
        print("[ui-pipeline] === Auto pipeline start ===")
        result = cmd_export_c(args)
        if result != 0:
            print("[ui-pipeline] Export failed; skipping build/flash.")
            return
        result = cmd_build(args)
        if result != 0:
            print("[ui-pipeline] Build failed; skipping flash.")
            return
        if args.port:
            cmd_flash(args)
        print("[ui-pipeline] === Auto pipeline done ===")

    observer = Observer()
    handler = _DesignChangeHandler(design_path, _run_pipeline, debounce_s=args.debounce)
    observer.schedule(handler, str(design_path.parent), recursive=False)

    print(f"[ui-pipeline] Watching {design_path} for changes (Ctrl+C to stop)…")
    observer.start()
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[ui-pipeline] Stopping watcher…")
        observer.stop()
    observer.join()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ESP32OS UI → C → firmware pipeline helper"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # export-c
    p_export = subparsers.add_parser(
        "export-c", help="Export C layout from a JSON design using UIDesigner"
    )
    p_export.add_argument(
        "--design",
        required=True,
        help="Path to UI Designer JSON file (save from ui_designer/ui_designer_pro)",
    )
    p_export.add_argument(
        "--scene",
        help="Scene name to export (default: current/first scene in design)",
    )
    p_export.add_argument(
        "--base-name",
        default="ui_design",
        help="Base name for generated C files in src/ (default: ui_design)",
    )
    p_export.add_argument(
        "--icon-size",
        type=int,
        default=16,
        help="Icon size in px for C export (default: 16)",
    )
    p_export.set_defaults(func=cmd_export_c)

    # build
    p_build = subparsers.add_parser(
        "build", help="Build firmware using PlatformIO (pio run)"
    )
    p_build.add_argument(
        "--env",
        default="esp32-s3-devkitm-1",
        help="PlatformIO environment name (default: esp32-s3-devkitm-1)",
    )
    p_build.set_defaults(func=cmd_build)

    # flash
    p_flash = subparsers.add_parser(
        "flash", help="Flash firmware to ESP32 using PlatformIO upload"
    )
    p_flash.add_argument(
        "--env",
        default="esp32-s3-devkitm-1",
        help="PlatformIO environment name (default: esp32-s3-devkitm-1)",
    )
    p_flash.add_argument(
        "--port",
        required=True,
        help="Serial port for upload (e.g. COM3 or /dev/ttyUSB0)",
    )
    p_flash.set_defaults(func=cmd_flash)

    # run-all
    p_all = subparsers.add_parser(
        "run-all",
        help="Run export-c → build → flash as a single pipeline",
    )
    p_all.add_argument(
        "--design",
        required=True,
        help="Path to UI Designer JSON file",
    )
    p_all.add_argument(
        "--scene",
        help="Scene name to export (default: current/first scene in design)",
    )
    p_all.add_argument(
        "--base-name",
        default="ui_design",
        help="Base name for generated C files in src/ (default: ui_design)",
    )
    p_all.add_argument(
        "--icon-size",
        type=int,
        default=16,
        help="Icon size in px for C export (default: 16)",
    )
    p_all.add_argument(
        "--env",
        default="esp32-s3-devkitm-1",
        help="PlatformIO environment name (default: esp32-s3-devkitm-1)",
    )
    p_all.add_argument(
        "--port",
        help="Serial port for upload (if omitted, flash step is skipped)",
    )
    p_all.set_defaults(func=cmd_run_all)

    # watch
    p_watch = subparsers.add_parser(
        "watch",
        help="Watch a design JSON file and auto-run export → build → (optional) flash",
    )
    p_watch.add_argument(
        "--design",
        required=True,
        help="Path to UI Designer JSON file",
    )
    p_watch.add_argument(
        "--scene",
        help="Scene name to export (default: current/first scene in design)",
    )
    p_watch.add_argument(
        "--base-name",
        default="ui_design",
        help="Base name for generated C files in src/ (default: ui_design)",
    )
    p_watch.add_argument(
        "--icon-size",
        type=int,
        default=16,
        help="Icon size in px for C export (default: 16)",
    )
    p_watch.add_argument(
        "--env",
        default="esp32-s3-devkitm-1",
        help="PlatformIO environment name (default: esp32-s3-devkitm-1)",
    )
    p_watch.add_argument(
        "--port",
        help="Serial port for upload (if omitted, only export+build is run)",
    )
    p_watch.add_argument(
        "--debounce",
        type=float,
        default=0.5,
        help="Debounce window in seconds before rerunning pipeline (default: 0.5)",
    )
    p_watch.set_defaults(func=cmd_watch)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if not func:
        parser.print_help()
        return 1
    return int(func(args))


if __name__ == "__main__":
    raise SystemExit(main())
