#!/usr/bin/env python3
"""
C Header Export for UI Designer
Generates embedded-friendly const ui_widget_t arrays from JSON designs
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Widget type mapping to C enum
WIDGET_TYPE_MAP = {
    "label": "UI_WIDGET_LABEL",
    "box": "UI_WIDGET_BOX",
    "button": "UI_WIDGET_BUTTON",
    "gauge": "UI_WIDGET_GAUGE",
    "progressbar": "UI_WIDGET_PROGRESSBAR",
    "checkbox": "UI_WIDGET_CHECKBOX",
    "radiobutton": "UI_WIDGET_RADIOBUTTON",
    "slider": "UI_WIDGET_SLIDER",
    "chart": "UI_WIDGET_CHART",
    "icon": "UI_WIDGET_ICON",
    "spinner": "UI_WIDGET_SPINNER",
    "textbox": "UI_WIDGET_TEXTBOX",
    "panel": "UI_WIDGET_PANEL",
}

# Border style mapping
BORDER_STYLE_MAP = {
    "single": "UI_BORDER_SINGLE",
    "double": "UI_BORDER_DOUBLE",
    "rounded": "UI_BORDER_ROUNDED",
    "bold": "UI_BORDER_BOLD",
    "dashed": "UI_BORDER_DASHED",
    "none": "UI_BORDER_NONE",
}

# Align/valign mapping
ALIGN_MAP = {
    "left": "UI_ALIGN_LEFT",
    "center": "UI_ALIGN_CENTER",
    "right": "UI_ALIGN_RIGHT",
}

VALIGN_MAP = {
    "top": "UI_VALIGN_TOP",
    "middle": "UI_VALIGN_MIDDLE",
    "bottom": "UI_VALIGN_BOTTOM",
}


def sanitize_name(name: str) -> str:
    """Convert scene/widget name to valid C identifier."""
    # Replace spaces/dashes with underscores, remove invalid chars
    sanitized = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
    # Ensure doesn't start with digit
    if sanitized and sanitized[0].isdigit():
        sanitized = "scene_" + sanitized
    return sanitized.lower()


def escape_c_string(text: str) -> str:
    """Escape string for C literal."""
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")


def parse_color(color_name: str) -> str:
    """Convert color name to C constant (assumes ui_render.h defines these)."""
    color_upper = color_name.upper()
    # Common colors
    color_map = {
        "BLACK": "UI_COLOR_BLACK",
        "WHITE": "UI_COLOR_WHITE",
        "RED": "UI_COLOR_RED",
        "GREEN": "UI_COLOR_GREEN",
        "BLUE": "UI_COLOR_BLUE",
        "YELLOW": "UI_COLOR_YELLOW",
        "CYAN": "UI_COLOR_CYAN",
        "MAGENTA": "UI_COLOR_MAGENTA",
        "GRAY": "UI_COLOR_GRAY",
        "ORANGE": "UI_COLOR_ORANGE",
        "PURPLE": "UI_COLOR_PURPLE",
        "BROWN": "UI_COLOR_BROWN",
    }
    # Handle hex colors by converting to closest named color or using raw value
    if color_name.startswith("#"):
        return f"0x{color_name[1:].upper()}"
    return color_map.get(color_upper, f"UI_COLOR_{color_upper}")


def generate_widget_struct(widget: Dict[str, Any], index: int) -> str:
    """Generate C initializer for single widget."""
    wtype = WIDGET_TYPE_MAP.get(widget.get("type", "label"), "UI_WIDGET_LABEL")
    x = widget.get("x", 0)
    y = widget.get("y", 0)
    w = widget.get("width", 10)
    h = widget.get("height", 3)
    text = escape_c_string(widget.get("text", ""))
    fg = parse_color(widget.get("color_fg", "white"))
    bg = parse_color(widget.get("color_bg", "black"))
    border = "true" if widget.get("border", True) else "false"
    border_style = BORDER_STYLE_MAP.get(widget.get("border_style", "single"), "UI_BORDER_SINGLE")
    align = ALIGN_MAP.get(widget.get("align", "left"), "UI_ALIGN_LEFT")
    valign = VALIGN_MAP.get(widget.get("valign", "middle"), "UI_VALIGN_MIDDLE")
    visible = "true" if widget.get("visible", True) else "false"
    enabled = "true" if widget.get("enabled", True) else "false"
    value = widget.get("value", 0)
    min_val = widget.get("min_value", 0)
    max_val = widget.get("max_value", 100)

    return f"""    {{ // Widget {index}: {widget.get('type', 'label')}
        .type = {wtype},
        .x = {x}, .y = {y}, .width = {w}, .height = {h},
        .text = "{text}",
        .fg_color = {fg}, .bg_color = {bg},
        .border = {border}, .border_style = {border_style},
        .align = {align}, .valign = {valign},
        .visible = {visible}, .enabled = {enabled},
        .value = {value}, .min_value = {min_val}, .max_value = {max_val},
    }}"""


def generate_scene_header(scene_name: str, scene_data: Dict[str, Any]) -> str:
    """Generate C header for single scene."""
    safe_name = sanitize_name(scene_name)
    widgets = scene_data.get("widgets", [])
    width = scene_data.get("width", 128)
    height = scene_data.get("height", 64)
    bg_color = parse_color(scene_data.get("bg_color", "black"))

    widget_count = len(widgets)

    if widget_count == 0:
        widget_structs = "    // No widgets"
    else:
        widget_structs = ",\n".join(generate_widget_struct(w, i) for i, w in enumerate(widgets))

    header = f"""
