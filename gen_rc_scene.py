#!/usr/bin/env python3
"""Generate rc_scene.json — RC transmitter UI for 256×128 4bpp OLED.

RENDERING padding (draw_text_clipped in drawing.py):
  padding = max(2, pixel_padding // 2) = 2   (pixel_padding = GRID//2 = 4)
  clip_rect = rect.inflate(-4, -4)
  → inner_w = w - 4,  inner_h = h - 4
  → max_chars = inner_w // 6,  1 line needs inner_h ≥ 8

So for ALL text widgets (label OR button):
  min width  = n*6 + 4   (n chars)
  min height = 12         (inner 8 = 1 font line)
"""
import json
import re

W, H = 256, 128
CHAR_W = 6
RENDER_PAD = 2  # per-side padding used by drawing.py

LH = 12   # label/button height  (inner_h = 12-4 = 8 = 1 line)
BH = 12   # same for buttons


def text_w(n):
    """Min width for *n* chars — matches rendering clip_rect."""
    return n * CHAR_W + RENDER_PAD * 2   # n*6 + 4


def btn_w(n):
    """Min button width for *n* chars (same formula — rendering padding is equal)."""
    return n * CHAR_W + RENDER_PAD * 2   # n*6 + 4

def widget(wtype, x, y, w, h, text="", *, wid=None, style="default",
           fg="#f0f0f0", bg="black", border=False, border_style="none",
           align="left", valign="middle", value=0, min_value=0, max_value=100,
           bold=False, visible=True, enabled=True, runtime="",
           data_points=None, icon_char=""):
    return {
        "type": wtype, "x": x, "y": y, "width": w, "height": h,
        "text": text, "style": style,
        "color_fg": fg, "color_bg": bg,
        "border": border, "border_style": border_style,
        "align": align, "valign": valign,
        "text_overflow": "ellipsis", "max_lines": 1 if wtype != "panel" else None,
        "value": value, "min_value": min_value, "max_value": max_value,
        "checked": False, "enabled": enabled, "visible": visible,
        "icon_char": icon_char,
        "data_points": data_points or [],
        "z_index": 0, "padding_x": 1, "padding_y": 0,
        "margin_x": 0, "margin_y": 0,
        "constraints": {}, "responsive_rules": [], "animations": [],
        "runtime": runtime, "locked": False,
        "theme_fg_role": "", "theme_bg_role": "",
        "state": "default", "state_overrides": {},
        "bg_color": None, "text_color": None, "color": None,
        "font_size": None, "bold": bold,
        "corner_radius": None, "border_width": None, "border_color": None,
        "_widget_id": wid,
    }

