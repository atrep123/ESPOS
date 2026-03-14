"""Navigation & list component blueprints: tabs, list, menu_list, list_item."""

from __future__ import annotations

from typing import Any, Dict, List

from .components_shared import (
    LABEL_H,
    NEON_FG,
    NEON_MAGENTA,
    PAD_SM,
    PANEL2_BG,
    PANEL_BG,
    TEXT_FG,
    scene_size,
    scene_width,
)


def build_tabs(sc: object) -> List[Dict[str, Any]]:
    sw, sh = scene_size(sc, 256, 128)
    tabbar_h = 24
    tab_w = max(48, (sw - 8) // 3)
    return [
        {
            "type": "panel",
            "role": "tabbar",
            "x": 0,
            "y": 0,
            "width": sw,
            "height": tabbar_h,
            "border": True,
            "border_style": "single",
            "color_fg": NEON_FG,
            "color_bg": PANEL2_BG,
            "z": 0,
        },
        {
            "type": "button",
            "role": "tab1",
            "x": 4,
            "y": 4,
            "width": tab_w,
            "height": LABEL_H,
            "text": "Tab 1",
            "style": "bold highlight",
            "align": "center",
            "valign": "middle",
            "text_overflow": "ellipsis",
            "max_lines": 1,
            "color_fg": NEON_MAGENTA,
            "color_bg": PANEL_BG,
            "border": True,
            "border_style": "rounded",
            "z": 1,
        },
        {
            "type": "button",
            "role": "tab2",
            "x": 4 + tab_w + 4,
            "y": 4,
            "width": tab_w,
            "height": LABEL_H,
            "text": "Tab 2",
            "align": "center",
            "valign": "middle",
            "text_overflow": "ellipsis",
            "max_lines": 1,
            "color_fg": TEXT_FG,
            "color_bg": PANEL_BG,
            "border": True,
            "border_style": "rounded",
            "z": 1,
        },
        {
            "type": "button",
            "role": "tab3",
            "x": 4 + (tab_w + 4) * 2,
            "y": 4,
            "width": max(48, sw - (4 + (tab_w + 4) * 2) - 4),
            "height": LABEL_H,
            "text": "Tab 3",
            "align": "center",
            "valign": "middle",
            "text_overflow": "ellipsis",
            "max_lines": 1,
            "color_fg": TEXT_FG,
            "color_bg": PANEL_BG,
            "border": True,
            "border_style": "rounded",
            "z": 1,
        },
        {
            "type": "panel",
            "role": "content",
            "x": 0,
            "y": tabbar_h,
            "width": sw,
            "height": max(1, sh - tabbar_h),
            "border": True,
            "border_style": "single",
            "color_fg": NEON_FG,
            "color_bg": PANEL_BG,
            "z": 0,
        },
        {
            "type": "label",
            "role": "content.title",
            "x": 8,
            "y": tabbar_h + 6,
            "width": max(1, sw - 16),
            "height": LABEL_H,
            "text": "Tab content",
            "align": "left",
            "valign": "top",
            "text_overflow": "ellipsis",
            "max_lines": 1,
            "color_fg": TEXT_FG,
            "color_bg": PANEL_BG,
            "border": False,
            "z": 1,
        },
    ]


def build_list(sc: object) -> List[Dict[str, Any]]:
    sw, sh = scene_size(sc, 256, 128)
    pad = PAD_SM
    w = max(64, min(sw, sw - pad * 2))
    # Keep the list inside the scene (no minimum taller than the screen).
    max_h = max(0, sh - pad * 2)
    title_h = 16
    item_h = 16
    # Fit as many items as possible (up to 6) without overflowing the panel.
    max_items = 6
    min_h = title_h + 4 + item_h + 4
    h = max(min_h, min(120, max_h if max_h > 0 else min_h))
    avail = max(0, h - (title_h + 4))
    items = max(1, min(max_items, avail // item_h))

    inner_x = 8
    inner_w = max(1, w - inner_x * 2)
    scroll_w = min(48, max(24, inner_w // 4))
    title_w = max(1, inner_w - scroll_w - 4)
    value_w = max(48, min(96, inner_w // 3))
    label_w = max(1, inner_w - value_w - 8)
    label_x = inner_x + 4
    value_x = inner_x + inner_w - value_w - 4

    widgets: List[Dict[str, Any]] = [
        {
            "type": "panel",
            "role": "panel",
            "x": 0,
            "y": 0,
            "width": w,
            "height": h,
            "border": True,
            "border_style": "single",
            "color_fg": NEON_FG,
            "color_bg": PANEL_BG,
            "z": 0,
        },
        {
            "type": "label",
            "role": "title",
            "x": inner_x,
            "y": 2,
            "width": title_w,
            "height": title_h,
            "text": "List",
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
            "type": "label",
            "role": "scroll",
            "x": inner_x + title_w + 4,
            "y": 2,
            "width": scroll_w,
            "height": title_h,
            "text": f"1/{items}",
            "align": "right",
            "valign": "middle",
            "text_overflow": "ellipsis",
            "max_lines": 1,
            "color_fg": TEXT_FG,
            "color_bg": PANEL_BG,
            "border": False,
            "z": 1,
        },
    ]
    for i in range(items):
        y = title_h + 4 + i * item_h
        widgets.append(
            {
                "type": "button",
                "role": f"item{i}",
                "x": inner_x,
                "y": y,
                "width": inner_w,
                "height": item_h,
                "text": "",
                "align": "left",
                "valign": "middle",
                "text_overflow": "ellipsis",
                "max_lines": 1,
                "style": "highlight" if i == 0 else "default",
                "color_fg": TEXT_FG,
                "color_bg": PANEL2_BG,
                "border": True,
                "border_style": "single",
                "z": 1,
            }
        )
        widgets.append(
            {
                "type": "label",
                "role": f"item{i}.label",
                "x": label_x,
                "y": y,
                "width": label_w,
                "height": item_h,
                "text": f"Item {i + 1}",
                "align": "left",
                "valign": "middle",
                "text_overflow": "ellipsis",
                "max_lines": 1,
                "color_fg": TEXT_FG,
                "color_bg": PANEL2_BG,
                "border": False,
                "z": 2,
            }
        )
        widgets.append(
            {
                "type": "label",
                "role": f"item{i}.value",
                "x": value_x,
                "y": y,
                "width": value_w,
                "height": item_h,
                "text": "Value",
                "align": "right",
                "valign": "middle",
                "text_overflow": "ellipsis",
                "max_lines": 1,
                "color_fg": NEON_MAGENTA,
                "color_bg": PANEL2_BG,
                "border": False,
                "z": 2,
            }
        )
    return widgets


def build_menu_list(sc: object) -> List[Dict[str, Any]]:
    sw, sh = scene_size(sc, 256, 128)
    pad = PAD_SM
    w = min(220, max(120, sw - pad * 2))
    w = max(64, min(sw, w))
    # Keep the list inside the scene (no minimum taller than the screen).
    max_h = max(0, sh - pad * 2)
    title_h = 16
    item_h = 16
    # Fit as many items as possible (up to 6) without overflowing the panel.
    max_items = 6
    min_h = title_h + 4 + item_h + 4
    h = max(min_h, min(120, max_h if max_h > 0 else min_h))
    avail = max(0, h - (title_h + 4))
    items = max(1, min(max_items, avail // item_h))
    inner_w = max(1, w - 16)
    scroll_w = min(48, max(24, inner_w // 4))
    title_w = max(1, inner_w - scroll_w - 4)
    widgets: List[Dict[str, Any]] = [
        {
            "type": "panel",
            "role": "panel",
            "x": 0,
            "y": 0,
            "width": w,
            "height": h,
            "border": True,
            "border_style": "single",
            "color_fg": NEON_FG,
            "color_bg": PANEL_BG,
            "z": 0,
        },
        {
            "type": "label",
            "role": "title",
            "x": 8,
            "y": 2,
            "width": title_w,
            "height": title_h,
            "text": "Menu",
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
            "type": "label",
            "role": "scroll",
            "x": 8 + title_w + 4,
            "y": 2,
            "width": scroll_w,
            "height": title_h,
            "text": f"1/{items}",
            "align": "right",
            "valign": "middle",
            "text_overflow": "ellipsis",
            "max_lines": 1,
            "color_fg": TEXT_FG,
            "color_bg": PANEL_BG,
            "border": False,
            "z": 1,
        },
    ]
    for i in range(items):
        widgets.append(
            {
                "type": "button",
                "role": f"item{i}",
                "x": 8,
                "y": title_h + 4 + i * item_h,
                "width": inner_w,
                "height": item_h,
                "text": f"Item {i + 1}",
                "align": "left",
                "valign": "middle",
                "text_overflow": "ellipsis",
                "max_lines": 1,
                "style": "highlight" if i == 0 else "default",
                "color_fg": TEXT_FG,
                "color_bg": PANEL2_BG,
                "border": True,
                "border_style": "single",
                "z": 1,
            }
        )
    return widgets


def build_list_item(sc: object) -> List[Dict[str, Any]]:
    sw = scene_width(sc, 256)
    row_w = max(64, min(240, max(1, sw) - 8))
    pad = PAD_SM
    value_w = max(48, min(96, row_w // 3))
    value_x = max(pad, row_w - pad - value_w)
    return [
        {
            "type": "button",
            "role": "item",
            "x": 0,
            "y": 0,
            "width": row_w,
            "height": LABEL_H,
            "text": "Label",
            "align": "left",
            "valign": "middle",
            "text_overflow": "ellipsis",
            "max_lines": 1,
            "color_fg": TEXT_FG,
            "color_bg": PANEL2_BG,
            "border": True,
            "border_style": "single",
            "z": 0,
        },
        {
            "type": "label",
            "role": "value",
            "x": value_x,
            "y": 0,
            "width": value_w,
            "height": LABEL_H,
            "text": "Value",
            "align": "right",
            "valign": "middle",
            "text_overflow": "ellipsis",
            "max_lines": 1,
            "color_fg": NEON_MAGENTA,
            "color_bg": PANEL2_BG,
            "border": False,
            "z": 1,
        },
    ]
