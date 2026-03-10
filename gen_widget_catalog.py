#!/usr/bin/env python3
"""Generate widget_catalog.json — showcases ALL 12 widget types.

Multi-purpose demo: not tied to any specific application (RC, weather, etc.).
Each scene demonstrates a subset of widgets with various states and styles.

Target: 256×128, 4-bit grayscale OLED (SSD1363).
"""

import json
from pathlib import Path

W, H = 256, 128
CHAR_W = 6
PAD = 2
LH = 12  # label/button height


def text_w(n):
    return n * CHAR_W + PAD * 2


_next_id = 0


def _wid(prefix):
    global _next_id
    _next_id += 1
    return f"{prefix}.{_next_id}"


def widget(
    wtype,
    x,
    y,
    w,
    h,
    text="",
    *,
    wid=None,
    style="default",
    fg="#f0f0f0",
    bg="black",
    border=False,
    border_style="none",
    align="left",
    valign="middle",
    value=0,
    min_value=0,
    max_value=100,
    checked=False,
    enabled=True,
    visible=True,
    runtime="",
    data_points=None,
    icon_char="",
    text_overflow="ellipsis",
):
    return {
        "type": wtype,
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "text": text,
        "style": style,
        "color_fg": fg,
        "color_bg": bg,
        "border": border,
        "border_style": border_style,
        "align": align,
        "valign": valign,
        "text_overflow": text_overflow,
        "max_lines": 1 if wtype != "panel" else None,
        "value": value,
        "min_value": min_value,
        "max_value": max_value,
        "checked": checked,
        "enabled": enabled,
        "visible": visible,
        "icon_char": icon_char,
        "data_points": data_points or [],
        "z_index": 0,
        "padding_x": 1,
        "padding_y": 0,
        "margin_x": 0,
        "margin_y": 0,
        "constraints": {},
        "responsive_rules": [],
        "animations": [],
        "runtime": runtime,
        "locked": False,
        "theme_fg_role": "",
        "theme_bg_role": "",
        "state": "default",
        "state_overrides": {},
        "bg_color": None,
        "text_color": None,
        "color": None,
        "font_size": None,
        "bold": False,
        "corner_radius": None,
        "border_width": None,
        "border_color": None,
        "_widget_id": wid,
    }


# ─── Scene 1: catalog_text — Labels, buttons, textbox ───
def scene_catalog_text():
    ws = []
    FG = "#f0f0f0"
    DM = "#909090"

    # Title
    ws.append(
        widget(
            "label",
            0,
            0,
            W,
            LH,
            "TEXT WIDGETS",
            wid="cat1.title",
            fg=FG,
            align="center",
            style="bold",
        )
    )

    # Labels with different alignments
    ws.append(widget("label", 4, 14, 80, LH, "LEFT", wid="cat1.lbl_left", fg=FG, align="left"))
    ws.append(
        widget("label", 88, 14, 80, LH, "CENTER", wid="cat1.lbl_center", fg=FG, align="center")
    )
    ws.append(widget("label", 172, 14, 80, LH, "RIGHT", wid="cat1.lbl_right", fg=FG, align="right"))

    # Labels with styles
    ws.append(widget("label", 4, 28, 80, LH, "DEFAULT", wid="cat1.lbl_def", fg=FG, style="default"))
    ws.append(widget("label", 88, 28, 80, LH, "BOLD", wid="cat1.lbl_bold", fg=FG, style="bold"))
    ws.append(
        widget("label", 172, 28, 80, LH, "INVERSE", wid="cat1.lbl_inv", fg=FG, style="inverse")
    )

    # Buttons (normal, pressed-look, disabled)
    ws.append(
        widget(
            "button",
            4,
            44,
            76,
            LH,
            "OK",
            wid="cat1.btn_ok",
            fg=FG,
            border=True,
            border_style="single",
        )
    )
    ws.append(
        widget(
            "button",
            84,
            44,
            76,
            LH,
            "CANCEL",
            wid="cat1.btn_cancel",
            fg=FG,
            border=True,
            border_style="single",
        )
    )
    ws.append(
        widget(
            "button",
            164,
            44,
            88,
            LH,
            "DISABLED",
            wid="cat1.btn_dis",
            fg=DM,
            border=True,
            border_style="single",
            enabled=False,
        )
    )

    # Textbox
    ws.append(
        widget(
            "textbox",
            4,
            60,
            248,
            LH,
            "EDITABLE TEXT",
            wid="cat1.tbox",
            fg=FG,
            border=True,
            border_style="single",
        )
    )

    # Label with border styles
    y = 76
    for i, bs in enumerate(["single", "double", "rounded", "bold", "dashed"]):
        x = 4 + i * 50
        ws.append(
            widget(
                "label",
                x,
                y,
                46,
                LH,
                bs[:5].upper(),
                wid=f"cat1.bs_{bs}",
                fg=FG,
                border=True,
                border_style=bs,
            )
        )

    # Panel
    ws.append(
        widget(
            "panel",
            4,
            92,
            248,
            32,
            wid="cat1.panel",
            fg=DM,
            bg="#0a0a0a",
            border=True,
            border_style="single",
        )
    )
    ws.append(widget("label", 8, 96, 100, LH, "IN PANEL", wid="cat1.panel_lbl", fg=FG))
    ws.append(
        widget(
            "label", 120, 96, 128, LH, "NESTED LABEL", wid="cat1.panel_lbl2", fg=DM, align="right"
        )
    )

    return {
        "width": W,
        "height": H,
        "widgets": ws,
    }