# ─── Scene 1: rc_main — Main flight HUD ───
# Layout: status bar, 2 stick gauges left/right, 4 channels center,
#         RSSI row, timer row, nav hint
def scene_rc_main():
    ws = []
    W2 = "#ffffff"
    W1 = "#d0d0d0"
    DM = "#808080"

    # ── Status bar (y=0) ──
    # M01(22) MDL1(28) [==batt40==] 4.18V(34) gap STABLE(40) 0:00:00(46)
    ws.append(widget("label", 0, 0, text_w(3), LH, "M01", wid="rc.model_num",
                      fg=W1, runtime="bind=model_num;kind=str"))
    ws.append(widget("label", 22, 0, text_w(4), LH, "MDL1", wid="rc.model_name",
                      fg=W2, bold=True, style="bold",
                      runtime="bind=model_name;kind=str"))
    ws.append(widget("progressbar", 50, 0, 40, LH, wid="rc.batt_bar",
                      fg=W1, bg="#181818", value=85,
                      runtime="bind=batt_pct;kind=int;min=0;max=100"))
    ws.append(widget("label", 92, 0, text_w(5), LH, "4.18V", wid="rc.batt_v",
                      fg=W2, runtime="bind=batt_voltage;kind=float;min=3.0;max=4.2"))
    ws.append(widget("label", 160, 0, text_w(6), LH, "STABLE", wid="rc.flight_mode",
                      fg=W2, bold=True, style="bold",
                      runtime="bind=flight_mode;kind=str"))
    ws.append(widget("label", 208, 0, text_w(7), LH, "0:00:00", wid="rc.timer1",
                      fg=W1, align="right", runtime="bind=timer1;kind=str"))

    # ── Left stick: THR + RUD (x=0..46) ──
    ws.append(widget("label", 0, 14, text_w(3), LH, "THR", wid="rc.thr_lbl",
                      fg=W1, align="center"))
    ws.append(widget("label", 24, 14, text_w(3), LH, "RUD", wid="rc.rud_lbl",
                      fg=W1, align="center"))
    ws.append(widget("gauge", 0, 26, 22, 60, wid="rc.throttle",
                      fg=W1, bg="#101010", value=0, min_value=-100, max_value=100,
                      runtime="bind=ch3;kind=int;min=-100;max=100"))
    ws.append(widget("gauge", 24, 26, 22, 60, wid="rc.rudder",
                      fg=W1, bg="#101010", value=0, min_value=-100, max_value=100,
                      runtime="bind=ch4;kind=int;min=-100;max=100"))

    # ── Right stick: AIL + ELE (x=208..254) ──
    ws.append(widget("label", 208, 14, text_w(3), LH, "AIL", wid="rc.ail_lbl",
                      fg=W1, align="center"))
    ws.append(widget("label", 232, 14, text_w(3), LH, "ELE", wid="rc.ele_lbl",
                      fg=W1, align="center"))
    ws.append(widget("gauge", 208, 26, 22, 60, wid="rc.aileron",
                      fg=W1, bg="#101010", value=0, min_value=-100, max_value=100,
                      runtime="bind=ch1;kind=int;min=-100;max=100"))
    ws.append(widget("gauge", 232, 26, 22, 60, wid="rc.elevator",
                      fg=W1, bg="#101010", value=0, min_value=-100, max_value=100,
                      runtime="bind=ch2;kind=int;min=-100;max=100"))

    # ── Center: 4 channels (x=50..200) — each row 16px ──
    channels = [("Ail", "ch1"), ("Ele", "ch2"), ("Thr", "ch3"), ("Rud", "ch4")]
    for i, (name, bind) in enumerate(channels):
        ry = 16 + i * 16
        ws.append(widget("label", 50, ry, text_w(3), LH, name, wid=f"rc.{bind}_name",
                          fg=W1))
        ws.append(widget("progressbar", 72, ry, 96, LH, wid=f"rc.{bind}_bar",
                          fg=W1, bg="#101010", value=50,
                          runtime=f"bind={bind};kind=int;min=0;max=100"))
        ws.append(widget("label", 170, ry, text_w(4), LH, "1500", wid=f"rc.{bind}_us",
                          fg=W2, align="right",
                          runtime=f"bind={bind}_us;kind=int;min=900;max=2100"))

    # ── RSSI + TX voltage + current (y=88, below gauges at 86) ──
    # RSSI(28) [==bar60==] -40D(28)  TX4.1(34)  12.3A(34)
    ws.append(widget("label", 0, 88, text_w(4), LH, "RSSI", wid="rc.rssi_lbl", fg=DM))
    ws.append(widget("progressbar", 28, 88, 60, LH, wid="rc.rssi_bar",
                      fg=W1, bg="#101010", value=75,
                      runtime="bind=rssi;kind=int;min=0;max=100"))
    ws.append(widget("label", 90, 88, text_w(4), LH, "-40D",
                      wid="rc.rssi_dbm", fg=W1,
                      runtime="bind=rssi_dbm;kind=int;min=-120;max=0"))
    ws.append(widget("label", 120, 88, text_w(5), LH, "TX4.1", wid="rc.tx_batt",
                      fg=W1, runtime="bind=tx_voltage;kind=float;min=3.0;max=5.0"))
    ws.append(widget("label", 156, 88, text_w(5), LH, "12.3A", wid="rc.current",
                      fg=W1, runtime="bind=current;kind=float;min=0;max=50.0"))
    ws.append(widget("label", 192, 88, text_w(5), LH, "0 MAH", wid="rc.mah_used",
                      fg=W1, align="right",
                      runtime="bind=mah_used;kind=int;min=0;max=9999"))

    # ── Bottom: timers + mode (y=100) ──
    ws.append(widget("label", 0, 100, text_w(7), LH, "T1 0:00", wid="rc.timer1_big",
                      fg=W2, bold=True, style="bold", runtime="bind=timer1;kind=str"))
    ws.append(widget("label", 48, 100, text_w(7), LH, "T2 0:00",
                      wid="rc.timer2_big",
                      fg=W1, runtime="bind=timer2;kind=str"))
    ws.append(widget("label", 96, 100, text_w(6), LH, "STABLE",
                      wid="rc.mode_big",
                      fg=W2, bold=True, style="bold",
                      runtime="bind=flight_mode;kind=str"))

    # Nav hint at very bottom (y=114 → bottom 126, 2px margin)
    ws.append(widget("label", 0, 114, W, LH, "< CH  TRIM  TELE  SETUP >",
                      wid="rc.nav_hint", fg=DM, align="center"))

    return {"name": "rc_main", "width": W, "height": H, "bg_color": "black", "widgets": ws}


# ─── Scene 2: rc_channels — Full 8-ch monitor ───
def scene_rc_channels():
    ws = []
    W2 = "#ffffff"
    W1 = "#d0d0d0"

    ws.append(widget("label", 0, 0, text_w(10), LH, "CH Monitor", wid="rch.title",
                      fg=W2, bold=True, style="bold"))

    ch_names = ["Aileron", "Elevator", "Throttle", "Rudder",
                "Aux 1", "Aux 2", "Aux 3", "Aux 4"]
    for i in range(8):
        col = i // 4
        row = i % 4
        x = col * 128
        y = 14 + row * 28

        ch = i + 1
        bind = f"ch{ch}"
        short = ch_names[i][:3]

        ws.append(widget("label", x, y, text_w(7), LH, f"CH{ch} {short}",
                          wid=f"rch.ch{ch}_label", fg=W2))
        ws.append(widget("label", x + 80, y, text_w(4), LH, "1500",
                          wid=f"rch.ch{ch}_us", fg=W2, align="right",
                          runtime=f"bind={bind}_us;kind=int;min=900;max=2100"))
        ws.append(widget("progressbar", x, y + 12, 120, LH,
                          wid=f"rch.ch{ch}_bar", fg=W1, bg="#101010", value=50,
                          runtime=f"bind={bind};kind=int;min=0;max=100"))

    return {"name": "rc_channels", "width": W, "height": H, "bg_color": "black", "widgets": ws}


# ─── Scene 3: rc_trims ───
def scene_rc_trims():
    ws = []
    W2 = "#ffffff"
    W1 = "#d0d0d0"

    ws.append(widget("label", 0, 0, text_w(5), LH, "Trims", wid="rct.title",
                      fg=W2, bold=True, style="bold"))

    trims = [("Aileron", "trim_ail"), ("Elevator", "trim_ele"),
             ("Throttle", "trim_thr"), ("Rudder", "trim_rud")]
    for i, (name, bind) in enumerate(trims):
        y = 16 + i * 26
        ws.append(widget("label", 0, y, text_w(3), LH, name[:3], wid=f"rct.{bind}_name",
                          fg=W2))
        ws.append(widget("slider", text_w(3), y, 200, LH, wid=f"rct.{bind}_slider",
                          fg=W1, bg="#101010", value=0, min_value=-50, max_value=50,
                          runtime=f"bind={bind};kind=int;min=-50;max=50;step=1"))
        ws.append(widget("label", text_w(3) + 200, y, text_w(3), LH, "+0", wid=f"rct.{bind}_value",
                          fg=W2, align="right",
                          runtime=f"bind={bind};kind=int;min=-50;max=50"))

    ws.append(widget("button", 80, 114, btn_w(9), BH, "Reset All", wid="rct.reset_btn",
                      fg=W2, bg="#181818", border=True, border_style="single",
                      align="center", style="highlight"))

    return {"name": "rc_trims", "width": W, "height": H, "bg_color": "black", "widgets": ws}


