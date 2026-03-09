from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui_cli import create_cli_interface
from tools.validate_design import validate_file

cmds = [
    "new demo_clean2",
    "bp 256x128",
    "snap off",
    "add label 4 2 248 12 \"ESP32OS SHARP LCD DEMO\"",
    "add label 4 16 248 12 \"PICO2W LS027B7DH01\"",
    "add label 4 32 122 12 \"SYSTEM INFO\"",
    "add label 4 46 122 12 \"BOARD: PICO 2W\"",
    "add label 4 60 122 12 \"CPU: RP2350\"",
    "add label 130 32 122 12 \"DISPLAY\"",
    "add label 130 46 122 12 \"LS027B7DH01\"",
    "add label 130 60 122 12 \"SHARP MEMORY LCD\"",
    "add label 4 80 248 12 \"PRIMITIVES\"",
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
    "add label 4 2 248 12 \"CHECKERBOARD\"",
    "add label 8 20 112 12 \"8x8 CELLS\"",
    "add label 130 20 56 12 \"4x4\"",
    "add label 194 20 56 12 \"16x16\"",
    "add label 130 68 116 12 \"10x10 MIX\"",
    "add box 6 34 112 82",
    "add box 128 34 56 32",
    "add box 192 34 56 32",
    "add box 128 82 120 34",
    "edit 0 border true",
    "edit 0 valign top",
    "new animation_demo",
    "bp 256x128",
    "snap off",
    "add label 4 2 186 12 \"ESP32OS SHARP LCD DEMO\"",
    "add label 194 2 58 12 \"F:0123\"",
    "add label 4 20 248 12 \"ANIMATION\"",
    "add box 2 34 252 64",
    "add button 6 104 52 14 \"HI!\"",
    "edit 0 border true",
    "edit 1 border true",
    "edit 2 border true",
    "edit 2 valign top",
    "edit 4 border true",
    "switch demo_clean2",
    "save demo_scene.json",
    "quit",
]

create_cli_interface(cmds)

OUT_PATH = ROOT / "demo_scene.json"
issues = validate_file(OUT_PATH, warnings_as_errors=False, strict_critical=True)
errors = [issue for issue in issues if issue.level == "ERROR"]
if errors:
    for issue in errors:
        print(f"[STRICT-CRITICAL] {issue.message}")
    raise SystemExit(1)