# ─── Scene 2: catalog_controls — Checkbox, radiobutton, slider ───
def scene_catalog_controls():
    ws = []
    FG = "#f0f0f0"
    DM = "#909090"

    ws.append(
        widget(
            "label", 0, 0, W, LH, "CONTROLS", wid="cat2.title", fg=FG, align="center", style="bold"
        )
    )

    # Checkboxes
    ws.append(widget("checkbox", 4, 14, 76, LH, "OPT 1", wid="cat2.chk1", fg=FG, checked=True))
    ws.append(widget("checkbox", 84, 14, 76, LH, "OPT 2", wid="cat2.chk2", fg=FG, checked=False))
    ws.append(
        widget(
            "checkbox",
            164,
            14,
            88,
            LH,
            "DISABLED",
            wid="cat2.chk3",
            fg=DM,
            checked=True,
            enabled=False,
        )
    )

    # Radiobuttons
    ws.append(widget("radiobutton", 4, 28, 76, LH, "RADIO A", wid="cat2.rad1", fg=FG, checked=True))
    ws.append(
        widget("radiobutton", 84, 28, 76, LH, "RADIO B", wid="cat2.rad2", fg=FG, checked=False)
    )
    ws.append(
        widget(
            "radiobutton",
            164,
            28,
            88,
            LH,
            "RADIO C",
            wid="cat2.rad3",
            fg=DM,
            checked=False,
            enabled=False,
        )
    )

    # Sliders
    ws.append(
        widget(
            "slider", 4, 44, 120, 16, wid="cat2.sld1", fg=FG, value=25, min_value=0, max_value=100
        )
    )
    ws.append(
        widget(
            "slider", 128, 44, 124, 16, wid="cat2.sld2", fg=FG, value=75, min_value=0, max_value=100
        )
    )
    ws.append(
        widget(
            "slider",
            4,
            64,
            248,
            16,
            wid="cat2.sld_wide",
            fg=FG,
            value=50,
            min_value=0,
            max_value=100,
        )
    )

    # Progressbars at various levels
    ws.append(widget("label", 4, 84, 40, LH, "0%", wid="cat2.pbar_l0", fg=DM))
    ws.append(widget("progressbar", 44, 84, 80, LH, wid="cat2.pbar0", fg=FG, bg="#101010", value=0))
    ws.append(widget("label", 128, 84, 40, LH, "50%", wid="cat2.pbar_l1", fg=DM))
    ws.append(
        widget("progressbar", 168, 84, 80, LH, wid="cat2.pbar50", fg=FG, bg="#101010", value=50)
    )

    # Full-width progressbar
    ws.append(
        widget(
            "progressbar", 4, 100, 248, LH, "85%", wid="cat2.pbar85", fg=FG, bg="#101010", value=85
        )
    )
    ws.append(
        widget(
            "progressbar",
            4,
            116,
            248,
            LH,
            "100%",
            wid="cat2.pbar100",
            fg=FG,
            bg="#101010",
            value=100,
        )
    )

    return {
        "width": W,
        "height": H,
        "widgets": ws,
    }