# ─── Scene 4: rc_setup ───
def scene_rc_setup():
    ws = []
    W2 = "#ffffff"

    ws.append(widget("label", 0, 0, text_w(5), LH, "Setup", wid="rcs.title",
                      fg=W2, bold=True, style="bold"))

    items = [
        ("Model Select",  "rcs.model_sel",
         "bind=model;kind=list;values=Model1|Model2|Model3|Model4"),
        ("Channel Map",   "rcs.ch_map",    ""),
        ("Endpoints",     "rcs.endpoints", ""),
        ("Failsafe",      "rcs.failsafe",  ""),
        ("TX Power",      "rcs.tx_power",
         "bind=tx_power;kind=list;values=10mW|25mW|50mW|100mW"),
        ("Bind Receiver", "rcs.bind_rx",   ""),
        ("Calibrate",     "rcs.calibrate", ""),
    ]
    for i, (text, wid_name, rt) in enumerate(items):
        y = 14 + i * 16
        sty = "highlight" if i == 0 else "default"
        ws.append(widget("button", 8, y, 240, BH, text, wid=wid_name,
                          fg=W2, bg="#080808", border=True, border_style="single",
                          align="left", style=sty, runtime=rt))

    return {"name": "rc_setup", "width": W, "height": H, "bg_color": "black", "widgets": ws}


# ─── Scene 5: rc_model — Endpoints ───
def scene_rc_model():
    ws = []
    W2 = "#ffffff"
    W1 = "#d0d0d0"

    ws.append(widget("label", 0, 0, text_w(9), LH, "Endpoints", wid="rcm.title",
                      fg=W2, bold=True, style="bold"))

    ch_names = ["Ail", "Ele", "Thr", "Rud"]
    for i, name in enumerate(ch_names):
        y = 14 + i * 24
        ch = i + 1
        ws.append(widget("label", 0, y, text_w(3), LH, name, wid=f"rcm.ch{ch}_name",
                          fg=W2, bold=True, style="bold"))
        ws.append(widget("label", text_w(3), y, text_w(4), LH, "1000", wid=f"rcm.ch{ch}_min",
                          fg=W1, runtime=f"bind=ep{ch}_min;kind=int;min=800;max=1500;step=10"))
        ws.append(widget("label", text_w(3) + text_w(4), y, text_w(4), LH, "1500",
                          wid=f"rcm.ch{ch}_ctr",
                          fg=W2, runtime=f"bind=ep{ch}_ctr;kind=int;min=1400;max=1600;step=5"))
        ws.append(widget("label", text_w(3) + 2 * text_w(4), y, text_w(4), LH, "2000",
                          wid=f"rcm.ch{ch}_max",
                          fg=W1, runtime=f"bind=ep{ch}_max;kind=int;min=1500;max=2200;step=10"))
        ws.append(widget("progressbar", 0, y + 12, 130, LH, wid=f"rcm.ch{ch}_range",
                          fg=W1, bg="#101010", value=50,
                          runtime=f"bind=ch{ch};kind=int;min=0;max=100"))

    ws.append(widget("button", 8, 114, btn_w(4), BH, "Save", wid="rcm.save_btn",
                      fg=W2, bg="#181818", border=True, border_style="single",
                      align="center"))
    ws.append(widget("button", 176, 114, btn_w(6), BH, "Cancel", wid="rcm.cancel_btn",
                      fg=W1, bg="#181818", border=True, border_style="single",
                      align="center"))

    return {"name": "rc_model", "width": W, "height": H, "bg_color": "black", "widgets": ws}


# ─── Scene 6: rc_failsafe ───
def scene_rc_failsafe():
    ws = []
    W2 = "#ffffff"
    W1 = "#d0d0d0"

    ws.append(widget("label", 0, 0, text_w(8), LH, "Failsafe", wid="rcf.title",
                      fg=W2, bold=True, style="bold"))

    ws.append(widget("label", 0, 14, text_w(21), LH, "Set safe loss values!", wid="rcf.warning",
                      fg=W2, bold=True, style="bold"))

    ws.append(widget("label", 0, 28, text_w(5), LH, "Mode:", wid="rcf.mode_lbl",
                      fg=W1))
    ws.append(widget("button", text_w(5), 28, btn_w(9), BH, "Hold Last", wid="rcf.mode_btn",
                      fg=W2, bg="#181818", border=True, border_style="single",
                      align="center",
                      runtime="bind=fs_mode;kind=list;values=Hold Last|Custom|No Pulse"))

    names = ["Ail", "Ele", "Thr", "Rud"]
    for i in range(4):
        ch = i + 1
        y = 42 + i * 18
        ws.append(widget("label", 0, y, text_w(3), LH, names[i], wid=f"rcf.ch{ch}_name",
                          fg=W2))
        ws.append(widget("slider", text_w(3), y, 180, LH, wid=f"rcf.ch{ch}_slider",
                          fg=W1, bg="#101010", value=1500, min_value=900, max_value=2100,
                          runtime=f"bind=fs_ch{ch};kind=int;min=900;max=2100;step=10"))
        ws.append(widget("label", text_w(3) + 180, y, text_w(4), LH, "1500",
                          wid=f"rcf.ch{ch}_val",
                          fg=W2, align="right",
                          runtime=f"bind=fs_ch{ch};kind=int;min=900;max=2100"))

    ws.append(widget("button", 0, 114, btn_w(11), BH, "Set Current", wid="rcf.set_current",
                      fg=W2, bg="#181818", border=True, border_style="single",
                      align="center"))
    ws.append(widget("button", btn_w(11) + 4, 114, btn_w(4), BH, "Save", wid="rcf.save_btn",
                      fg=W2, bg="#181818", border=True, border_style="single",
                      align="center"))
    ws.append(widget("button", btn_w(11) + 4 + btn_w(4) + 4, 114, btn_w(4), BH, "Back",
                      wid="rcf.back_btn",
                      fg=W1, bg="#181818", border=True, border_style="single",
                      align="center"))

    return {"name": "rc_failsafe", "width": W, "height": H, "bg_color": "black", "widgets": ws}