// Scene: {scene_name}
// Size: {width}x{height}, Widgets: {widget_count}

static const ui_widget_t {safe_name}_widgets[] = {{
{widget_structs}
}};

static const ui_scene_t {safe_name}_scene = {{
    .name = "{scene_name}",
    .width = {width},
    .height = {height},
    .bg_color = {bg_color},
    .widget_count = {widget_count},
    .widgets = {safe_name}_widgets,
}};
"""
    return header


def export_c_header(json_path: Path, output_path: Path):
    """Main export function: JSON → C header."""
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[ERROR] Error reading JSON: {e}")
        sys.exit(1)

    scenes_raw = data.get("scenes", {})

    # Convert scenes list to dict if needed
    if isinstance(scenes_raw, list):
        scenes = {scene.get("id", f"scene_{i}"): scene for i, scene in enumerate(scenes_raw)}
    else:
        scenes = scenes_raw

    if not scenes:
        print("[WARN] Warning: No scenes found in JSON")
        sys.exit(0)

    # Generate header
    header_guard = output_path.stem.upper().replace("-", "_") + "_H"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    output = f"""/*
 * Auto-generated UI Design Header
 * Source: {json_path.name}
 * Generated: {timestamp}
 * DO NOT EDIT MANUALLY
 */

#ifndef {header_guard}
#define {header_guard}

#include "ui_render.h"

"""

    # Generate each scene
    for scene_name, scene_data in scenes.items():
        output += generate_scene_header(scene_name, scene_data)

    # Add scene array
    output += "\n// Scene registry\n"
    output += "static const ui_scene_t* all_scenes[] = {\n"
    for scene_name in scenes.keys():
        safe_name = sanitize_name(scene_name)
        output += f"    &{safe_name}_scene,\n"
    output += "};\n\n"
    output += f"#define SCENE_COUNT {len(scenes)}\n\n"
    output += f"#endif // {header_guard}\n"

    # Write output
    try:
        output_path.write_text(output, encoding="utf-8")
        total_widgets = sum(len(s.get("widgets", [])) for s in scenes.values())
        print(f"[OK] C header exported: {output_path}")
        print(f"  Scenes: {len(scenes)}, Total widgets: {total_widgets}")
    except Exception as e:
        print(f"[ERROR] Error writing header: {e}")
        sys.exit(1)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Export UI Designer JSON to C header")
    parser.add_argument("json_file", help="Input JSON design file")
    parser.add_argument("-o", "--output", help="Output .h file (default: <json_name>.h)")
    args = parser.parse_args()

    json_path = Path(args.json_file)
    if not json_path.exists():
        print(f"[ERROR] File not found: {json_path}")
        sys.exit(1)

    output_path = Path(args.output) if args.output else json_path.with_suffix(".h")

    export_c_header(json_path, output_path)


if __name__ == "__main__":
    main()
