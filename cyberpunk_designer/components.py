from __future__ import annotations

from typing import Dict, List


def component_blueprints(name: str, sc) -> List[Dict[str, object]]:
    """Return a list of widget dicts for a named component."""
    name = str(name or "").strip().lower()
    if name == "menu":
        name = "menu_list"
    # Neutral defaults (device-friendly; avoid neon/cyberpunk look).
    neon_fg = "#f5f5f5"
    neon_magenta = "#e0e0e0"
    panel_bg = "#101010"
    panel2_bg = "#080808"
    text_fg = "#f0f0f0"

    if name == "card":
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
                "color_fg": neon_fg,
                "color_bg": panel_bg,
                "z": 0,
            },
            {
                "type": "label",
                "role": "title",
                "x": 12,
                "y": 10,
                "width": 160,
                "height": 16,
                "text": "Card Title",
                "style": "bold",
                "text_overflow": "ellipsis",
                "max_lines": 1,
                "color_fg": neon_magenta,
                "color_bg": panel_bg,
                "border": False,
                "z": 1,
            },
            {
                "type": "label",
                "role": "value",
                "x": 12,
                "y": 30,
                "width": 160,
                "height": 14,
                "text": "Value: 123",
                "text_overflow": "ellipsis",
                "max_lines": 1,
                "color_fg": text_fg,
                "color_bg": panel_bg,
                "border": False,
                "z": 1,
            },
            {
                "type": "progressbar",
                "role": "progress",
                "x": 12,
                "y": 56,
                "width": 168,
                "height": 14,
                "value": 65,
                "min_value": 0,
                "max_value": 100,
                "text": "Progress",
                "text_overflow": "ellipsis",
                "max_lines": 1,
                "color_fg": neon_fg,
                "color_bg": panel2_bg,
                "border": True,
                "border_style": "single",
                "z": 1,
            },
        ]

    if name == "toast":
        try:
            sw = int(sc.width)
            sh = int(sc.height)
        except Exception:
            sw, sh = 256, 128
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
                "color_fg": neon_fg,
                "color_bg": panel2_bg,
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
                "color_fg": text_fg,
                "color_bg": panel2_bg,
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
                "color_fg": neon_magenta,
                "color_bg": panel_bg,
                "border": True,
                "border_style": "rounded",
                "z": 1,
            },
        ]

    if name == "modal":
        try:
            sw = int(sc.width)
            sh = int(sc.height)
        except Exception:
            sw, sh = 320, 240
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
                "color_fg": neon_fg,
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
                "color_fg": neon_magenta,
                "color_bg": panel_bg,
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
                "color_fg": neon_magenta,
                "color_bg": panel_bg,
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
                "color_fg": text_fg,
                "color_bg": panel_bg,
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
                "color_fg": neon_fg,
                "color_bg": panel2_bg,
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
                "color_fg": neon_magenta,
                "color_bg": panel2_bg,
                "border": True,
                "border_style": "rounded",
                "z": 101,
            },
        ]

    if name == "dialog_confirm":
        try:
            sw = int(sc.width)
            sh = int(sc.height)
        except Exception:
            sw, sh = 256, 128

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
                "color_fg": neon_magenta,
                "color_bg": panel_bg,
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
                "color_fg": neon_magenta,
                "color_bg": panel_bg,
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
                "color_fg": text_fg,
                "color_bg": panel_bg,
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
                "color_fg": neon_fg,
                "color_bg": panel2_bg,
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
                "color_fg": neon_magenta,
                "color_bg": panel2_bg,
                "border": True,
                "border_style": "rounded",
                "z": 1,
            },
        ]

    if name == "notification":
        try:
            sw = int(sc.width)
            sh = int(sc.height)
        except Exception:
            sw, sh = 256, 128
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
                "color_fg": neon_fg,
                "color_bg": panel2_bg,
                "z": 0,
            },
            {
                "type": "label",
                "role": "title",
                "x": 12,
                "y": 10,
                "width": content_w,
                "height": 16,
                "text": "Notification",
                "style": "bold",
                "align": "left",
                "valign": "middle",
                "text_overflow": "ellipsis",
                "max_lines": 1,
                "color_fg": neon_magenta,
                "color_bg": panel2_bg,
                "border": False,
                "z": 1,
            },
            {
                "type": "label",
                "role": "message",
                "x": 12,
                "y": 30,
                "width": content_w,
                "height": 18,
                "text": "Something happened.",
                "align": "left",
                "valign": "middle",
                "text_overflow": "ellipsis",
                "max_lines": 1,
                "color_fg": text_fg,
                "color_bg": panel2_bg,
                "border": False,
                "z": 1,
            },
            {
                "type": "button",
                "role": "button",
                "x": 12,
                "y": button_y,
                "width": 70,
                "height": 18,
                "text": "Open",
                "align": "center",
                "valign": "middle",
                "text_overflow": "ellipsis",
                "max_lines": 1,
                "color_fg": neon_fg,
                "color_bg": panel_bg,
                "border": True,
                "border_style": "rounded",
                "z": 1,
            },
        ]

    if name == "chart_bar":
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
                "color_fg": neon_fg,
                "color_bg": panel_bg,
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
                "color_fg": neon_magenta,
                "color_bg": panel2_bg,
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
                "height": 16,
                "text": "Chart title",
                "color_fg": text_fg,
                "color_bg": panel_bg,
                "border": False,
                "z": 1,
            },
        ]

    if name == "chart_line":
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
                "color_fg": neon_fg,
                "color_bg": panel_bg,
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
                "color_fg": neon_fg,
                "color_bg": panel2_bg,
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
                "height": 16,
                "text": "Chart title",
                "color_fg": text_fg,
                "color_bg": panel_bg,
                "border": False,
                "z": 1,
            },
        ]

    if name == "gauge_hud":
        try:
            sw = int(sc.width)
            sh = int(sc.height)
        except Exception:
            sw, sh = 256, 128
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
                "color_fg": neon_magenta,
                "color_bg": panel_bg,
                "z": 0,
            },
            {
                "type": "label",
                "role": "title",
                "x": 12,
                "y": 12,
                "width": content_w,
                "height": 16,
                "text": "HUD",
                "style": "bold",
                "align": "left",
                "valign": "middle",
                "text_overflow": "ellipsis",
                "max_lines": 1,
                "color_fg": neon_magenta,
                "color_bg": panel_bg,
                "border": False,
                "z": 1,
            },
            {
                "type": "gauge",
                "role": "gauge",
                "x": 12,
                "y": 36,
                "width": content_w,
                "height": 44,
                "text": "RPM",
                "value": 42,
                "min_value": 0,
                "max_value": 100,
                "color_fg": neon_fg,
                "color_bg": panel2_bg,
                "border": True,
                "border_style": "rounded",
                "z": 1,
            },
            {
                "type": "label",
                "role": "line1",
                "x": 12,
                "y": 88,
                "width": content_w,
                "height": 16,
                "text": "Speed: 88",
                "align": "left",
                "valign": "middle",
                "text_overflow": "ellipsis",
                "max_lines": 1,
                "color_fg": text_fg,
                "color_bg": panel_bg,
                "border": False,
                "z": 1,
            },
            {
                "type": "label",
                "role": "line2",
                "x": 12,
                "y": 108,
                "width": content_w,
                "height": 16,
                "text": "Temp: 42C",
                "align": "left",
                "valign": "middle",
                "text_overflow": "ellipsis",
                "max_lines": 1,
                "color_fg": text_fg,
                "color_bg": panel_bg,
                "border": False,
                "z": 1,
            },
        ]

    if name == "dashboard_256x128":
        try:
            sw = int(sc.width)
            sh = int(sc.height)
        except Exception:
            sw, sh = 256, 128

        pad = 4
        gap = 4
        top_h = 20
        bottom_h = 20
        col_w = max(40, (sw - pad * 2 - gap * 2) // 3)
        col_h = top_h

        main_y = pad + top_h + gap
        main_h = max(32, sh - main_y - bottom_h - pad)
        bottom_y = sh - bottom_h - pad

        def metric_block(i: int, title: str, value: int):
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
                    "color_fg": neon_fg,
                    "color_bg": panel2_bg,
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
                    "color_fg": neon_magenta,
                    "color_bg": panel2_bg,
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
                    "color_fg": neon_fg,
                    "color_bg": panel2_bg,
                    "border": True,
                    "border_style": "single",
                    "z": 2,
                },
            ]

        widgets: List[Dict[str, object]] = [
            {
                "type": "panel",
                "role": "root",
                "x": 0,
                "y": 0,
                "width": sw,
                "height": sh,
                "border": False,
                "color_fg": neon_fg,
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
                "color_fg": neon_fg,
                "color_bg": panel_bg,
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
                "color_fg": text_fg,
                "color_bg": panel_bg,
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
                "color_fg": neon_fg,
                "color_bg": panel2_bg,
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
                "color_fg": text_fg,
                "color_bg": panel2_bg,
                "border": False,
                "z": 4,
            },
        ]
        return widgets

    if name == "status_bar":
        try:
            sw = int(sc.width)
        except Exception:
            sw = 256
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
                "color_fg": neon_fg,
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
                "color_fg": neon_magenta,
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
                "color_fg": text_fg,
                "color_bg": "#000000",
                "border": False,
                "z": 1,
            },
        ]

    if name == "tabs":
        try:
            sw = int(sc.width)
            sh = int(sc.height)
        except Exception:
            sw, sh = 256, 128
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
                "color_fg": neon_fg,
                "color_bg": panel2_bg,
                "z": 0,
            },
            {
                "type": "button",
                "role": "tab1",
                "x": 4,
                "y": 4,
                "width": tab_w,
                "height": 16,
                "text": "Tab 1",
                "style": "bold highlight",
                "align": "center",
                "valign": "middle",
                "text_overflow": "ellipsis",
                "max_lines": 1,
                "color_fg": neon_magenta,
                "color_bg": panel_bg,
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
                "height": 16,
                "text": "Tab 2",
                "align": "center",
                "valign": "middle",
                "text_overflow": "ellipsis",
                "max_lines": 1,
                "color_fg": text_fg,
                "color_bg": panel_bg,
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
                "height": 16,
                "text": "Tab 3",
                "align": "center",
                "valign": "middle",
                "text_overflow": "ellipsis",
                "max_lines": 1,
                "color_fg": text_fg,
                "color_bg": panel_bg,
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
                "color_fg": neon_fg,
                "color_bg": panel_bg,
                "z": 0,
            },
            {
                "type": "label",
                "role": "content.title",
                "x": 8,
                "y": tabbar_h + 6,
                "width": max(1, sw - 16),
                "height": 16,
                "text": "Tab content",
                "align": "left",
                "valign": "top",
                "text_overflow": "ellipsis",
                "max_lines": 1,
                "color_fg": text_fg,
                "color_bg": panel_bg,
                "border": False,
                "z": 1,
            },
        ]

    if name == "list":
        try:
            sw = int(sc.width)
            sh = int(sc.height)
        except Exception:
            sw, sh = 256, 128
        pad = 4
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

        widgets: List[Dict[str, object]] = [
            {
                "type": "panel",
                "role": "panel",
                "x": 0,
                "y": 0,
                "width": w,
                "height": h,
                "border": True,
                "border_style": "single",
                "color_fg": neon_fg,
                "color_bg": panel_bg,
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
                "color_fg": neon_magenta,
                "color_bg": panel_bg,
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
                "color_fg": text_fg,
                "color_bg": panel_bg,
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
                    "color_fg": text_fg,
                    "color_bg": panel2_bg,
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
                    "color_fg": text_fg,
                    "color_bg": panel2_bg,
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
                    "color_fg": neon_magenta,
                    "color_bg": panel2_bg,
                    "border": False,
                    "z": 2,
                }
            )
        return widgets

    if name == "menu_list":
        try:
            sw = int(sc.width)
            sh = int(sc.height)
        except Exception:
            sw, sh = 256, 128
        pad = 4
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
        widgets: List[Dict[str, object]] = [
            {
                "type": "panel",
                "role": "panel",
                "x": 0,
                "y": 0,
                "width": w,
                "height": h,
                "border": True,
                "border_style": "single",
                "color_fg": neon_fg,
                "color_bg": panel_bg,
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
                "color_fg": neon_magenta,
                "color_bg": panel_bg,
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
                "color_fg": text_fg,
                "color_bg": panel_bg,
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
                    "color_fg": text_fg,
                    "color_bg": panel2_bg,
                    "border": True,
                    "border_style": "single",
                    "z": 1,
                }
            )
        return widgets

    if name == "list_item":
        try:
            sw = int(sc.width)
        except Exception:
            sw = 256
        row_w = max(64, min(240, max(1, sw) - 8))
        pad = 4
        value_w = max(48, min(96, row_w // 3))
        value_x = max(pad, row_w - pad - value_w)
        return [
            {
                "type": "button",
                "role": "item",
                "x": 0,
                "y": 0,
                "width": row_w,
                "height": 16,
                "text": "Label",
                "align": "left",
                "valign": "middle",
                "text_overflow": "ellipsis",
                "max_lines": 1,
                "color_fg": text_fg,
                "color_bg": panel2_bg,
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
                "height": 16,
                "text": "Value",
                "align": "right",
                "valign": "middle",
                "text_overflow": "ellipsis",
                "max_lines": 1,
                "color_fg": neon_magenta,
                "color_bg": panel2_bg,
                "border": False,
                "z": 1,
            },
        ]

    if name == "setting_int":
        try:
            sw = int(sc.width)
        except Exception:
            sw = 256
        row_w = max(64, min(240, max(1, sw) - 8))
        return [
            {
                "type": "button",
                "role": "item",
                "x": 0,
                "y": 0,
                "width": row_w,
                "height": 16,
                "text": "Setting",
                "align": "left",
                "valign": "middle",
                "text_overflow": "ellipsis",
                "max_lines": 1,
                "runtime": "bind=key;kind=int;min=0;max=100;step=1",
                "color_fg": text_fg,
                "color_bg": panel2_bg,
                "border": True,
                "border_style": "single",
                "z": 0,
            },
        ]

    if name == "setting_bool":
        try:
            sw = int(sc.width)
        except Exception:
            sw = 256
        row_w = max(64, min(240, max(1, sw) - 8))
        return [
            {
                "type": "button",
                "role": "item",
                "x": 0,
                "y": 0,
                "width": row_w,
                "height": 16,
                "text": "Setting",
                "align": "left",
                "valign": "middle",
                "text_overflow": "ellipsis",
                "max_lines": 1,
                "runtime": "bind=key;kind=bool;values=off|on",
                "color_fg": text_fg,
                "color_bg": panel2_bg,
                "border": True,
                "border_style": "single",
                "z": 0,
            },
        ]

    if name == "setting_enum":
        try:
            sw = int(sc.width)
        except Exception:
            sw = 256
        row_w = max(64, min(240, max(1, sw) - 8))
        return [
            {
                "type": "button",
                "role": "item",
                "x": 0,
                "y": 0,
                "width": row_w,
                "height": 16,
                "text": "Setting",
                "align": "left",
                "valign": "middle",
                "text_overflow": "ellipsis",
                "max_lines": 1,
                "runtime": "bind=key;kind=enum;values=A|B|C",
                "color_fg": text_fg,
                "color_bg": panel2_bg,
                "border": True,
                "border_style": "single",
                "z": 0,
            },
        ]

    if name == "dialog":
        try:
            sw = int(sc.width)
            sh = int(sc.height)
        except Exception:
            sw, sh = 256, 128
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
                "color_fg": neon_magenta,
                "color_bg": panel_bg,
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
                "color_fg": neon_magenta,
                "color_bg": panel_bg,
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
                "color_fg": text_fg,
                "color_bg": panel_bg,
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
                "color_fg": neon_fg,
                "color_bg": panel2_bg,
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
                "color_fg": neon_magenta,
                "color_bg": panel2_bg,
                "border": True,
                "border_style": "rounded",
                "z": 1,
            },
        ]

    return []