# ─── Scene 7: rc_telemetry — Live telemetry dashboard ───
def scene_rc_telemetry():
    ws = []
    W2 = "#ffffff"
    W1 = "#d0d0d0"
    DM = "#808080"
    # Column grid: label(22px) + value(34px) + gap(6px) = 62px per column
    V0 = 22    # col 0 value start
    C1 = 62    # col 1 label start
    V1 = 84    # col 1 value start
    C2 = 124   # col 2 label start

    ws.append(widget("label", 0, 0, text_w(9), LH, "Telemetry", wid="rct2.title",
                      fg=W2, bold=True, style="bold"))
    ws.append(widget("label", C1, 0, text_w(4), LH, "LIVE", wid="rct2.status",
                      fg="#60ff60", bold=True, style="bold"))

    # ── Link quality (y=14) ──
    ws.append(widget("label", 0, 14, text_w(3), LH, "LNK", wid="rct2.rssi_lbl", fg=DM))
    ws.append(widget("progressbar", V0, 14, 80, LH, wid="rct2.rssi_bar",
                      fg=W1, bg="#101010", value=85,
                      runtime="bind=rssi;kind=int;min=0;max=100"))
    ws.append(widget("label", 104, 14, text_w(4), LH, "85 %",
                      wid="rct2.rssi_pct", fg=W2,
                      runtime="bind=rssi;kind=int;min=0;max=100"))
    ws.append(widget("label", 136, 14, text_w(5), LH, "-42DB", wid="rct2.rssi_db",
                      fg=W1, runtime="bind=rssi_dbm;kind=int;min=-120;max=0"))

    # ── Battery (y=28) ──
    ws.append(widget("label", 0, 28, text_w(3), LH, "BAT", wid="rct2.bat_lbl",
                      fg=DM, bold=True, style="bold"))
    ws.append(widget("label", V0, 28, text_w(5), LH, "4.18V", wid="rct2.bat_v",
                      fg=W2, runtime="bind=batt_voltage;kind=float;min=3.0;max=4.2"))
    ws.append(widget("progressbar", 58, 28, 60, LH, wid="rct2.bat_bar",
                      fg=W1, bg="#101010", value=85,
                      runtime="bind=batt_pct;kind=int;min=0;max=100"))
    ws.append(widget("label", 120, 28, text_w(4), LH, "85 %",
                      wid="rct2.bat_pct", fg=W2,
                      runtime="bind=batt_pct;kind=int;min=0;max=100"))

    # ── Cell voltages (y=42) — 4 cells, each 64px wide ──
    for c in range(1, 5):
        xo = (c - 1) * 64
        ws.append(widget("label", xo, 42, text_w(2), LH, f"C{c}", wid=f"rct2.cell{c}_lbl",
                          fg=DM))
        ws.append(widget("label", xo + 16, 42, text_w(5), LH, "4.18V",
                          wid=f"rct2.cell{c}_v", fg=W1,
                          runtime=f"bind=cell{c}_v;kind=float;min=3.0;max=4.3"))

    # ── Current sensor (y=56) ──
    ws.append(widget("label", 0, 56, text_w(3), LH, "AMP", wid="rct2.amp_lbl", fg=DM))
    ws.append(widget("label", V0, 56, text_w(5), LH, "12.3A", wid="rct2.amp_val",
                      fg=W2, runtime="bind=current;kind=float;min=0;max=99.9"))
    ws.append(widget("label", C1, 56, text_w(3), LH, "MAH", wid="rct2.mah_lbl", fg=DM))
    ws.append(widget("label", V1, 56, text_w(5), LH, " 1250", wid="rct2.mah_val",
                      fg=W2, runtime="bind=mah_used;kind=int;min=0;max=99999"))
    ws.append(widget("label", C2, 56, text_w(5), LH, "28.5W", wid="rct2.watts",
                      fg=W1, runtime="bind=watts;kind=float;min=0;max=999"))

    # ── GPS section (y=70) ──
    ws.append(widget("label", 0, 70, text_w(3), LH, "GPS", wid="rct2.gps_lbl",
                      fg=DM, bold=True, style="bold"))
    ws.append(widget("label", V0, 70, text_w(4), LH, "12 S", wid="rct2.gps_sats",
                      fg=W1, runtime="bind=gps_sats;kind=int;min=0;max=30"))
    ws.append(widget("label", C1, 70, text_w(4), LH, "3DFX", wid="rct2.gps_fix",
                      fg=W2, runtime="bind=gps_fix;kind=str"))

    # Speed / Altitude (y=84), Distance / Heading (y=98)
    ws.append(widget("label", 0, 84, text_w(3), LH, "SPD", wid="rct2.spd_lbl", fg=DM))
    ws.append(widget("label", V0, 84, text_w(5), LH, " 0KMH", wid="rct2.spd_val",
                      fg=W2, runtime="bind=gps_speed;kind=float;min=0;max=999"))
    ws.append(widget("label", C1, 84, text_w(3), LH, "ALT", wid="rct2.alt_lbl", fg=DM))
    ws.append(widget("label", V1, 84, text_w(5), LH, "  0 M", wid="rct2.alt_val",
                      fg=W2, runtime="bind=gps_alt;kind=float;min=-99;max=9999"))

    ws.append(widget("label", 0, 98, text_w(3), LH, "DST", wid="rct2.dst_lbl", fg=DM))
    ws.append(widget("label", V0, 98, text_w(5), LH, "  0 M", wid="rct2.dst_val",
                      fg=W2, runtime="bind=gps_dist;kind=float;min=0;max=99999"))
    ws.append(widget("label", C1, 98, text_w(3), LH, "HDG", wid="rct2.hdg_lbl", fg=DM))
    ws.append(widget("label", V1, 98, text_w(4), LH, "  0D", wid="rct2.hdg_val",
                      fg=W1, runtime="bind=gps_hdg;kind=int;min=0;max=359"))

    # ── RSSI history chart (right side y=70..110) ──
    ws.append(widget("chart", 160, 70, 94, 40, wid="rct2.rssi_chart",
                      fg=W1, bg="#101010",
                      runtime="bind=rssi;kind=int;min=0;max=100"))

    # ── Nav hint ──
    ws.append(widget("label", 0, 114, W, LH, "< MAIN  CH  TRIM  SETUP >",
                      wid="rct2.nav_hint", fg=DM, align="center"))

    return {"name": "rc_telemetry", "width": W, "height": H, "bg_color": "black", "widgets": ws}