# ─── Scene 3: catalog_data — Gauge, chart, icon, box ───
def scene_catalog_data():
    ws = []
    FG = "#f0f0f0"
    DM = "#909090"

    ws.append(
        widget(
            "label",
            0,
            0,
            W,
            LH,
            "DATA WIDGETS",
            wid="cat3.title",
            fg=FG,
            align="center",
            style="bold",
        )
    )

    # Gauges
    ws.append(
        widget(
            "gauge",
            4,
            14,
            56,
            56,
            wid="cat3.gauge1",
            fg=FG,
            bg="#101010",
            value=30,
            min_value=0,
            max_value=100,
        )
    )
    ws.append(
        widget(
            "gauge",
            64,
            14,
            56,
            56,
            wid="cat3.gauge2",
            fg=FG,
            bg="#101010",
            value=75,
            min_value=0,
            max_value=100,
        )
    )
    ws.append(
        widget(
            "gauge",
            124,
            14,
            56,
            56,
            wid="cat3.gauge3",
            fg=DM,
            bg="#101010",
            value=100,
            min_value=0,
            max_value=100,
        )
    )

    # Icons
    ws.append(widget("icon", 184, 14, 20, 20, wid="cat3.ico1", fg=FG, icon_char="@"))
    ws.append(widget("icon", 208, 14, 20, 20, wid="cat3.ico2", fg=FG, icon_char="#"))
    ws.append(widget("icon", 232, 14, 20, 20, wid="cat3.ico3", fg=DM, icon_char="*"))

    # Box (decorative rectangles)
    ws.append(
        widget(
            "box",
            184,
            38,
            32,
            16,
            wid="cat3.box1",
            fg=FG,
            bg="#303030",
            border=True,
            border_style="single",
        )
    )
    ws.append(
        widget(
            "box",
            220,
            38,
            32,
            16,
            wid="cat3.box2",
            fg=DM,
            bg="#181818",
            border=True,
            border_style="double",
        )
    )

    # Charts — bar
    ws.append(
        widget(
            "chart",
            4,
            74,
            120,
            50,
            "BAR",
            wid="cat3.chart_bar",
            fg=FG,
            bg="#0a0a0a",
            style="bar",
            data_points=[10, 30, 20, 50, 40, 60, 35, 55],
        )
    )
    # Charts — line
    ws.append(
        widget(
            "chart",
            128,
            74,
            124,
            50,
            "LINE",
            wid="cat3.chart_line",
            fg=FG,
            bg="#0a0a0a",
            style="line",
            data_points=[5, 15, 12, 25, 20, 30, 18, 22],
        )
    )

    return {
        "width": W,
        "height": H,
        "widgets": ws,
    }


