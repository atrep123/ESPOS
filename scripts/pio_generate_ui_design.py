"""
PlatformIO extra script: generate `src/ui_design.c` + `src/ui_design.h` from a UI Designer JSON.

Default input: `main_scene.json` (repo root), scene: `main`.

Env overrides:
  - ESP32OS_PIO_UI_EXPORT=0        Disable generation
  - ESP32OS_UI_JSON=<path>        Input JSON path
  - ESP32OS_UI_SCENE=<name>       Scene name (fallback: first scene)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

Import("env")  # type: ignore[name-defined]  # noqa: F821

try:
    REPO_ROOT = Path(__file__).resolve().parents[1]
except NameError:  # PlatformIO/SCons may execute without __file__
    REPO_ROOT = Path(env["PROJECT_DIR"])  # type: ignore[name-defined]  # noqa: F821
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.ui_codegen import (
    generate_ui_design_multi_pair,
    generate_ui_design_pair,
    load_scenes,
    write_if_changed,
)
from tools.validate_design import validate_file


def _strip_optional_quotes(value: str) -> str:
    text = value.strip()
    if len(text) >= 2 and (
        (text[0] == '"' and text[-1] == '"') or (text[0] == "'" and text[-1] == "'")
    ):
        text = text[1:-1].strip()
    return text


def _main() -> None:
    export_flag = os.environ.get("ESP32OS_PIO_UI_EXPORT", "1").strip().lower()
    if export_flag not in {"0", "false", "off", "no", "1", "true", "on", "yes"}:
        raise RuntimeError(
            f"[UI] ESP32OS_PIO_UI_EXPORT must be 0/1/true/false/on/off/yes/no, got: {export_flag!r}"
        )

    project_dir = Path(env["PROJECT_DIR"])  # type: ignore[name-defined]  # noqa: F821
    json_override = os.environ.get("ESP32OS_UI_JSON")
    if json_override is not None:
        json_override = _strip_optional_quotes(json_override)
        if not json_override:
            raise RuntimeError("[UI] ESP32OS_UI_JSON cannot be empty")

    json_path_raw = (
        json_override if json_override is not None else str(project_dir / "main_scene.json")
    )
    json_path = Path(json_path_raw).expanduser()
    if not json_path.is_absolute():
        json_path = project_dir / json_path
    json_path = json_path.resolve()
    try:
        json_path.relative_to(project_dir.resolve())
    except ValueError as exc:
        raise RuntimeError(f"[UI] JSON path escapes project directory: {json_path}") from exc
    if json_path.exists() and json_path.is_dir():
        raise RuntimeError(f"[UI] JSON path points to a directory: {json_path}")

    scene_name_raw = os.environ.get("ESP32OS_UI_SCENE", "main")
    scene_name = _strip_optional_quotes(scene_name_raw)
    if not scene_name:
        raise RuntimeError("[UI] ESP32OS_UI_SCENE cannot be empty")
    out_c = project_dir / "src" / "ui_design.c"
    out_h = project_dir / "src" / "ui_design.h"

    if not json_path.exists():
        raise RuntimeError(f"[UI] JSON not found: {json_path}")

    try:
        source_label = json_path.relative_to(project_dir).as_posix()
    except ValueError:
        source_label = json_path.name
    try:
        scenes = load_scenes(json_path)
    except (json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"[UI] Failed to parse {json_path.name}: {exc}") from exc

    # Mandatory for every build, including reuse of already generated files.
    issues = validate_file(json_path, warnings_as_errors=False)
    errors = [i for i in issues if i.level == "ERROR"]
    if errors:
        for e in errors:
            print(f"[UI][VALIDATE] {e.level}: {e.message}")
        raise RuntimeError(f"[UI] Validation found {len(errors)} error(s) in {json_path.name}")
    for w in (i for i in issues if i.level in {"WARNING", "WARN"}):
        print(f"[UI][VALIDATE] {w.level}: {w.message}")

    if len(scenes) > 1:
        c_text, h_text = generate_ui_design_multi_pair(json_path, source_label=source_label)
        mode = f"multi-scene, {len(scenes)} scenes"
    else:
        c_text, h_text = generate_ui_design_pair(
            json_path, scene_name=scene_name, source_label=source_label
        )
        mode = f"scene: {scene_name}"

    if export_flag in {"0", "false", "off", "no"}:
        if (
            not out_c.is_file()
            or not out_h.is_file()
            or out_c.read_text(encoding="utf-8") != c_text
            or out_h.read_text(encoding="utf-8") != h_text
        ):
            raise RuntimeError(
                "[UI] Export disabled, but generated files do not match validated design"
            )
        print("[UI] Reusing validated, current generated files")
        return

    changed = False
    changed |= write_if_changed(out_h, h_text)
    changed |= write_if_changed(out_c, c_text)
    if changed:
        print(f"[UI] Generated ui_design from {json_path.name} ({mode})")


_main()
