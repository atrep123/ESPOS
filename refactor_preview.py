#!/usr/bin/env python3
"""
Refactor ui_designer_preview.py into modular structure.
Splits the monolithic file into preview/ package.
"""

import os
import re


def extract_animation_editor():
    """Extract AnimationEditorWindow class to separate file."""
    with open("ui_designer_preview.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Find AnimationEditorWindow class
    match = re.search(
        r"(class AnimationEditorWindow:.*?)(?=\nclass |\n# ----|$)", content, re.DOTALL
    )

    if not match:
        print("AnimationEditorWindow not found")
        return

    class_code = match.group(1)

    # Extract imports needed
    imports = """'''Animation editor timeline window.'''

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Any, Optional

from design_tokens import color_hex

if TYPE_CHECKING:
    from preview.window import VisualPreviewWindow

try:
    COMBO_SELECTED = "<<ComboboxSelected>>"
except Exception:
    COMBO_SELECTED = "<ComboboxSelected>"


"""

    animation_file = imports + class_code

    os.makedirs("preview", exist_ok=True)
    with open("preview/animation_editor.py", "w", encoding="utf-8") as f:
        f.write(animation_file)

    print("✓ Created preview/animation_editor.py")


def create_rendering_module():
    """Extract rendering helpers to separate module."""
    rendering_code = '''"""Widget rendering helpers for preview canvas."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Tuple

from PIL import Image, ImageDraw

from design_tokens import color_hex

if TYPE_CHECKING:
    from ui_models import WidgetConfig


def size(w: int, h: int, spacing_scale: float) -> Tuple[int, int]:
    """Scale a base (w,h) by current responsive spacing scale."""
    return (int(w * spacing_scale), int(h * spacing_scale))


def widget_edges(w: "WidgetConfig") -> Dict[str, int]:
    """Return all relevant edge and center positions for a widget (helper)."""
    return {
        "left": w.x,
        "right": w.x + w.width,
        "top": w.y,
        "bottom": w.y + w.height,
        "center_x": w.x + w.width // 2,
        "center_y": w.y + w.height // 2,
    }


def get_color_rgb(color_name: str) -> Tuple[int, int, int]:
    """Convert color name to RGB tuple."""
    colors = {
        "black": (0, 0, 0),
        "white": (255, 255, 255),
        "red": (255, 0, 0),
        "green": (0, 255, 0),
        "blue": (0, 0, 255),
        "yellow": (255, 255, 0),
        "cyan": (0, 255, 255),
        "magenta": (255, 0, 255),
        "gray": (128, 128, 128),
        "orange": (255, 165, 0),
        "purple": (128, 0, 128),
    }
    return colors.get(color_name.lower(), (255, 255, 255))


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore


def draw_rounded_rectangle(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[int, int, int, int],
    radius: int,
    fill: Any = None,
    outline: Any = None,
    width: int = 1,
) -> None:
    """Draw a rounded rectangle on PIL ImageDraw."""
    x1, y1, x2, y2 = xy
    if radius > 0:
        diameter = radius * 2
        # Main rectangles
        draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
        draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
        # Corners
        draw.ellipse([x1, y1, x1 + diameter, y1 + diameter], fill=fill)
        draw.ellipse([x2 - diameter, y1, x2, y1 + diameter], fill=fill)
        draw.ellipse([x1, y2 - diameter, x1 + diameter, y2], fill=fill)
        draw.ellipse([x2 - diameter, y2 - diameter, x2, y2], fill=fill)
        # Border
        if outline and width > 0:
            draw.arc([x1, y1, x1 + diameter, y1 + diameter], 180, 270, fill=outline, width=width)
            draw.arc([x2 - diameter, y1, x2, y1 + diameter], 270, 360, fill=outline, width=width)
            draw.arc([x1, y2 - diameter, x1 + diameter, y2], 90, 180, fill=outline, width=width)
            draw.arc([x2 - diameter, y2 - diameter, x2, y2], 0, 90, fill=outline, width=width)
            draw.line([x1 + radius, y1, x2 - radius, y1], fill=outline, width=width)
            draw.line([x1 + radius, y2, x2 - radius, y2], fill=outline, width=width)
            draw.line([x1, y1 + radius, x1, y2 - radius], fill=outline, width=width)
            draw.line([x2, y1 + radius, x2, y2 - radius], fill=outline, width=width)
    else:
        draw.rectangle(xy, fill=fill, outline=outline, width=width)
'''

    os.makedirs("preview", exist_ok=True)
    with open("preview/rendering.py", "w", encoding="utf-8") as f:
        f.write(rendering_code)

    print("✓ Created preview/rendering.py")


def update_init():
    """Update __init__.py to use noqa for intentional re-exports."""
    init_code = '''"""Preview module for UI Designer - modular architecture."""

from preview.animation_editor import AnimationEditorWindow  # noqa: F401
from preview.settings import PreviewSettings  # noqa: F401
from preview.window import VisualPreviewWindow  # noqa: F401

__all__ = ["PreviewSettings", "VisualPreviewWindow", "AnimationEditorWindow"]
'''

    with open("preview/__init__.py", "w", encoding="utf-8") as f:
        f.write(init_code)

    print("✓ Updated preview/__init__.py")


if __name__ == "__main__":
    print("Refactoring ui_designer_preview.py...")
    print()

    create_rendering_module()
    extract_animation_editor()
    update_init()

    print()
    print("✓ Refactoring complete!")
    print()
    print("Next steps:")
    print("1. Review generated files in preview/")
    print("2. Main window class still in ui_designer_preview.py (too large to auto-extract)")
    print("3. Manually split VisualPreviewWindow into preview/window.py")
    print("4. Update imports in other files to use: from preview import VisualPreviewWindow")