# ─── Scene 4: catalog_dashboard — Mixed widgets (realistic layout) ───
def scene_catalog_dashboard():
    ws = []
    FG = "#ffffff"
    W1 = "#d0d0d0"
    DM = "#808080"

    # Status bar
    ws.append(
        widget("label", 0, 0, text_w(10), LH, "DASHBOARD", wid="cat4.title", fg=FG, style="bold")
    )
    ws.append(
        widget(
            "label",
            120,
            0,
            text_w(8),
            LH,
            "12:34:56",
            wid="cat4.clock",
            fg=W1,
            align="right",
            runtime="bind=clock;kind=str",
        )
    )
    ws.append(
        widget(
            "progressbar",
            192,
            0,
            60,
            LH,
            wid="cat4.batt",
            fg=W1,
            bg="#101010",
            value=72,
            runtime="bind=batt_pct;kind=int;min=0;max=100",
        )
    )

    # Left column: gauges + value labels
    ws.append(
        widget(
            "gauge",
            4,
            16,
            48,
            48,
            wid="cat4.temp_g",
            fg=W1,
            bg="#101010",
            value=65,
            min_value=0,
            max_value=100,
            runtime="bind=temperature;kind=int;min=0;max=100",
        )
    )
    ws.append(
        widget(
            "label",
            4,
            66,
            48,
            LH,
            "65 C",
            wid="cat4.temp_v",
            fg=W1,
            align="center",
            runtime="bind=temperature;kind=int",
        )
    )

    ws.append(
        widget(
            "gauge",
            56,
            16,
            48,
            48,
            wid="cat4.hum_g",
            fg=W1,
            bg="#101010",
            value=42,
            min_value=0,
            max_value=100,
            runtime="bind=humidity;kind=int;min=0;max=100",
        )
    )
    ws.append(
        widget(
            "label",
            56,
            66,
            48,
            LH,
            "42%",
            wid="cat4.hum_v",
            fg=W1,
            align="center",
            runtime="bind=humidity;kind=int",
        )
    )

    # Right side: chart
    ws.append(
        widget(
            "chart",
            108,
            16,
            144,
            62,
            "HISTORY",
            wid="cat4.hist",
            fg=W1,
            bg="#0a0a0a",
            style="line",
            data_points=[20, 25, 22, 28, 35, 30, 38, 42, 40, 45],
        )
    )

    # Bottom controls
    ws.append(
        widget(
            "slider",
            4,
            82,
            120,
            14,
            wid="cat4.threshold",
            fg=W1,
            value=50,
            min_value=0,
            max_value=100,
            runtime="bind=threshold;kind=int;min=0;max=100",
        )
    )
    ws.append(
        widget(
            "label",
            128,
            82,
            56,
            LH,
            "THR:50",
            wid="cat4.thr_lbl",
            fg=DM,
            runtime="bind=threshold;kind=int",
        )
    )

    ws.append(
        widget(
            "checkbox",
            4,
            100,
            80,
            LH,
            "ALERT",
            wid="cat4.chk_alert",
            fg=W1,
            checked=True,
            runtime="bind=alert_on;kind=bool",
        )
    )
    ws.append(
        widget(
            "checkbox",
            88,
            100,
            80,
            LH,
            "LOG",
            wid="cat4.chk_log",
            fg=W1,
            checked=False,
            runtime="bind=log_on;kind=bool",
        )
    )

    ws.append(
        widget(
            "button",
            172,
            100,
            40,
            LH,
            "RST",
            wid="cat4.btn_rst",
            fg=FG,
            border=True,
            border_style="single",
        )
    )
    ws.append(
        widget(
            "button",
            216,
            100,
            36,
            LH,
            "CFG",
            wid="cat4.btn_cfg",
            fg=FG,
            border=True,
            border_style="single",
        )
    )

    # Bottom bar
    ws.append(
        widget(
            "label",
            0,
            116,
            W,
            LH,
            "UP/DN=SEL  OK=EDIT  BACK=EXIT",
            wid="cat4.nav",
            fg=DM,
            align="center",
        )
    )

    return {
        "width": W,
        "height": H,
        "widgets": ws,
    }


def main():
    result = {
        "width": W,
        "height": H,
        "scenes": {
            "catalog_text": scene_catalog_text(),
            "catalog_controls": scene_catalog_controls(),
            "catalog_data": scene_catalog_data(),
            "catalog_dashboard": scene_catalog_dashboard(),
        },
    }

    out = Path("widget_catalog.json")
    text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if out.exists() and out.read_text(encoding="utf-8") == text:
        print(f"[OK] {out} unchanged")
    else:
        out.write_text(text, encoding="utf-8")
        print(
            f"[OK] wrote {out} ({len(text)} bytes, "
            f"{sum(len(s['widgets']) for s in result['scenes'].values())} widgets "
            f"in {len(result['scenes'])} scenes)"
        )


if __name__ == "__main__":
    main()
