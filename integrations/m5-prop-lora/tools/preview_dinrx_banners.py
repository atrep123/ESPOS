"""Compare DinMeter status-banner design variants (READ-ONLY preview).

Renders the four device states (KLID / NABITO / PALI / STOP) across several
banner-treatment styles into one side-by-side sheet so we can pick a direction.
All styles use only LovyanGFX-portable primitives (fillRect / fillRoundRect /
fillCircle / drawString), so the winner ports straight into prop_rx.cpp.

Run:  python tools/preview_dinrx_banners.py
Out:  build/preview_dinrx/banner_styles.png
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import preview_din_rx_render as P  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

W = P.SCREEN_W
CROP_H = 40  # banner is 30px; show a little below for bottom-rule styles


def blend(c: int, bg: int, t: float) -> int:
    """Blend colour c toward bg by fraction t (t=1.0 -> bg)."""
    r, g, b = P.rgb(c)
    br, bgc, bb = P.rgb(bg)
    return P.rgb_int((
        int(r + (br - r) * t),
        int(g + (bgc - g) * t),
        int(b + (bb - b) * t),
    ))


def accent_color(view: P.View) -> int:
    """Bright, saturated colour used for dots / rules / left bars."""
    if view.status == "STOP":
        return 0x2E7BFF
    if view.mode == "fire":
        return 0xFF3B30
    if view.armed:
        return 0xFFA52E
    return 0x8FA6B2  # calm cool-grey for safe idle (not muddy mid-grey)


def _center_y(canvas: P.Canvas) -> int:
    return max(1, (P.STATUS_H - canvas.font_height(3, bold=True)) // 2)


# ---------------------------------------------------------------------------
# Style A: current (flat full-width flood) -- reference.
# ---------------------------------------------------------------------------
def style_current(canvas: P.Canvas, view: P.View) -> None:
    P.draw_status_bar(canvas, view)


# ---------------------------------------------------------------------------
# Style B: chip / pill -- dark bar, state word in a rounded chip of its colour.
# ---------------------------------------------------------------------------
def style_pill(canvas: P.Canvas, view: P.View) -> None:
    canvas.fill_rect(0, 0, W, P.STATUS_H, 0x171F29)
    canvas.draw_fast_hline(0, P.STATUS_H - 1, W, 0x090D12)

    canvas.set_text_size(3)
    txt = P.state_label(view)
    tw = canvas.text_width(txt, bold=True)
    pad = 11
    pill_w = tw + pad * 2
    pill_h = 24
    px = 7
    py = (P.STATUS_H - pill_h) // 2

    idle = not view.armed and view.mode != "fire" and view.status != "STOP"
    fill = 0x2B3A44 if idle else P.state_banner_color(view)
    text_col = 0xD3E2E8 if idle else P.banner_text_color(view)

    canvas.fill_round_rect(px, py, pill_w, pill_h, 6, fill)
    ty = py + max(0, (pill_h - canvas.font_height(3, bold=True)) // 2)
    canvas.draw_string(txt, px + pad, ty, text_col, fill, bold=True)
    P.draw_battery(canvas, view)


# ---------------------------------------------------------------------------
# Style C: left accent bar + dark tint of the state hue, label in accent colour.
# ---------------------------------------------------------------------------
def style_accent(canvas: P.Canvas, view: P.View) -> None:
    state = P.state_banner_color(view)
    acc = accent_color(view)
    bg = blend(state, P.COLOR_BG, 0.80)  # subtle dark tint of the hue

    canvas.fill_rect(0, 0, W, P.STATUS_H, bg)
    canvas.fill_rect(0, 0, 6, P.STATUS_H, acc)  # left accent bar

    canvas.set_text_size(3)
    canvas.draw_string(P.state_label(view), 16, _center_y(canvas), acc, bg, bold=True)
    P.draw_battery(canvas, view)


# ---------------------------------------------------------------------------
# Style D: state dot + bold white label + bright bottom accent rule.
# ---------------------------------------------------------------------------
def style_rule(canvas: P.Canvas, view: P.View) -> None:
    acc = accent_color(view)
    bar = 0x141B23
    canvas.fill_rect(0, 0, W, P.STATUS_H, bar)

    canvas.fill_circle(14, P.STATUS_H // 2, 5, acc)
    canvas.set_text_size(3)
    canvas.draw_string(P.state_label(view), 27, _center_y(canvas), 0xF2F5F7, bar, bold=True)
    canvas.fill_rect(0, P.STATUS_H - 3, W, 3, acc)  # bottom accent rule
    P.draw_battery(canvas, view)


# ---------------------------------------------------------------------------
# Style E: safety hybrid -- LOUD flood for armed/fire/stop, calm bar for idle.
# Keeps cross-room visibility of dangerous states; only KLID is refined.
# ---------------------------------------------------------------------------
def style_hybrid(canvas: P.Canvas, view: P.View) -> None:
    idle = not view.armed and view.mode != "fire" and view.status != "STOP"
    if idle:
        bar = 0x161D26
        canvas.fill_rect(0, 0, W, P.STATUS_H, bar)
        canvas.fill_circle(14, P.STATUS_H // 2, 5, 0x8FA6B2)
        canvas.set_text_size(3)
        canvas.draw_string("KLID", 27, _center_y(canvas), 0xCFE0E6, bar, bold=True)
        canvas.fill_rect(0, P.STATUS_H - 3, W, 3, 0x3B4A55)
    else:
        flood = P.state_banner_color(view)
        canvas.fill_rect(0, 0, W, P.STATUS_H, flood)
        # brighter top highlight + darker bottom edge = a little depth, not flat
        canvas.fill_rect(0, 0, W, 2, blend(flood, 0xFFFFFF, 0.28))
        canvas.fill_rect(0, P.STATUS_H - 2, W, 2, blend(flood, 0x000000, 0.35))
        canvas.set_text_size(3)
        canvas.draw_string(P.state_label(view), 10, _center_y(canvas),
                           P.banner_text_color(view), flood, bold=True)
    P.draw_battery(canvas, view)


STYLES = [
    ("A  Soucasny (flood)", style_current),
    ("B  Pill / chip", style_pill),
    ("C  Akcent + tint", style_accent),
    ("D  Tecka + spodni linka", style_rule),
    ("E  Hybrid (klid jemny, alarm hlasity)", style_hybrid),
]

STATES = [
    ("KLID", P.View(status="KLID", mode="idle", battery_percent=76)),
    ("NABITO", P.View(status="NABITO", mode="idle", armed=True, battery_percent=64)),
    ("PALI", P.View(status="PALI", mode="fire", battery_percent=58)),
    ("STOP", P.View(status="STOP", mode="idle", battery_percent=22)),
]


def render_cell(style_fn, view: P.View) -> Image.Image:
    canvas = P.Canvas(P.COLOR_BG)
    canvas.fill_screen(P.COLOR_BG)
    style_fn(canvas, view)
    return canvas.raw().crop((0, 0, W, CROP_H))


def main() -> None:
    out = P.ROOT / "build" / "preview_dinrx"
    out.mkdir(parents=True, exist_ok=True)

    margin = 14
    label_col = 250
    col_gap = 10
    header_h = 24
    row_gap = 18

    sheet_w = margin + label_col + len(STATES) * W + (len(STATES) - 1) * col_gap + margin
    sheet_h = margin + header_h + len(STYLES) * (CROP_H + row_gap) + margin
    sheet = Image.new("RGB", (sheet_w, sheet_h), (24, 26, 30))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype(str(P.FONT_BOLD), 15)
        small = ImageFont.truetype(str(P.FONT_REGULAR), 13)
    except OSError:
        font = small = ImageFont.load_default()

    x0 = margin + label_col
    for ci, (sname, _) in enumerate(STATES):
        cx = x0 + ci * (W + col_gap)
        draw.text((cx + W // 2 - 24, margin), sname, font=font, fill=(220, 224, 230))

    for ri, (label, style_fn) in enumerate(STYLES):
        y = margin + header_h + ri * (CROP_H + row_gap)
        draw.text((margin, y + CROP_H // 2 - 8), label, font=small, fill=(206, 224, 230))
        for ci, (_, view) in enumerate(STATES):
            cx = x0 + ci * (W + col_gap)
            sheet.paste(render_cell(style_fn, view), (cx, y))

    path = out / "banner_styles.png"
    sheet.save(path)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