# ─── Scene 8: rc_mixer — Rates, Expo, Mixes ───
def scene_rc_rates():
    """Dual Rate & Expo — one screen per axis group, clean layout."""
    ws = []
    W2 = "#ffffff"
    W1 = "#d0d0d0"
    DM = "#808080"

    # Header
    ws.append(widget("label", 0, 0, text_w(5), LH, "RATES", wid="rcr.title",
                      fg=W2, bold=True, style="bold"))
    ws.append(widget("label", 40, 0, text_w(10), LH, "PROFILE  1", wid="rcr.prof",
                      fg=W1, runtime="bind=rate_profile;kind=str"))

    # Column headers (y=14)
    ws.append(widget("label", 66, 14, text_w(4), LH, "RATE", wid="rcr.hdr_dr",
                      fg=DM, align="center"))
    ws.append(widget("label", 168, 14, text_w(4), LH, "EXPO", wid="rcr.hdr_ex",
                      fg=DM, align="center"))

    # 4 axes — spacious rows (20px each: y=28,48,68,88)
    axes = [("AIL", "ail"), ("ELE", "ele"), ("THR", "thr"), ("RUD", "rud")]
    for i, (label, bind) in enumerate(axes):
        y = 28 + i * 20

        # Axis name
        ws.append(widget("label", 0, y, text_w(3), LH, label, wid=f"rcr.{bind}_lbl",
                          fg=W2, bold=True, style="bold"))

        # Dual rate: bar(60px) + value
        ws.append(widget("progressbar", 24, y, 60, LH, wid=f"rcr.{bind}_dr_bar",
                          fg=W1, bg="#101010", value=100,
                          runtime=f"bind=dr_{bind};kind=int;min=0;max=125"))
        ws.append(widget("label", 86, y, text_w(4), LH, "100%",
                          wid=f"rcr.{bind}_dr_val", fg=W2, align="right",
                          runtime=f"bind=dr_{bind};kind=int;min=0;max=125"))

        # Expo: bar(60px) + value
        ws.append(widget("progressbar", 126, y, 60, LH, wid=f"rcr.{bind}_ex_bar",
                          fg=W1, bg="#101010", value=30,
                          runtime=f"bind=expo_{bind};kind=int;min=0;max=100"))
        ws.append(widget("label", 188, y, text_w(3), LH, "30%",
                          wid=f"rcr.{bind}_ex_val", fg=W2, align="right",
                          runtime=f"bind=expo_{bind};kind=int;min=0;max=100"))

    # Nav hint
    ws.append(widget("label", 0, 114, W, LH, "< MAIN  CH  TRIM  MIX >",
                      wid="rcr.nav_hint", fg=DM, align="center"))

    return {"name": "rc_rates", "width": W, "height": H, "bg_color": "black", "widgets": ws}


def scene_rc_mixer():
    """Channel mixes — detailed view with bars."""
    ws = []
    W2 = "#ffffff"
    W1 = "#d0d0d0"
    DM = "#808080"

    # Header
    ws.append(widget("label", 0, 0, text_w(5), LH, "MIXES", wid="rcx.title",
                      fg=W2, bold=True, style="bold"))

    # 6 mix slots, each row = 18px: source>dest bar value
    # y = 14, 32, 50, 68, 86 (5 visible mixes + add slot)
    mixes = [
        ("AIL>RUD", "mix1", 50),
        ("ELE>FLP", "mix2", 0),
        ("THR>ELE", "mix3", 0),
        ("RUD>AIL", "mix4", 0),
        ("THR>FLP", "mix5", 0),
    ]
    for j, (name, bind, val) in enumerate(mixes):
        y = 16 + j * 18

        ws.append(widget("label", 0, y, text_w(7), LH, name, wid=f"rcx.{bind}_lbl",
                          fg=W1))
        ws.append(widget("progressbar", 48, y, 80, LH, wid=f"rcx.{bind}_bar",
                          fg=W1, bg="#101010", value=abs(val),
                          runtime=f"bind={bind};kind=int;min=-100;max=100"))
        ws.append(widget("label", 132, y, text_w(4), LH, f"{val:3d}%",
                          wid=f"rcx.{bind}_val", fg=W2, align="right",
                          runtime=f"bind={bind};kind=int;min=-100;max=100"))
        # On/off indicator
        ws.append(widget("checkbox", 162, y, LH, LH,
                          wid=f"rcx.{bind}_on", fg=W1, value=1 if val != 0 else 0,
                          runtime=f"bind={bind}_en;kind=bool"))

    # Add-mix button
    ws.append(widget("button", 0, 100, text_w(9), LH, "ADD  MIX",
                      wid="rcx.add_mix", fg=W1, runtime="action=add_mix"))

    # Nav hint
    ws.append(widget("label", 0, 114, W, LH, "< MAIN  RATE  CH  SETUP >",
                      wid="rcx.nav_hint", fg=DM, align="center"))

    return {"name": "rc_mixer", "width": W, "height": H, "bg_color": "black", "widgets": ws}


