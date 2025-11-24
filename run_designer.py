#!/usr/bin/env python3
"""
Quick launcher for UI Designer with GUI (Dark Mode)
"""

# Hard dependency: Pillow (used by preview rendering)
try:
    import PIL  # noqa: F401
except ImportError:
    print(
        "[ERROR] Missing dependency 'Pillow'. Install it with "
        "`python -m pip install -r requirements.txt` "
        "or `python -m pip install pillow`, then rerun."
    )
    raise SystemExit(1)

import re
from pathlib import Path

# Import from preview module
from preview.window import TK_AVAILABLE, VisualPreviewWindow
from ui_designer import UIDesigner


def _read_display_resolution(default=(128, 64)) -> tuple[int, int]:
    """Read DISPLAY_WIDTH/HEIGHT from src/display_config.h if present."""
    cfg_path = Path(__file__).parent / "src" / "display_config.h"
    if not cfg_path.exists():
        return default
    try:
        text = cfg_path.read_text(encoding="utf-8", errors="ignore")
        w = re.search(r"#define\s+DISPLAY_WIDTH\s+(\d+)", text)
        h = re.search(r"#define\s+DISPLAY_HEIGHT\s+(\d+)", text)
        if w and h:
            width = int(w.group(1))
            height = int(h.group(1))
            if width > 0 and height > 0:
                return width, height
    except Exception:
        pass
    return default

# Create designer sized to firmware display (falls back to 128x64)
width, height = _read_display_resolution()
designer = UIDesigner(width=width, height=height)
# Reduce friction: start with grid/snap disabled
designer.grid_enabled = False
designer.snap_to_grid = False

# Create default scene (empty canvas - ready for your widgets)
designer.create_scene("main")
designer.current_scene = "main"

# Launch visual editor with dark theme
print(f"Opening UI Designer in Dark Mode at {width}x{height}...")
print("- Drag widgets to move")
print("- Drag handles to resize")
print("- Double-click to edit properties")
print("- Ctrl+S to save")
print("- Theme: Dark (customizable in dropdown)")

if not TK_AVAILABLE:
    print(
        "[ERROR] Tkinter GUI is not available. "
        "Install Tk (e.g., `python -m pip install tk` on Windows "
        "or `sudo apt-get install python3-tk` on Linux) and try again."
    )
    raise SystemExit(1)

preview = VisualPreviewWindow(designer)
# Mirror the no-grid, no-snap defaults in the preview UI
try:
    preview.settings.grid_enabled = False
    preview.settings.snap_enabled = False
    if hasattr(preview, "grid_var"):
        preview.grid_var.set(False)
    if hasattr(preview, "snap_var"):
        preview.snap_var.set(False)
except Exception:
    pass
preview.run()
