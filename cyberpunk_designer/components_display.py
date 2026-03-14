"""Display & overlay component blueprints: card, toast, notification, modal,
dialog, dialog_confirm, status_bar, dashboard."""

from __future__ import annotations

from typing import Any, Dict, List

from .components_shared import (
    LABEL_H,
    NEON_FG,
    NEON_MAGENTA,
    PAD,
    PAD_SM,
    PANEL2_BG,
    PANEL_BG,
    TEXT_FG,
    scene_size,
    scene_width,
)


def build_card(sc: object) -> List[Dict[str, Any]]:
    return [
        {
            "type": "panel",
            "role": "panel",
            "x": 0,
            "y": 0,
            "width": 192,
            "height": 88,
            "border": True,
            "border_style": "rounded",
            "color_fg": NEON_FG,
            "color_bg": PANEL_BG,
            "z": 0,
        },
        {
            "type": "label",
            "role": "title",
            "x": PAD,
            "y": 10,
            "width": 160,
            "height": LABEL_H,
            "text": "Card Title",
            "style": "bold",
            "text_overflow": "ellipsis",
            "max_lines": 1,
            "color_fg": NEON_MAGENTA,
            "color_bg": PANEL_BG,
            "border": False,
            "z": 1,
        },
        {
            "type": "label",
            "role": "value",
            "x": PAD,
            "y": 30,
            "width": 160,
            "height": 14,
            "text": "Value: 123",
            "text_overflow": "ellipsis",
            "max_lines": 1,
            "color_fg": TEXT_FG,
            "color_bg": PANEL_BG,
            "border": False,
            "z": 1,
        },
        {
            "type": "progressbar",
            "role": "progress",
            "x": PAD,
            "y": 56,
            "width": 168,
            "height": 14,
            "value": 65,
            "min_value": 0,
            "max_value": 100,
            "text": "Progress",
            "text_overflow": "ellipsis",
            "max_lines": 1,
            "color_fg": NEON_FG,
            "color_bg": PANEL2_BG,
            "border": True,
            "border_style": "single",
            "z": 1,
        },
    ]