# ═══════════════════════════════════════════════════════════════════
# PERIMETER RULES — hard validation, must all pass or script fails
# ═══════════════════════════════════════════════════════════════════

# Valid widget types (must match ui_scene.h UiWidgetType enum)
VALID_TYPES = {"label", "box", "button", "gauge", "progressbar",
               "checkbox", "radiobutton", "slider", "textbox",
               "panel", "icon", "chart"}

# Widget types that have visible text and need overflow checks
TEXT_TYPES = {"label", "button", "checkbox"}
# Widget types that never have text overflow
NO_TEXT_TYPES = {"gauge", "progressbar", "slider", "box", "panel", "icon", "chart"}

# Valid style names the renderer understands
VALID_STYLES = {"default", "bold", "highlight", "inverse", "inverse_highlight"}
# Valid align/valign
VALID_ALIGNS = {"left", "center", "right"}
VALID_VALIGNS = {"top", "middle", "bottom"}
# Valid border styles
VALID_BORDER_STYLES = {"none", "", "single", "double", "rounded", "dashed"}
# Valid overflow modes
VALID_OVERFLOW = {"ellipsis", "wrap", "clip", "auto"}

# Supported font characters (must match font6x8.py / ui_font_6x8.c)
# Lowercase a-z auto-mapped to uppercase in both renderers
FONT_CHARS = set(" .:_-/%?+<>!=(),#*0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ")

# 4-bit grayscale: 16 levels (0x00, 0x11, ..., 0xFF)
# Colors dimmer than this threshold are invisible on OLED
MIN_VISIBLE_BRIGHTNESS = 0x20   # ~12% — anything below is unreadable

# Minimum pixel margin from screen edges for non-full-span widgets
MIN_EDGE_MARGIN = 2

_HEX_RE = re.compile(r"^#([0-9a-fA-F]{6})$")
_NAMED_COLORS = {
    "black": (0, 0, 0), "white": (255, 255, 255),
    "red": (255, 0, 0), "green": (0, 255, 0), "blue": (0, 0, 255),
    "gray": (128, 128, 128), "grey": (128, 128, 128),
}


def _parse_color(s):
    """Parse color string → (r,g,b) or None."""
    if not s:
        return None
    low = s.strip().lower()
    if low in _NAMED_COLORS:
        return _NAMED_COLORS[low]
    m = _HEX_RE.match(s.strip())
    if m:
        h = m.group(1)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    return None


def _brightness(rgb):
    """Perceived brightness (0..255) using rec.709 luma."""
    return int(0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2])


def _wref(scene_name, w, idx):
    """Human-readable widget reference for error messages."""
    wid = w.get("_widget_id") or f"#{idx}"
    return f"{scene_name}/{wid}"


