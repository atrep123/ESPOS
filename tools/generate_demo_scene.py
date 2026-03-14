import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEMPLATES_PATH = ROOT / "templates.json"

from tools.validate_design import validate_file
from ui_cli import create_cli_interface


def _output_path_from_argv() -> Path:
    if len(sys.argv) >= 2 and sys.argv[1].strip():
        out = Path(sys.argv[1])
        return out if out.is_absolute() else (ROOT / out)
    return ROOT / "demo_scene.json"


OUT_PATH = _output_path_from_argv()
OUT_REL = OUT_PATH.relative_to(ROOT) if OUT_PATH.is_absolute() else OUT_PATH

cmds = [
    "new demo_clean2",
    "bp 256x128",
    "snap off",
    'add label 4 2 248 12 "ESP32OS SHARP LCD DEMO"',
    'add label 4 16 248 12 "PICO2W LS027B7DH01"',
    'add label 4 32 122 12 "SYSTEM INFO"',
    'add label 4 46 122 12 "BOARD: PICO 2W"',
    'add label 4 60 122 12 "CPU: RP2350"',
    'add label 130 32 122 12 "DISPLAY"',
    'add label 130 46 122 12 "LS027B7DH01"',
    'add label 130 60 122 12 "SHARP MEMORY LCD"',
    'add button 4 80 248 12 "PRIMITIVES"',
    "add box 4 98 8 8",
    "add box 20 98 10 10",
    "add box 44 98 12 12",
    "add box 72 98 14 14",
    "add box 104 98 16 16",
    "edit 0 border true",
    "edit 1 border true",
    "edit 2 border true",
    "edit 3 border true",
    "edit 4 border true",
    "edit 5 border true",
    "edit 6 border true",
    "edit 7 border true",
    "edit 0 valign top",
    "edit 1 valign top",
    "edit 2 valign top",
    "edit 3 valign top",
    "edit 4 valign top",
    "edit 5 valign top",
    "edit 6 valign top",
    "edit 7 valign top",
    "new checkerboard_demo",
    "bp 256x128",
    "snap off",
    'add button 4 2 248 12 "CHECKERBOARD"',
    'add label 8 20 112 12 "8x8 CELLS"',
    'add label 130 20 56 12 "4x4"',
    'add label 194 20 56 12 "16x16"',
    'add label 130 68 116 12 "10x10 MIX"',
    "add box 6 34 112 82",
    "add box 128 34 56 32",
    "add box 192 34 56 32",
    "add box 128 82 120 34",
    "edit 0 border true",
    "edit 0 valign top",
    "new animation_demo",
    "bp 256x128",
    "snap off",
    'add label 4 2 186 12 "ESP32OS SHARP LCD DEMO"',
    'add label 194 2 58 12 "F:0123"',
    'add label 4 20 248 12 "ANIMATION"',
    "add box 2 34 252 64",
    'add button 6 104 52 14 "HI!"',
    "edit 0 border true",
    "edit 1 border true",
    "edit 2 border true",
    "edit 2 valign top",
    "edit 4 border true",
    "switch demo_clean2",
    f"save {OUT_REL.as_posix()}",
    "quit",
]

_templates_before = TEMPLATES_PATH.read_bytes() if TEMPLATES_PATH.exists() else None
try:
    create_cli_interface(cmds)
finally:
    if _templates_before is None:
        if TEMPLATES_PATH.exists():
            TEMPLATES_PATH.unlink()
    elif TEMPLATES_PATH.read_bytes() != _templates_before:
        TEMPLATES_PATH.write_bytes(_templates_before)

SCHEMA_PATH = ROOT / "schemas" / "ui_design.schema.json"
VALUE_WIDGET_TYPES = {"gauge", "progressbar", "slider", "chart"}


def _normalize_widgets_to_schema(data: dict) -> dict:
    with SCHEMA_PATH.open("r", encoding="utf-8") as sf:
        schema = json.load(sf)

    allowed = set(schema["$defs"]["widget"]["properties"].keys())
    for scene in data.get("scenes", {}).values():
        widgets = scene.get("widgets", [])
        if not isinstance(widgets, list):
            continue
        normalized_widgets = []
        for widget in widgets:
            if not isinstance(widget, dict):
                normalized_widgets.append(widget)
                continue
            normalized = {k: v for k, v in widget.items() if k in allowed}
            if "items" in widget and "list_items" in allowed and "list_items" not in normalized:
                normalized["list_items"] = widget.get("items")
            normalized_widgets.append(normalized)
        scene["widgets"] = normalized_widgets
    return data


with OUT_PATH.open("r", encoding="utf-8") as f:
    generated = json.load(f)

for scene in generated.get("scenes", {}).values():
    for widget in scene.get("widgets", []):
        if widget.get("type") not in VALUE_WIDGET_TYPES:
            widget.pop("max_value", None)

generated = _normalize_widgets_to_schema(generated)

with OUT_PATH.open("w", encoding="utf-8") as f:
    json.dump(generated, f, indent=2)

issues = validate_file(OUT_PATH, warnings_as_errors=False, strict_critical=True)
errors = [issue for issue in issues if issue.level == "ERROR"]
if errors:
    for issue in errors:
        print(f"[STRICT-CRITICAL] {issue.message}")
    raise SystemExit(1)