def build_toast(sc: object) -> List[Dict[str, Any]]:
    sw, sh = scene_size(sc, 256, 128)
    panel_w = max(64, min(240, max(1, sw)))
    panel_h = max(32, min(44, max(1, sh)))
    pad_x = 10
    gap_x = 6
    btn_h = min(20, max(16, panel_h - 2))
    btn_w = min(64, max(40, panel_w // 5))
    btn_x = max(0, panel_w - pad_x - btn_w)
    btn_y = max(0, (panel_h - btn_h) // 2)
    msg_h = min(16, max(12, panel_h - 2))
    msg_y = max(0, (panel_h - msg_h) // 2)
    msg_x = pad_x
    msg_w = max(1, btn_x - gap_x - msg_x)
    return [
        {
            "type": "panel",
            "role": "panel",
            "x": 0,
            "y": 0,
            "width": panel_w,
            "height": panel_h,
            "border": True,
            "border_style": "single",
            "color_fg": NEON_FG,
            "color_bg": PANEL2_BG,
            "z": 0,
        },
        {
            "type": "label",
            "role": "message",
            "x": msg_x,
            "y": msg_y,
            "width": msg_w,
            "height": msg_h,
            "text": "Toast: saved.",
            "align": "left",
            "valign": "middle",
            "text_overflow": "ellipsis",
            "max_lines": 1,
            "color_fg": TEXT_FG,
            "color_bg": PANEL2_BG,
            "border": False,
            "z": 1,
        },
        {
            "type": "button",
            "role": "button",
            "x": btn_x,
            "y": btn_y,
            "width": btn_w,
            "height": btn_h,
            "text": "OK",
            "style": "bold",
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
    ]


def build_notification(sc: object) -> List[Dict[str, Any]]:
    sw, sh = scene_size(sc, 256, 128)
    panel_w = max(64, min(sw, 260))
    panel_h = max(40, min(sh, 72))
    content_w = max(1, panel_w - 24)
    button_y = min(50, max(0, panel_h - 22))
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
            "color_fg": NEON_FG,
            "color_bg": PANEL2_BG,
            "z": 0,
        },
        {
            "type": "label",
            "role": "title",
            "x": PAD,
            "y": 10,
            "width": content_w,
            "height": LABEL_H,
            "text": "Notification",
            "style": "bold",
            "align": "left",
            "valign": "middle",
            "text_overflow": "ellipsis",
            "max_lines": 1,
            "color_fg": NEON_MAGENTA,
            "color_bg": PANEL2_BG,
            "border": False,
            "z": 1,
        },
        {
            "type": "label",
            "role": "message",
            "x": PAD,
            "y": 30,
            "width": content_w,
            "height": 18,
            "text": "Something happened.",
            "align": "left",
            "valign": "middle",
            "text_overflow": "ellipsis",
            "max_lines": 1,
            "color_fg": TEXT_FG,
            "color_bg": PANEL2_BG,
            "border": False,
            "z": 1,
        },
        {
            "type": "button",
            "role": "button",
            "x": PAD,
            "y": button_y,
            "width": 70,
            "height": 18,
            "text": "Open",
            "align": "center",
            "valign": "middle",
            "text_overflow": "ellipsis",
            "max_lines": 1,
            "color_fg": NEON_FG,
            "color_bg": PANEL_BG,
            "border": True,
            "border_style": "rounded",
            "z": 1,
        },
    ]


def build_modal(sc: object) -> List[Dict[str, Any]]:
    sw, sh = scene_size(sc, 320, 240)
    dialog_w = max(160, min(360, int(sw * 0.7)))
    dialog_h = max(120, min(220, int(sh * 0.55)))
    dialog_x = max(0, (sw - dialog_w) // 2)
    dialog_y = max(0, (sh - dialog_h) // 2)
    return [
        {
            "type": "panel",
            "role": "overlay",
            "x": 0,
            "y": 0,
            "width": sw,
            "height": sh,
            "border": False,
            "color_fg": NEON_FG,
            "color_bg": "#000000",
            "locked": True,
            "z": 90,
        },
        {
            "type": "panel",
            "role": "dialog",
            "x": dialog_x,
            "y": dialog_y,
            "width": dialog_w,
            "height": dialog_h,
            "border": True,
            "border_style": "double",
            "color_fg": NEON_MAGENTA,
            "color_bg": PANEL_BG,
            "z": 100,
        },
        {
            "type": "label",
            "role": "title",
            "x": dialog_x + 14,
            "y": dialog_y + 16,
            "width": max(1, dialog_w - 28),
            "height": 18,
            "text": "Modal title",
            "style": "bold",
            "align": "left",
            "valign": "middle",
            "text_overflow": "ellipsis",
            "max_lines": 1,
            "color_fg": NEON_MAGENTA,
            "color_bg": PANEL_BG,
            "border": False,
            "z": 101,
        },
        {
            "type": "label",
            "role": "message",
            "x": dialog_x + 14,
            "y": dialog_y + 40,
            "width": max(1, dialog_w - 28),
            "height": 40,
            "text": "Message goes here.",
            "align": "left",
            "valign": "top",
            "text_overflow": "wrap",
            "max_lines": 3,
            "color_fg": TEXT_FG,
            "color_bg": PANEL_BG,
            "border": False,
            "z": 101,
        },
        {
            "type": "button",
            "role": "cancel",
            "x": dialog_x + 14,
            "y": dialog_y + dialog_h - 30,
            "width": 72,
            "height": 20,
            "text": "Cancel",
            "align": "center",
            "valign": "middle",
            "text_overflow": "ellipsis",
            "max_lines": 1,
            "color_fg": NEON_FG,
            "color_bg": PANEL2_BG,
            "border": True,
            "border_style": "rounded",
            "z": 101,
        },
        {
            "type": "button",
            "role": "ok",
            "x": dialog_x + dialog_w - 86,
            "y": dialog_y + dialog_h - 30,
            "width": 72,
            "height": 20,
            "text": "OK",
            "style": "bold",
            "align": "center",
            "valign": "middle",
            "text_overflow": "ellipsis",
            "max_lines": 1,
            "color_fg": NEON_MAGENTA,
            "color_bg": PANEL2_BG,
            "border": True,
            "border_style": "rounded",
            "z": 101,
        },
    ]


def build_dialog_confirm(sc: object) -> List[Dict[str, Any]]:
    sw, sh = scene_size(sc, 256, 128)

    target_w = max(160, min(280, sw - 16))
    target_h = max(96, min(140, sh - 16))
    dialog_w = max(64, min(sw, target_w))
    dialog_h = max(64, min(sh, target_h))

    pad_x = 12
    pad_y = 12
    title_h = 16
    btn_h = 20
    gap_x = 12
    gap_y = 8

    content_w = max(1, dialog_w - pad_x * 2)
    title_y = pad_y
    msg_y = title_y + title_h + gap_y
    btn_y = max(0, dialog_h - (pad_y + btn_h))
    msg_h = max(16, btn_y - msg_y - gap_y)

    btn_w = max(48, (dialog_w - pad_x * 2 - gap_x) // 2)
    cancel_x = pad_x
    confirm_x = max(pad_x, dialog_w - pad_x - btn_w)

    return [
        {
            "type": "panel",
            "role": "dialog",
            "x": 0,
            "y": 0,
            "width": dialog_w,
            "height": dialog_h,
            "border": True,
            "border_style": "double",
            "color_fg": NEON_MAGENTA,
            "color_bg": PANEL_BG,
            "z": 0,
        },
        {
            "type": "label",
            "role": "title",
            "x": pad_x,
            "y": title_y,
            "width": content_w,
            "height": title_h,
            "text": "Confirm action",
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
            "role": "message",
            "x": pad_x,
            "y": msg_y,
            "width": content_w,
            "height": msg_h,
            "text": "Are you sure?",
            "align": "left",
            "valign": "top",
            "text_overflow": "wrap",
            "max_lines": 4,
            "color_fg": TEXT_FG,
            "color_bg": PANEL_BG,
            "border": False,
            "z": 1,
        },
        {
            "type": "button",
            "role": "cancel",
            "x": cancel_x,
            "y": btn_y,
            "width": btn_w,
            "height": btn_h,
            "text": "Cancel",
            "align": "center",
            "valign": "middle",
            "text_overflow": "ellipsis",
            "max_lines": 1,
            "color_fg": NEON_FG,
            "color_bg": PANEL2_BG,
            "border": True,
            "border_style": "rounded",
            "z": 1,
        },
        {
            "type": "button",
            "role": "confirm",
            "x": confirm_x,
            "y": btn_y,
            "width": btn_w,
            "height": btn_h,
            "text": "Confirm",
            "style": "bold",
            "align": "center",
            "valign": "middle",
            "text_overflow": "ellipsis",
            "max_lines": 1,
            "color_fg": NEON_MAGENTA,
            "color_bg": PANEL2_BG,
            "border": True,
            "border_style": "rounded",
            "z": 1,
        },
    ]


def build_dialog(sc: object) -> List[Dict[str, Any]]:
    sw, sh = scene_size(sc, 256, 128)
    dialog_w = max(64, min(220, max(1, sw) - 8))
    dialog_h = max(64, min(104, max(1, sh) - 8))
    pad_x = 12
    pad_y = 10
    title_h = 16
    btn_h = 20
    gap_x = 12
    gap_y = 4
    content_w = max(1, dialog_w - pad_x * 2)
    title_y = pad_y
    msg_y = title_y + title_h + gap_y
    btn_y = max(0, dialog_h - (pad_y + btn_h))
    msg_h = max(16, btn_y - msg_y - gap_y)
    btn_w = max(48, (dialog_w - pad_x * 2 - gap_x) // 2)
    cancel_x = pad_x
    ok_x = max(pad_x, dialog_w - pad_x - btn_w)
    return [
        {
            "type": "panel",
            "role": "dialog",
            "x": 0,
            "y": 0,
            "width": dialog_w,
            "height": dialog_h,
            "border": True,
            "border_style": "double",
            "color_fg": NEON_MAGENTA,
            "color_bg": PANEL_BG,
            "z": 0,
        },
        {
            "type": "label",
            "role": "title",
            "x": pad_x,
            "y": title_y,
            "width": content_w,
            "height": title_h,
            "text": "Dialog",
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
            "role": "message",
            "x": pad_x,
            "y": msg_y,
            "width": content_w,
            "height": msg_h,
            "text": "Message goes here.",
            "align": "left",
            "valign": "top",
            "text_overflow": "wrap",
            "max_lines": 3,
            "color_fg": TEXT_FG,
            "color_bg": PANEL_BG,
            "border": False,
            "z": 1,
        },
        {
            "type": "button",
            "role": "cancel",
            "x": cancel_x,
            "y": btn_y,
            "width": btn_w,
            "height": btn_h,
            "text": "Cancel",
            "align": "center",
            "valign": "middle",
            "color_fg": NEON_FG,
            "color_bg": PANEL2_BG,
            "border": True,
            "border_style": "rounded",
            "z": 1,
        },
        {
            "type": "button",
            "role": "ok",
            "x": ok_x,
            "y": btn_y,
            "width": btn_w,
            "height": btn_h,
            "text": "OK",
            "style": "bold",
            "align": "center",
            "valign": "middle",
            "color_fg": NEON_MAGENTA,
            "color_bg": PANEL2_BG,
            "border": True,
            "border_style": "rounded",
            "z": 1,
        },
    ]


def build_status_bar(sc: object) -> List[Dict[str, Any]]:
    sw = scene_width(sc, 256)
    bar_h = 16
    return [
        {
            "type": "panel",
            "role": "bar",
            "x": 0,
            "y": 0,
            "width": sw,
            "height": bar_h,
            "border": True,
            "border_style": "single",
            "color_fg": NEON_FG,
            "color_bg": "#000000",
            "z": 0,
        },
        {
            "type": "label",
            "role": "left",
            "x": 6,
            "y": 0,
            "width": max(1, int(sw * 0.65) - 6),
            "height": bar_h,
            "text": "ESP32OS",
            "style": "bold",
            "align": "left",
            "valign": "middle",
            "text_overflow": "ellipsis",
            "max_lines": 1,
            "color_fg": NEON_MAGENTA,
            "color_bg": "#000000",
            "border": False,
            "z": 1,
        },
        {
            "type": "label",
            "role": "right",
            "x": int(sw * 0.65),
            "y": 0,
            "width": max(1, sw - int(sw * 0.65) - 6),
            "height": bar_h,
            "text": "WiFi  12:34",
            "align": "right",
            "valign": "middle",
            "text_overflow": "ellipsis",
            "max_lines": 1,
            "color_fg": TEXT_FG,
            "color_bg": "#000000",
            "border": False,
            "z": 1,
        },
    ]


def build_dashboard_256x128(sc: object) -> List[Dict[str, Any]]:
    sw, sh = scene_size(sc, 256, 128)

    pad = PAD_SM
    gap = PAD_SM
    top_h = 20
    bottom_h = 20
    col_w = max(40, (sw - pad * 2 - gap * 2) // 3)
    col_h = top_h

    main_y = pad + top_h + gap
    main_h = max(32, sh - main_y - bottom_h - pad)
    bottom_y = sh - bottom_h - pad

    def metric_block(i: int, title: str, value: int) -> List[Dict[str, Any]]:
        x = pad + i * (col_w + gap)
        return [
            {
                "type": "panel",
                "role": f"metric{i}.panel",
                "x": x,
                "y": pad,
                "width": col_w,
                "height": col_h,
                "border": True,
                "border_style": "single",
                "color_fg": NEON_FG,
                "color_bg": PANEL2_BG,
                "z": 1,
            },
            {
                "type": "label",
                "role": f"metric{i}.title",
                "x": x + 4,
                "y": pad + 2,
                "width": max(1, col_w - 8),
                "height": 12,
                "text": title,
                "style": "bold",
                "align": "left",
                "valign": "middle",
                "text_overflow": "ellipsis",
                "max_lines": 1,
                "color_fg": NEON_MAGENTA,
                "color_bg": PANEL2_BG,
                "border": False,
                "z": 2,
            },
            {
                "type": "progressbar",
                "role": f"metric{i}.progress",
                "x": x + 4,
                "y": pad + 12,
                "width": max(1, col_w - 8),
                "height": 6,
                "value": value,
                "min_value": 0,
                "max_value": 100,
                "text": "",
                "color_fg": NEON_FG,
                "color_bg": PANEL2_BG,
                "border": True,
                "border_style": "single",
                "z": 2,
            },
        ]

    widgets: List[Dict[str, Any]] = [
        {
            "type": "panel",
            "role": "root",
            "x": 0,
            "y": 0,
            "width": sw,
            "height": sh,
            "border": False,
            "color_fg": NEON_FG,
            "color_bg": "#000000",
            "z": 0,
        },
        *metric_block(0, "CPU", 35),
        *metric_block(1, "MEM", 62),
        *metric_block(2, "NET", 18),
        {
            "type": "panel",
            "role": "main",
            "x": pad,
            "y": main_y,
            "width": max(1, sw - pad * 2),
            "height": main_h,
            "border": True,
            "border_style": "single",
            "color_fg": NEON_FG,
            "color_bg": PANEL_BG,
            "z": 3,
        },
        {
            "type": "label",
            "role": "main.text",
            "x": pad + 6,
            "y": main_y + 6,
            "width": max(1, sw - pad * 2 - 12),
            "height": 14,
            "text": "Dashboard / Menu content",
            "align": "left",
            "valign": "top",
            "text_overflow": "ellipsis",
            "max_lines": 1,
            "color_fg": TEXT_FG,
            "color_bg": PANEL_BG,
            "border": False,
            "z": 4,
        },
        {
            "type": "panel",
            "role": "footer",
            "x": pad,
            "y": bottom_y,
            "width": max(1, sw - pad * 2),
            "height": bottom_h,
            "border": True,
            "border_style": "single",
            "color_fg": NEON_FG,
            "color_bg": PANEL2_BG,
            "z": 3,
        },
        {
            "type": "label",
            "role": "footer.hint",
            "x": pad + 6,
            "y": bottom_y + 4,
            "width": max(1, sw - pad * 2 - 12),
            "height": 14,
            "text": "A:Select  B:Back  ENC:Scroll",
            "align": "left",
            "valign": "middle",
            "text_overflow": "ellipsis",
            "max_lines": 1,
            "color_fg": TEXT_FG,
            "color_bg": PANEL2_BG,
            "border": False,
            "z": 4,
        },
    ]
    return widgets