def validate_scene(scene_name, scene):
    """Run all perimeter rules on one scene. Returns list of error strings."""
    errors = []
    sw, sh = scene["width"], scene["height"]
    widgets = scene["widgets"]

    seen_ids = {}

    for i, w in enumerate(widgets):
        ref = _wref(scene_name, w, i)
        wt = w["type"]
        x, y, ww, wh = w["x"], w["y"], w["width"], w["height"]
        text = w.get("text", "") or ""
        has_border = w.get("border", False)

        # ── Rule 1: Unique widget IDs ──
        wid = w.get("_widget_id")
        if wid:
            if wid in seen_ids:
                errors.append(f"DUPLICATE_ID: {ref} — id '{wid}' "
                              f"already used by widget #{seen_ids[wid]}")
            else:
                seen_ids[wid] = i
        else:
            errors.append(f"MISSING_ID: widget #{i} in {scene_name} has no _widget_id")

        # ── Rule 2: Valid widget type ──
        if wt not in VALID_TYPES:
            errors.append(f"BAD_TYPE: {ref} — '{wt}' not in {sorted(VALID_TYPES)}")

        # ── Rule 3: Positive dimensions ──
        if ww < 1 or wh < 1:
            errors.append(f"BAD_SIZE: {ref} — {ww}×{wh} (must be ≥1×1)")

        # ── Rule 4: Within scene bounds ──
        if x < 0 or y < 0:
            errors.append(f"OUT_OF_BOUNDS: {ref} — origin ({x},{y}) is negative")
        if x + ww > sw:
            errors.append(f"OUT_OF_BOUNDS: {ref} — right edge {x+ww} > scene width {sw}")
        if y + wh > sh:
            errors.append(f"OUT_OF_BOUNDS: {ref} — bottom edge {y+wh} > scene height {sh}")

        # ── Rule 5: Integer coordinates ──
        for dim_name, dim_val in [("x", x), ("y", y), ("w", ww), ("h", wh)]:
            if not isinstance(dim_val, int):
                errors.append(f"NON_INT: {ref} — {dim_name}={dim_val!r} must be int")

        # ── Rule 6: Minimum height for text types ──
        if wt in TEXT_TYPES:
            if wh < LH:
                errors.append(f"TOO_SHORT: {ref} — h={wh} < min {LH}")

        # ── Rule 7: Text overflow check (matches RENDERING formula) ──
        # drawing.py: clip_rect = rect.inflate(-4,-4) → inner = dim - 4
        if wt in TEXT_TYPES and text:
            margin = RENDER_PAD * 2   # 4px total
            inner_w = ww - margin
            inner_h = wh - margin
            max_chars = inner_w // CHAR_W if inner_w > 0 else 0
            max_lines = inner_h // 8 if inner_h > 0 else 0
            if max_lines < 1:
                errors.append(f"TEXT_OVERFLOW_V: {ref} — h={wh}, inner_h={inner_h}, "
                              f"can fit 0 lines (need ≥8px inner)")
            if len(text) > max_chars and max_chars > 0:
                errors.append(f"TEXT_OVERFLOW_H: {ref} — text '{text}' ({len(text)} chars) "
                              f"> max_chars {max_chars} (inner_w={inner_w})")

        # ── Rule 8: Minimum widget width for text types ──
        if wt in TEXT_TYPES and text:
            min_w = RENDER_PAD * 2 + CHAR_W  # at least 1 char must fit
            if ww < min_w:
                errors.append(f"TOO_NARROW: {ref} — w={ww} < min {min_w} "
                              f"(can't fit even 1 char)")

        # ── Rule 9: Value range sanity ──
        if wt in ("gauge", "progressbar", "slider"):
            vmin = w.get("min_value", 0)
            vmax = w.get("max_value", 100)
            val = w.get("value", 0)
            if vmin >= vmax:
                errors.append(f"BAD_RANGE: {ref} — min={vmin} >= max={vmax}")
            if val < vmin or val > vmax:
                errors.append(f"VALUE_OOB: {ref} — value={val} not in [{vmin},{vmax}]")

        # ── Rule 10: Valid style name ──
        style = w.get("style", "default") or "default"
        if style.lower() not in VALID_STYLES:
            errors.append(f"BAD_STYLE: {ref} — '{style}' not in {sorted(VALID_STYLES)}")

        # ── Rule 11: Valid align/valign ──
        align = (w.get("align", "left") or "left").lower()
        valign = (w.get("valign", "middle") or "middle").lower()
        if align not in VALID_ALIGNS:
            errors.append(f"BAD_ALIGN: {ref} — align='{align}' not in {sorted(VALID_ALIGNS)}")
        if valign not in VALID_VALIGNS:
            errors.append(f"BAD_VALIGN: {ref} — valign='{valign}' not in {sorted(VALID_VALIGNS)}")

        # ── Rule 12: Valid border_style ──
        bstyle = (w.get("border_style", "none") or "none").lower()
        if bstyle not in VALID_BORDER_STYLES:
            errors.append(f"BAD_BORDER_STYLE: {ref} — '{bstyle}' not in {sorted(VALID_BORDER_STYLES)}")

        # ── Rule 13: border=True requires a visible border_style ──
        if has_border and bstyle in {"none", ""}:
            errors.append(f"BORDER_NO_STYLE: {ref} — border=True but border_style='{bstyle}'")

        # ── Rule 14: Valid text_overflow ──
        overflow = (w.get("text_overflow", "ellipsis") or "ellipsis").lower()
        if overflow not in VALID_OVERFLOW:
            errors.append(f"BAD_OVERFLOW: {ref} — '{overflow}' not in {sorted(VALID_OVERFLOW)}")

        # ── Rule 15: Foreground color parseable and visible on black bg ──
        fg_str = w.get("color_fg", "")
        if fg_str:
            fg_rgb = _parse_color(fg_str)
            if fg_rgb is None:
                errors.append(f"BAD_COLOR_FG: {ref} — can't parse '{fg_str}'")
            elif wt in TEXT_TYPES and text:
                br = _brightness(fg_rgb)
                if br < MIN_VISIBLE_BRIGHTNESS:
                    errors.append(f"INVISIBLE_TEXT: {ref} — fg='{fg_str}' brightness "
                                  f"{br} < {MIN_VISIBLE_BRIGHTNESS} (unreadable on black)")

        # ── Rule 16: Background color parseable ──
        bg_str = w.get("color_bg", "")
        if bg_str:
            bg_rgb = _parse_color(bg_str)
            if bg_rgb is None:
                errors.append(f"BAD_COLOR_BG: {ref} — can't parse '{bg_str}'")

        # ── Rule 17: Contrast check — fg vs bg for text widgets ──
        if wt in TEXT_TYPES and text and fg_str and bg_str:
            fg_rgb = _parse_color(fg_str)
            bg_rgb = _parse_color(bg_str)
            if fg_rgb and bg_rgb:
                contrast = abs(_brightness(fg_rgb) - _brightness(bg_rgb))
                if contrast < 40:
                    errors.append(f"LOW_CONTRAST: {ref} — fg='{fg_str}' vs bg='{bg_str}' "
                                  f"Δbrightness={contrast} < 40")

        # ── Rule 18: Minimum gauge/slider/progressbar size ──
        if wt == "gauge" and (ww < 8 or wh < 8):
            errors.append(f"GAUGE_TOO_SMALL: {ref} — {ww}×{wh} (min 8×8)")
        if wt == "slider" and ww < 16:
            errors.append(f"SLIDER_TOO_NARROW: {ref} — w={ww} (min 16)")
        if wt == "progressbar" and ww < 8:
            errors.append(f"PBAR_TOO_NARROW: {ref} — w={ww} (min 8)")

        # ── Rule 19: z_index is an integer ──
        z = w.get("z_index", 0)
        if not isinstance(z, int):
            errors.append(f"BAD_Z_INDEX: {ref} — z_index={z!r} must be int")

        # ── Rule 20: runtime string format ──
        rt = w.get("runtime", "") or ""
        if rt:
            # Must be semicolon-separated key=value pairs
            for part in rt.split(";"):
                part = part.strip()
                if not part:
                    continue
                if "=" not in part:
                    errors.append(f"BAD_RUNTIME: {ref} — '{part}' missing '=' in runtime")
                    break

        # ── Rule 24: Edge margin — non-full-span widgets must not touch screen edges ──
        # Prevents widgets being flush against the display boundary (looks clipped)
        if ww < sw:  # widget narrower than scene → check horizontal edges
            if x > 0 and x + ww > sw - MIN_EDGE_MARGIN:
                errors.append(f"EDGE_MARGIN_R: {ref} — right edge {x+ww} "
                              f"> {sw - MIN_EDGE_MARGIN} (need {MIN_EDGE_MARGIN}px margin)")
        if wh < sh:  # widget shorter than scene → check vertical edges
            if y > 0 and y + wh > sh - MIN_EDGE_MARGIN:
                errors.append(f"EDGE_MARGIN_B: {ref} — bottom edge {y+wh} "
                              f"> {sh - MIN_EDGE_MARGIN} (need {MIN_EDGE_MARGIN}px margin)")

        # ── Rule 25: Text widget with no text and no runtime binding ──
        if wt in TEXT_TYPES and not text and not rt:
            errors.append(f"EMPTY_TEXT: {ref} — {wt} with no text and no runtime binding")

        # ── Rule 26: All text characters must be in font charset ──
        if wt in TEXT_TYPES and text:
            bad = [ch for ch in text if ch.upper() not in FONT_CHARS]
            if bad:
                unique = "".join(sorted(set(bad)))
                errors.append(f"UNSUPPORTED_CHAR: {ref} — text '{text}' has "
                              f"chars not in font: {unique!r}")

    # ── Rule 21: No overlapping widgets ──
    for i in range(len(widgets)):
        a = widgets[i]
        ax1, ay1 = a["x"], a["y"]
        ax2, ay2 = ax1 + a["width"], ay1 + a["height"]
        for j in range(i + 1, len(widgets)):
            b = widgets[j]
            bx1, by1 = b["x"], b["y"]
            bx2, by2 = bx1 + b["width"], by1 + b["height"]
            if ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1:
                ref_a = _wref(scene_name, a, i)
                ref_b = _wref(scene_name, b, j)
                errors.append(
                    f"OVERLAP: {ref_a} [{ax1},{ay1}..{ax2},{ay2}] ∩ "
                    f"{ref_b} [{bx1},{by1}..{bx2},{by2}]")

    # ── Rule 22: Scene must not be empty ──
    if not widgets:
        errors.append(f"EMPTY_SCENE: {scene_name} has 0 widgets")

    # ── Rule 23: Scene dimensions match global W×H ──
    if sw != W or sh != H:
        errors.append(f"SCENE_SIZE: {scene_name} is {sw}×{sh}, expected {W}×{H}")

    return errors


