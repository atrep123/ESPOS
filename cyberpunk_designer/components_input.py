"""Input, chart & data component blueprints: chart_bar, chart_line,
gauge_hud, setting_int, setting_bool, setting_enum, toggle."""

from __future__ import annotations

from typing import Any, Dict, List

from .components_shared import (
    LABEL_H,
    NEON_FG,
    NEON_MAGENTA,
    PAD,
    PANEL2_BG,
    PANEL_BG,
    TEXT_FG,
    scene_size,
    scene_width,
)


def build_chart_bar(sc: object) -> List[Dict[str, Any]]:
    return [
        {
            "type": "panel",
            "role": "panel",
            "x": 0,
            "y": 0,
            "width": 320,
            "height": 200,
            "border": True,
            "border_style": "single",
            "color_fg": NEON_FG,
            "color_bg": PANEL_BG,
            "z": 0,
        },
        {
            "type": "chart",
            "role": "chart",
            "x": 14,
            "y": 16,
            "width": 292,
            "height": 150,
            "text": "Bar chart",
            "style": "bar",
            "data_points": [10, 30, 20, 60, 40, 80],
            "color_fg": NEON_MAGENTA,
            "color_bg": PANEL2_BG,
            "border": True,
            "border_style": "rounded",
            "z": 1,
        },
        {
            "type": "label",
            "role": "title",
            "x": 14,
            "y": 172,
            "width": 292,
            "height": LABEL_H,
            "text": "Chart title",
            "color_fg": TEXT_FG,
            "color_bg": PANEL_BG,
            "border": False,
            "z": 1,
        },
    ]


def build_chart_line(sc: object) -> List[Dict[str, Any]]:
    return [
        {
            "type": "panel",
            "role": "panel",
            "x": 0,
            "y": 0,
            "width": 320,
            "height": 200,
            "border": True,
            "border_style": "single",
            "color_fg": NEON_FG,
            "color_bg": PANEL_BG,
            "z": 0,
        },
        {
            "type": "chart",
            "role": "chart",
            "x": 14,
            "y": 16,
            "width": 292,
            "height": 150,
            "text": "Line chart",
            "style": "line",
            "data_points": [5, 10, 18, 12, 25, 30, 22],
            "color_fg": NEON_FG,
            "color_bg": PANEL2_BG,
            "border": True,
            "border_style": "rounded",
            "z": 1,
        },
        {
            "type": "label",
            "role": "title",
            "x": 14,
            "y": 172,
            "width": 292,
            "height": LABEL_H,
            "text": "Chart title",
            "color_fg": TEXT_FG,
            "color_bg": PANEL_BG,
            "border": False,
            "z": 1,
        },
    ]


def build_gauge_hud(sc: object) -> List[Dict[str, Any]]:
    sw, sh = scene_size(sc, 256, 128)
    panel_w = max(64, min(sw, 240))
    panel_h = max(64, min(sh, 140))
    content_w = max(1, panel_w - 24)
    return [
        {
            "type": "panel",
            "role": "panel",
            "x": 0,
            "y": 0,
            "width": panel_w,
            "height": panel_h,
            "border": True,
            "border_style": "rounded",
            "color_fg": NEON_MAGENTA,
            "color_bg": PANEL_BG,
            "z": 0,
        },
        {
            "type": "label",
            "role": "title",
            "x": PAD,
            "y": 12,
            "width": content_w,
            "height": LABEL_H,
            "text": "HUD",
            "style": "bold",
            "align": "left",
            "valign": "middle",
            "text_overflow": "ellipsis",
            "max_lines": 1,
            "color_fg": NEON_MAGENTA,
            "color_bg": PANEL_BG,
            "border": False,
            "z": 1,
        },
        {
            "type": "gauge",
            "role": "gauge",
            "x": PAD,
            "y": 36,
            "width": content_w,
            "height": 44,
            "text": "RPM",
            "value": 42,
            "min_value": 0,
            "max_value": 100,
            "color_fg": NEON_FG,
            "color_bg": PANEL2_BG,
            "border": True,
            "border_style": "rounded",
            "z": 1,
        },
        {
            "type": "label",
            "role": "line1",
            "x": PAD,
            "y": 88,
            "width": content_w,
            "height": LABEL_H,
            "text": "Speed: 88",
            "align": "left",
            "valign": "middle",
            "text_overflow": "ellipsis",
            "max_lines": 1,
            "color_fg": TEXT_FG,
            "color_bg": PANEL_BG,
            "border": False,
            "z": 1,
        },
        {
            "type": "label",
            "role": "line2",
            "x": PAD,
            "y": 108,
            "width": content_w,
            "height": LABEL_H,
            "text": "Temp: 42C",
            "align": "left",
            "valign": "middle",
            "text_overflow": "ellipsis",
            "max_lines": 1,
            "color_fg": TEXT_FG,
            "color_bg": PANEL_BG,
            "border": False,
            "z": 1,
        },
    ]


def build_setting_int(sc: object) -> List[Dict[str, Any]]:
    sw = scene_width(sc, 256)
    row_w = max(64, min(240, max(1, sw) - 8))
    return [
        {
            "type": "button",
            "role": "item",
            "x": 0,
            "y": 0,
            "width": row_w,
            "height": LABEL_H,
            "text": "Setting",
            "align": "left",
            "valign": "middle",
            "text_overflow": "ellipsis",
            "max_lines": 1,
            "runtime": "bind=key;kind=int;min=0;max=100;step=1",
            "color_fg": TEXT_FG,
            "color_bg": PANEL2_BG,
            "border": True,
            "border_style": "single",
            "z": 0,
        },
    ]


def build_setting_bool(sc: object) -> List[Dict[str, Any]]:
    sw = scene_width(sc, 256)
    row_w = max(64, min(240, max(1, sw) - 8))
    return [
        {
            "type": "button",
            "role": "item",
            "x": 0,
            "y": 0,
            "width": row_w,
            "height": LABEL_H,
            "text": "Setting",
            "align": "left",
            "valign": "middle",
            "text_overflow": "ellipsis",
            "max_lines": 1,
            "runtime": "bind=key;kind=bool;values=off|on",
            "color_fg": TEXT_FG,
            "color_bg": PANEL2_BG,
            "border": True,
            "border_style": "single",
            "z": 0,
        },
    ]


def build_setting_enum(sc: object) -> List[Dict[str, Any]]:
    sw = scene_width(sc, 256)
    row_w = max(64, min(240, max(1, sw) - 8))
    return [
        {
            "type": "button",
            "role": "item",
            "x": 0,
            "y": 0,
            "width": row_w,
            "height": LABEL_H,
            "text": "Setting",
            "align": "left",
            "valign": "middle",
            "text_overflow": "ellipsis",
            "max_lines": 1,
            "runtime": "bind=key;kind=enum;values=A|B|C",
            "color_fg": TEXT_FG,
            "color_bg": PANEL2_BG,
            "border": True,
            "border_style": "single",
            "z": 0,
        },
    ]


def build_toggle(sc: object) -> List[Dict[str, Any]]:
    sw = scene_width(sc, 256)
    row_w = max(64, min(240, max(1, sw) - 8))
    return [
        {
            "type": "toggle",
            "role": "toggle",
            "x": 0,
            "y": 0,
            "width": row_w,
            "height": LABEL_H,
            "text": "Toggle",
            "checked": False,
            "align": "left",
            "valign": "middle",
            "color_fg": TEXT_FG,
            "color_bg": PANEL2_BG,
            "border": False,
            "z": 0,
        },
    ]
