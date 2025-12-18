"""
PlatformIO extra script: generate `src/ui_design.c` + `src/ui_design.h` from a UI Designer JSON.

Default input: `main_scene.json` (repo root), scene: `main`.

Env overrides:
  - ESP32OS_PIO_UI_EXPORT=0        Disable generation
  - ESP32OS_UI_JSON=<path>        Input JSON path
  - ESP32OS_UI_SCENE=<name>       Scene name (fallback: first scene)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

Import("env")  # noqa: F821 - provided by PlatformIO/SCons

try:
    REPO_ROOT = Path(__file__).resolve().parents[1]
except NameError:  # PlatformIO/SCons may execute without __file__
    REPO_ROOT = Path(env["PROJECT_DIR"])  # noqa: F821 - provided by PlatformIO/SCons
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.ui_codegen import generate_ui_design_pair, write_if_changed  # noqa: E402


def _main() -> None:
    if os.environ.get("ESP32OS_PIO_UI_EXPORT", "1").strip() == "0":
        print("[UI] Export disabled (ESP32OS_PIO_UI_EXPORT=0)")
        return

    project_dir = Path(env["PROJECT_DIR"])  # noqa: F821 - provided by PlatformIO/SCons
    json_path = Path(os.environ.get("ESP32OS_UI_JSON", str(project_dir / "main_scene.json"))).expanduser()
    if not json_path.is_absolute():
        json_path = project_dir / json_path

    scene_name = os.environ.get("ESP32OS_UI_SCENE", "main")
    out_c = project_dir / "src" / "ui_design.c"
    out_h = project_dir / "src" / "ui_design.h"

    if not json_path.exists():
        raise RuntimeError(f"[UI] JSON not found: {json_path}")

    try:
        source_label = json_path.relative_to(project_dir).as_posix()
    except Exception:
        source_label = json_path.name

    c_text, h_text = generate_ui_design_pair(json_path, scene_name=scene_name, source_label=source_label)
    changed = False
    changed |= write_if_changed(out_h, h_text)
    changed |= write_if_changed(out_c, c_text)
    if changed:
        print(f"[UI] Generated ui_design from {json_path.name} (scene: {scene_name})")


_main()
