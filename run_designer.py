#!/usr/bin/env python3
"""
Pygame entrypoint for the ESP32 OS UI Designer.

Replaces the missing Tk launcher with the Pygame-based CyberpunkEditorApp so
`launcher.py` and docs can point to a single, working command.
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import Optional

from ui_designer import HARDWARE_PROFILES, UIDesigner

# Main application design file (single source of truth, no demo scenes)
DEFAULT_JSON = Path("main_scene.json")


def _require_pygame() -> None:
    """Fail fast with a helpful hint when pygame is absent."""
    try:
        import pygame  # type: ignore  # noqa: F401
    except ImportError:
        print("[FAIL] Missing dependency: pygame")
        print("       Install with: pip install pygame")
        raise SystemExit(1) from None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pygame UI Designer launcher")
    parser.add_argument(
        "json",
        nargs="?",
        default=DEFAULT_JSON,
        help="Design JSON path (created if missing)",
    )
    parser.add_argument("--width", type=int, default=320, help="Canvas width (new files)")
    parser.add_argument("--height", type=int, default=240, help="Canvas height (new files)")
    parser.add_argument(
        "--headless-export",
        action="store_true",
        help="Create/update the JSON without opening the Pygame window",
    )
    parser.add_argument(
        "--profile",
        choices=list(HARDWARE_PROFILES.keys()),
        help="Hardware profil (prednastavi rozliseni a barvnou hloubku)",
    )
    parser.add_argument(
        "--live-preview-port", help="Odesle JSON na ESP32 (USB/seriovy port) po exportu"
    )
    parser.add_argument(
        "--live-preview-baud",
        type=int,
        default=115200,
        help="Baudrate pro live preview (default 115200)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Pouzije SDL dummy driver (bez realneho okna); vhodne pro CI/remote",
    )
    parser.add_argument(
        "--no-audio",
        action="store_true",
        help="Nastavi SDL_AUDIODRIVER=dummy (zamezi inicializaci zvuku)",
    )
    parser.add_argument(
        "--fps-limit",
        type=int,
        help="Cilovy FPS limit pro Pygame smycku (0 = neomezovat)",
    )
    parser.add_argument(
        "--autosave",
        action="store_true",
        help="Zapne autosave (interval lze nastavit env ESP32OS_AUTOSAVE_SECS)",
    )
    parser.add_argument(
        "--no-autosave",
        action="store_true",
        help="Vypne autosave i pokud je nastaven env",
    )
    return parser.parse_args()


def _apply_headless_env(enable_headless: bool, disable_audio: bool) -> None:
    """Set SDL env vars for headless/dummy mode."""
    if enable_headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    if disable_audio:
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


def run_headless(json_path: Path, width: int, height: int, profile: Optional[str] = None) -> int:
    """Create or update JSON without launching Pygame. If file exists, keep its dimensions unless forced."""
    designer = UIDesigner(width, height)
    if profile:
        designer.set_hardware_profile(profile)
    if json_path.exists():
        designer.load_from_json(str(json_path))
    else:
        designer.create_scene("main")
        sc = designer.scenes[designer.current_scene]
        sc.width, sc.height = width, height
    json_path.parent.mkdir(parents=True, exist_ok=True)
    designer.save_to_json(str(json_path))
    est = designer.estimate_resources()
    if est:
        print(
            f"[INFO] FB: {est['framebuffer_kb']:.1f}KB | Flash est: {est['flash_kb']:.1f}KB | Widgets: {int(est['widgets'])}"
        )
    print(f"[OK] Saved design JSON: {json_path}")
    return 0


def send_live_preview(json_path: Path, port: str, baud: int = 115200) -> None:
    """Best-effort push of JSON to ESP32 over serial. Expects device-side handler for framed JSON."""
    if not port.strip():
        print("[WARN] Live preview port is empty; skipping.")
        return
    if not re.match(r"^(COM\d+|/dev/tty(USB|ACM|S)\d+)$", port):
        print(f"[WARN] Suspicious serial port name: {port!r}; skipping live preview.")
        return
    try:
        import serial  # type: ignore
    except ImportError:
        print("[WARN] PySerial neni nainstalovany; preskakuji live preview.")
        return
    payload = json_path.read_text(encoding="utf-8")
    frame = f"<<UIJSON>>{payload}<<END>>".encode()
    try:
        with serial.Serial(port=port, baudrate=baud, timeout=2) as ser:
            ser.write(frame)
            ser.flush()
        print(f"[OK] Live preview odeslan na {port} @ {baud}")
    except (OSError, ValueError) as exc:
        print(f"[WARN] Live preview selhal ({exc})")


def main() -> None:
    args = parse_args()
    json_path = Path(args.json).expanduser()

    width = args.width
    height = args.height
    profile = args.profile
    if profile and profile in HARDWARE_PROFILES:
        pinfo = HARDWARE_PROFILES[profile]
        width, height = pinfo["width"], pinfo["height"]

    _apply_headless_env(
        enable_headless=args.headless or args.headless_export, disable_audio=args.no_audio
    )
    if args.fps_limit is not None:
        os.environ["ESP32OS_FPS"] = str(max(0, args.fps_limit))
    if args.autosave:
        os.environ["ESP32OS_AUTOSAVE"] = "1"
    if args.no_autosave:
        os.environ["ESP32OS_AUTOSAVE"] = "0"

    if args.headless_export:
        rc = run_headless(json_path, width, height, profile=profile)
        if args.live_preview_port:
            send_live_preview(json_path, args.live_preview_port, args.live_preview_baud)
        raise SystemExit(rc)

    _require_pygame()
    try:
        from cyberpunk_editor import CyberpunkEditorApp
    except ImportError as exc:
        print(f"[FAIL] Unable to start Pygame designer: {exc}")
        raise SystemExit(1) from None

    app = CyberpunkEditorApp(json_path, (width, height), profile=profile)
    app.run()


if __name__ == "__main__":
    main()