def validate_all(doc):
    """Validate all scenes. Prints results and returns True if clean."""
    all_errors = []

    # ── Global: at least 1 scene ──
    if not doc.get("scenes"):
        all_errors.append("NO_SCENES: document has no scenes")
        _print_errors(all_errors)
        return False

    for name, scene in doc["scenes"].items():
        errs = validate_scene(name, scene)
        all_errors.extend(errs)

    # ── Global: unique IDs across ALL scenes ──
    global_ids = {}
    for name, scene in doc["scenes"].items():
        for _i, w in enumerate(scene["widgets"]):
            wid = w.get("_widget_id")
            if wid:
                if wid in global_ids:
                    all_errors.append(
                        f"GLOBAL_DUP_ID: '{wid}' in {name} and {global_ids[wid]}")
                else:
                    global_ids[wid] = name

    # ── Global: total widget count sanity ──
    total = sum(len(s["widgets"]) for s in doc["scenes"].values())
    if total > 500:
        all_errors.append(f"TOO_MANY_WIDGETS: {total} total (max 500)")

    # ── Global: max widgets per scene ──
    for name, scene in doc["scenes"].items():
        n = len(scene["widgets"])
        if n > 80:
            all_errors.append(f"SCENE_TOO_DENSE: {name} has {n} widgets (max 80)")

    _print_errors(all_errors)
    return len(all_errors) == 0


def _print_errors(all_errors):
    if all_errors:
        print(f"\n{'='*60}")
        print(f"PERIMETER VALIDATION FAILED — {len(all_errors)} error(s):")
        print(f"{'='*60}")
        for err in all_errors:
            print(f"  ✗ {err}")
        print()
    else:
        print("✓ Perimeter validation passed — 26 rules, all OK")


# ─── Assemble ───
doc = {
    "width": W,
    "height": H,
    "groups": {},
    "scenes": {
        "rc_main": scene_rc_main(),
        "rc_channels": scene_rc_channels(),
        "rc_trims": scene_rc_trims(),
        "rc_setup": scene_rc_setup(),
        "rc_model": scene_rc_model(),
        "rc_failsafe": scene_rc_failsafe(),
        "rc_telemetry": scene_rc_telemetry(),
        "rc_rates": scene_rc_rates(),
        "rc_mixer": scene_rc_mixer(),
    },
}

# Run perimeter validation BEFORE writing
if not validate_all(doc):
    import sys
    sys.exit(1)

with open("rc_scene.json", "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=2, ensure_ascii=False)

# Stats
total = sum(len(s["widgets"]) for s in doc["scenes"].values())
print(f"Generated rc_scene.json: {len(doc['scenes'])} scenes, {total} widgets")
for name, scene in doc["scenes"].items():
    print(f"  {name}: {len(scene['widgets'])} widgets")
