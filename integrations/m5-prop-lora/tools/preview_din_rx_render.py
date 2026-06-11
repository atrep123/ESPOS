"""Desktop PNG preview harness for the M5 DinMeter receiver UI.

This is a design/rendering harness, not firmware. It mirrors the LovyanGFX
layout in ``firmware/din-rx/src/prop_rx.cpp`` closely enough to inspect the
240x135 receiver UI on a PC.

Run:  python tools/preview_din_rx_render.py
Out:  build/preview_dinrx/*.png and build/preview_dinrx/contact.png
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field, replace
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


# ----------------------------------------------------------------------------
# Constants mirrored from firmware/din-rx/src/prop_rx.cpp.
# ----------------------------------------------------------------------------

S = 4  # supersample factor for antialiasing
SCREEN_W = 240
SCREEN_H = 135
# Vertical budget (SCREEN_H=135) -- council "decluttered hybrid":
#   STAV 0..28 | EFEKT frame 30..89 (plot 36..80, palette merged at the 0% line) | 2 rows 93..129
# + a 4px state-colour SPINE down the left edge (always the state colour) for angle/peripheral legibility.
_THEME = json.loads((Path(__file__).resolve().parent / "m5_theme.json").read_text(encoding="utf-8"))
_C = {k: int(v, 16) for k, v in _THEME["colors"].items()}
_L = _THEME["layout"]

STATUS_H = _L["STATUS_H"]
SPINE_W = _L["SPINE_W"]
PLOT_X = _L["PLOT_X"]
PLOT_Y = _L["PLOT_Y"]
PLOT_W = _L["PLOT_W"]
PLOT_H = _L["PLOT_H"]
EFEKT_TOP = _L["EFEKT_TOP"]
EFEKT_BOT = _L["EFEKT_BOT"]
PLOT_TOP = _L["PLOT_TOP"]
PLOT_PEAK_PAD = _L["PLOT_PEAK_PAD"]
PALETTE_Y = _L["PALETTE_Y"]
ROW_Y = _L["ROW_Y"]
ROW_H = _L["ROW_H"]
ROW_VISIBLE = _L["ROW_VISIBLE"]
PLOT_MAX_CYCLES = _L["PLOT_MAX_CYCLES"]

LED_COUNT = 4
DEFAULT_PERIOD_MS = 1000
DEFAULT_REPEAT = 1

EFFECT_SHAPE_SINE2 = 0
EFFECT_SHAPE_SQUARE = 1
EFFECT_SHAPE_SAWTOOTH = 2
EFFECT_SHAPE_TRIANGLE = 3
EFFECT_SHAPE_EXP = 4

COLOR_BG = _C["COLOR_BG"]
WHITE = 0xFFFFFF
COLOR_TEXT = _C["COLOR_TEXT"]
COLOR_MUTED = _C["COLOR_MUTED"]
COLOR_GOOD = _C["COLOR_GOOD"]
COLOR_WARN = _C["COLOR_WARN"]
COLOR_BAD = _C["COLOR_BAD"]
COLOR_BLUE = _C["COLOR_BLUE"]
COLOR_KLID = _C["COLOR_KLID"]
COLOR_LED_UI = (COLOR_BAD, COLOR_GOOD, COLOR_BLUE, COLOR_WARN)
CHIP_KLID_BG = _C["CHIP_KLID_BG"]
CHIP_KLID_TEXT = _C["CHIP_KLID_TEXT"]
COLOR_TEAL = _C["COLOR_TEAL"]


def apply_theme(theme: dict) -> None:
    """Runtime override of the theme constants for the live Studio preview.

    `theme` matches m5_theme.json: {"colors": {NAME: "0xRRGGBB"|int}, "layout": {NAME: int}}.
    Missing/unknown keys keep their current value; derived constants are recomputed.
    A no-op (pixel-identical) when called with the values already in m5_theme.json.
    """
    g = globals()
    for name, value in (theme.get("colors") or {}).items():
        if name in g:
            g[name] = int(value, 16) if isinstance(value, str) else int(value)
    for name, value in (theme.get("layout") or {}).items():
        if name in g:
            g[name] = int(value)
    g["COLOR_LED_UI"] = (g["COLOR_BAD"], g["COLOR_GOOD"], g["COLOR_BLUE"], g["COLOR_WARN"])


ROOT = Path(__file__).resolve().parents[1]
FONT_REGULAR = ROOT / "firmware/dial-tx/components/lvgl/scripts/built_in_font/DejaVuSans.ttf"
FONT_BOLD = ROOT / "firmware/dial-tx/components/lvgl/scripts/built_in_font/Montserrat-Medium.ttf"


def rgb(c: int) -> tuple[int, int, int]:
    return ((c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF)


def rgb_int(color: tuple[int, int, int]) -> int:
    r, g, b = color
    return (r << 16) | (g << 8) | b


def dim_rgb(color: int, level: int) -> int:
    r, g, b = rgb(color)
    return rgb_int((r * level // 255, g * level // 255, b * level // 255))


def clamp_byte(value: int) -> int:
    return max(0, min(255, int(value)))


def clamp_percent(value: int) -> int:
    return max(0, min(100, int(value)))


def _font(text_size: int, bold: bool = False, mono: bool = False) -> ImageFont.ImageFont:
    # LovyanGFX Font0 textSize 2/3 is compact. These sizes approximate that
    # density while keeping PIL output legible on the 240x135 canvas.
    px = {1: 8, 2: 15, 3: 23}.get(text_size, max(8, text_size * 8))
    if mono:
        candidates = [
            "DejaVuSansMono-Bold.ttf" if bold else "DejaVuSansMono.ttf",
            str(FONT_BOLD if bold else FONT_REGULAR),
            str(FONT_REGULAR),
        ]
    else:
        candidates = [
            str(FONT_BOLD if bold else FONT_REGULAR),
            str(FONT_REGULAR),
            "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, px * S)
        except OSError:
            continue
    return ImageFont.load_default()


# ----------------------------------------------------------------------------
# Canvas: supersampled wrapper exposing LovyanGFX-like primitives.
# ----------------------------------------------------------------------------


class Canvas:
    def __init__(self, bg: int = COLOR_BG):
        self.img = Image.new("RGB", (SCREEN_W * S, SCREEN_H * S), rgb(bg))
        self.d = ImageDraw.Draw(self.img)
        self.text_size = 1
        self.text_color = COLOR_TEXT
        self.text_bg = bg

    def fill_screen(self, color: int) -> None:
        self.d.rectangle([0, 0, SCREEN_W * S, SCREEN_H * S], fill=rgb(color))

    def fill_rect(self, x: int, y: int, w: int, h: int, color: int) -> None:
        self.d.rectangle([x * S, y * S, (x + w) * S - 1, (y + h) * S - 1], fill=rgb(color))

    def draw_rect(self, x: int, y: int, w: int, h: int, color: int, width: int = 1) -> None:
        self.d.rectangle(
            [x * S, y * S, (x + w) * S - 1, (y + h) * S - 1],
            outline=rgb(color),
            width=max(1, width * S),
        )

    def fill_round_rect(self, x: int, y: int, w: int, h: int, r: int, color: int) -> None:
        self.d.rounded_rectangle(
            [x * S, y * S, (x + w) * S - 1, (y + h) * S - 1],
            radius=r * S,
            fill=rgb(color),
        )

    def draw_fast_hline(self, x: int, y: int, w: int, color: int) -> None:
        self.line(x, y, x + w - 1, y, color)

    def draw_fast_vline(self, x: int, y: int, h: int, color: int) -> None:
        self.line(x, y, x, y + h - 1, color)

    def line(self, x0: int, y0: int, x1: int, y1: int, color: int, width: int = 1) -> None:
        self.d.line([x0 * S, y0 * S, x1 * S, y1 * S], fill=rgb(color), width=max(1, width * S))

    def polygon(self, points: tuple[tuple[int, int], ...], fill: int, outline: int | None = None) -> None:
        scaled = [(x * S, y * S) for x, y in points]
        self.d.polygon(scaled, fill=rgb(fill))
        if outline is not None:
            self.d.line(scaled + [scaled[0]], fill=rgb(outline), width=max(1, S))

    def fill_circle(self, cx: int, cy: int, r: int, color: int) -> None:
        self.d.ellipse(
            [(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S],
            fill=rgb(color),
        )

    def set_text_size(self, size: int) -> None:
        self.text_size = size

    def set_text_color(self, fg: int, bg: int = COLOR_BG) -> None:
        self.text_color = fg
        self.text_bg = bg

    def text_width(self, text: str, size: int | None = None, bold: bool = False, mono: bool = False) -> int:
        f = _font(size or self.text_size, bold=bold, mono=mono)
        bbox = self.d.textbbox((0, 0), text, font=f)
        return int(math.ceil((bbox[2] - bbox[0]) / S))

    def font_height(self, size: int | None = None, bold: bool = False, mono: bool = False) -> int:
        f = _font(size or self.text_size, bold=bold, mono=mono)
        bbox = self.d.textbbox((0, 0), "Hg", font=f)
        return int(math.ceil((bbox[3] - bbox[1]) / S))

    def draw_string(
        self,
        text: str,
        x: int,
        y: int,
        fg: int | None = None,
        bg: int | None = None,
        bold: bool = False,
        mono: bool = False,
    ) -> None:
        color = self.text_color if fg is None else fg
        background = self.text_bg if bg is None else bg
        f = _font(self.text_size, bold=bold, mono=mono)
        if background is not None:
            bbox = self.d.textbbox((x * S, y * S), text, font=f)
            self.d.rectangle(bbox, fill=rgb(background))
        self.d.text((x * S, y * S), text, font=f, fill=rgb(color))

    def draw_right_string(
        self,
        text: str,
        right: int,
        y: int,
        fg: int,
        bg: int = COLOR_BG,
        bold: bool = False,
        mono: bool = False,
    ) -> None:
        self.set_text_color(fg, bg)
        self.draw_string(text, right - self.text_width(text, bold=bold, mono=mono), y, bold=bold, mono=mono)

    def draw_center_string(
        self,
        text: str,
        cx: int,
        y: int,
        fg: int,
        bg: int = COLOR_BG,
        bold: bool = False,
        mono: bool = False,
    ) -> None:
        self.draw_string(text, cx - self.text_width(text, bold=bold, mono=mono) // 2, y, fg, bg, bold=bold, mono=mono)

    def draw_string_vcenter(
        self,
        text: str,
        x: int,
        cy: int,
        fg: int,
        bold: bool = False,
        mono: bool = False,
    ) -> None:
        """Left-align at x, vertically centre the glyph INK box on screen row cy.

        PIL's default anchor leaves ascender padding above the caps, so a plain
        draw_string sits visually low inside a chip; this measures the real ink
        bbox of *this* text and centres that instead.
        """
        f = _font(self.text_size, bold=bold, mono=mono)
        bbox = self.d.textbbox((0, 0), text, font=f)
        ink_top = bbox[1]
        ink_h = bbox[3] - bbox[1]
        ty = int(round(cy * S - ink_h / 2 - ink_top))
        self.d.text((x * S, ty), text, font=f, fill=rgb(fg))

    def raw(self) -> Image.Image:
        return self.img.resize((SCREEN_W, SCREEN_H), Image.Resampling.LANCZOS)


# ----------------------------------------------------------------------------
# View model and effect math.
# ----------------------------------------------------------------------------


@dataclass(frozen=True)
class EffectConfig:
    pre_trigger: bool = False
    shape: int = EFFECT_SHAPE_SINE2
    shape_param: int = 50
    period_ms: int = DEFAULT_PERIOD_MS
    repeat: int = DEFAULT_REPEAT
    intensity: int = 100
    led_delay_ms: tuple[int, ...] = (0, 80, 160, 240)


@dataclass(frozen=True)
class View:
    status: str = "KLID"
    mode: str = "idle"  # idle / preview / fire
    armed: bool = False
    config: EffectConfig = field(default_factory=EffectConfig)
    battery_percent: int = 72
    rows_visible: bool = False
    row_scroll: int = 0
    selected_row: int = 0
    editing: bool = False
    selected_delay_led: int = 0
    elapsed_ms: int = 0
    has_palette: bool = True
    palette_fade: bool = True
    palette: tuple[tuple[int, int, int], ...] = (
        (255, 40, 35),
        (255, 180, 20),
        (35, 220, 95),
        (45, 125, 255),
    )
    dial_colors: tuple[tuple[int, int, int], ...] = (
        (255, 40, 35),
        (35, 220, 95),
        (45, 125, 255),
        (255, 180, 20),
    )


def max_delay_ms(config: EffectConfig) -> int:
    return max(config.led_delay_ms)


def finite_effect_total_ms(config: EffectConfig) -> tuple[bool, int]:
    if config.repeat == 0:
        return False, 0
    return True, max_delay_ms(config) + config.repeat * config.period_ms


def plot_has_multiplier(config: EffectConfig) -> bool:
    return config.repeat == 0 or config.repeat > PLOT_MAX_CYCLES


def plot_visible_cycles(config: EffectConfig) -> int:
    if plot_has_multiplier(config):
        return PLOT_MAX_CYCLES
    return max(1, config.repeat)


def plot_span_pixels(config: EffectConfig) -> int:
    return (PLOT_W * 74) // 100 if plot_has_multiplier(config) else PLOT_W


def plot_duration_ms(config: EffectConfig) -> int:
    return max(1, max_delay_ms(config) + plot_visible_cycles(config) * config.period_ms)


def waveform_level(local_ms: int, period_ms: int, shape: int, param: int) -> int:
    x = 0.0 if period_ms == 0 else float(local_ms % period_ms) / float(period_ms)

    if shape == EFFECT_SHAPE_SQUARE:
        duty = max(5, min(95, int(param))) / 100.0
        value = 1.0 if x < duty else 0.0
    elif shape == EFFECT_SHAPE_SAWTOOTH:
        value = x if param >= 50 else 1.0 - x
    elif shape == EFFECT_SHAPE_TRIANGLE:
        value = 2.0 * x if x < 0.5 else 2.0 * (1.0 - x)
    elif shape == EFFECT_SHAPE_EXP:
        k = 2.0 + (clamp_percent(param) / 100.0) * 8.0
        value = math.exp(-k * x)
    else:
        value = math.sin(math.pi * x)
        value *= value

    return clamp_byte(round(max(0.0, min(1.0, value)) * 255.0))


def plot_floor_level(config: EffectConfig) -> int:
    return 41 if config.pre_trigger else 0


def plot_level_at(config: EffectConfig, led: int, elapsed_ms: int) -> int:
    floor = plot_floor_level(config)
    if led < 0 or led >= LED_COUNT or elapsed_ms < config.led_delay_ms[led]:
        return floor

    local_ms = elapsed_ms - config.led_delay_ms[led]
    led_draw_ms = plot_visible_cycles(config) * config.period_ms
    if local_ms >= led_draw_ms:
        return floor

    hump = waveform_level(local_ms, config.period_ms, config.shape, config.shape_param) * config.intensity // 100
    return floor + ((255 - floor) * hump) // 255


def lerp_hsv(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    import colorsys

    ah, a_s, a_v = colorsys.rgb_to_hsv(a[0] / 255.0, a[1] / 255.0, a[2] / 255.0)
    bh, b_s, b_v = colorsys.rgb_to_hsv(b[0] / 255.0, b[1] / 255.0, b[2] / 255.0)
    dh = bh - ah
    if dh > 0.5:
        dh -= 1.0
    if dh < -0.5:
        dh += 1.0
    h = (ah + dh * t) % 1.0
    s = a_s + (b_s - a_s) * t
    v = a_v + (b_v - a_v) * t
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))


def palette_color_at(view: View, local_ms: int, period_ms: int) -> tuple[int, int, int]:
    if not view.palette:
        return (255, 255, 255)
    if len(view.palette) == 1:
        return view.palette[0]

    k = 0 if period_ms == 0 else local_ms // period_ms
    if not view.palette_fade:
        return view.palette[k % len(view.palette)]

    frac = 0.0 if period_ms == 0 else float(local_ms % period_ms) / float(period_ms)
    return lerp_hsv(view.palette[k % len(view.palette)], view.palette[(k + 1) % len(view.palette)], frac)


def ui_color_for_led(view: View, led: int) -> int:
    if 0 <= led < len(view.dial_colors):
        return rgb_int(view.dial_colors[led])
    return COLOR_LED_UI[max(0, min(LED_COUNT - 1, led))]


def full_luma(color: int) -> int:
    r, g, b = rgb(color)
    peak = max(r, g, b)
    if peak <= 0:
        return color
    scale = 255.0 / peak
    return rgb_int((clamp_byte(r * scale), clamp_byte(g * scale), clamp_byte(b * scale)))


# ----------------------------------------------------------------------------
# Render pieces mirrored from prop_rx.cpp.
# ----------------------------------------------------------------------------


def state_banner_color(view: View) -> int:
    if view.status == "STOP":
        return COLOR_BLUE
    if view.mode == "fire":
        return COLOR_BAD
    if view.armed:
        return COLOR_WARN
    return COLOR_KLID


def state_spine_color(view: View) -> int:
    # The left spine echoes the state colour. KLID gets a POSITIVE green (not the dead
    # slate of 'no signal') so 'idle-safe' reads peripherally / from an angle -- a blank
    # dark screen otherwise reads as 'broken' rather than 'safe' (council: Opus+Copilot).
    if (not view.armed) and view.mode != "fire" and view.status != "STOP":
        return COLOR_GOOD
    return state_banner_color(view)


def state_label(view: View) -> str:
    if view.status == "STOP":
        return "STOP"
    if view.mode == "fire":
        return "PÁLÍ"
    if view.armed:
        return "NABITO"
    return "KLID"


def battery_color(view: View) -> int:
    if view.battery_percent > 40:
        return COLOR_GOOD
    if view.battery_percent >= 20:
        return COLOR_WARN
    return COLOR_BAD


def draw_battery(canvas: Canvas, view: View) -> None:
    bar_w = 32
    bar_h = 14
    bar_x = SCREEN_W - 9 - bar_w  # extra inset clears the 4px firing border on the right
    bar_y = 9
    # In the colour-flood states (NABITO/PALI/STOP) the bare gauge blends into the wash and
    # a low-charge red/amber fill reads as 'danger' on the flood (council: Gemini, every
    # pass). Seat it on a dark backing chip AND use a neutral WHITE fill there -- charge is
    # still shown by fill WIDTH; the green/amber/red charge colour only carries meaning in
    # KLID (no flood), where it is genuinely useful.
    flood = view.armed or view.mode == "fire" or view.status == "STOP"
    if flood:
        canvas.fill_round_rect(bar_x - 4, bar_y - 3, bar_w + 7, bar_h + 6, 3, 0x0A0C10)
    canvas.draw_rect(bar_x, bar_y, bar_w, bar_h, WHITE)
    canvas.fill_rect(bar_x + bar_w, bar_y + 4, 2, bar_h - 8, WHITE)
    fill_w = max(0, min(bar_w - 4, (view.battery_percent * (bar_w - 4)) // 100))
    canvas.fill_rect(bar_x + 2, bar_y + 2, fill_w, bar_h - 4, WHITE if flood else battery_color(view))


def banner_text_color(view: View) -> int:
    # High-contrast label colour per banner background.
    if view.status == "STOP" or view.mode == "fire":
        return WHITE        # on blue / red
    if view.armed:
        return 0x0A0C10     # dark on amber (NABITO)
    return WHITE            # on dark-grey (KLID)


def draw_warning_glyph(canvas: Canvas, cx: int, cy: int, size: int, tri_color: int,
                       bang_color: int, solid: bool = True) -> None:
    # Compact hazard mark (apex-up triangle + '!'). solid=True (PALI/firing) = FILLED
    # triangle; solid=False (NABITO/armed) = HOLLOW outline -- a NON-COLOUR differentiator
    # between armed and firing for colour-blind / across-a-dark-room safety, beyond the
    # amber-vs-red hue alone (council r4 operator lens: Opus). Firmware adds a PALI pulse.
    h = int(size * 1.6)
    pts = ((cx, cy - h // 2), (cx - size, cy + h // 2), (cx + size, cy + h // 2))
    if solid:
        canvas.polygon(pts, tri_color)
    else:
        canvas.line(pts[0][0], pts[0][1], pts[1][0], pts[1][1], tri_color, width=2)
        canvas.line(pts[1][0], pts[1][1], pts[2][0], pts[2][1], tri_color, width=2)
        canvas.line(pts[2][0], pts[2][1], pts[0][0], pts[0][1], tri_color, width=2)
    canvas.set_text_size(1)
    bw = canvas.text_width("!", bold=True)
    canvas.draw_string_vcenter("!", cx - bw // 2, cy + 1, bang_color if solid else tri_color, bold=True)


def draw_status_bar(canvas: Canvas, view: View) -> None:
    txt = state_label(view)
    canvas.set_text_size(3)

    # SAFETY: the dangerous LIVE states (NABITO = armed, PALI = firing) get a LOUD
    # full-width colour flood + hazard glyph so they are unmistakable across a room
    # (Gemini jury + Filip flagged the chip as not alarming enough). The calm/safe
    # states (KLID idle, STOP latched) keep the clean floating chip.
    if view.armed or view.mode == "fire":
        flood = state_banner_color(view)
        canvas.fill_rect(0, 0, SCREEN_W, STATUS_H, flood)
        draw_warning_glyph(canvas, 16, STATUS_H // 2, 8, WHITE, 0x0A0C10, solid=(view.mode == "fire"))
        canvas.draw_string_vcenter(txt, 30, STATUS_H // 2, banner_text_color(view), bold=True)
        draw_battery(canvas, view)
        return

    # STOP (e-stopped / latched): full-width BLUE flood so a room-wide "someone hit
    # E-STOP" reads instantly, but NO hazard glyph and NO screen border -- it is a
    # SAFE latched state, one visual tier below the live-danger amber/red floods.
    if view.status == "STOP":
        canvas.fill_rect(0, 0, SCREEN_W, STATUS_H, COLOR_BLUE)
        canvas.draw_string_vcenter(txt, 12, STATUS_H // 2, WHITE, bold=True)
        # "ZAJISTENO" caption: a Czech semantic bridge so STOP reads as a held/latched
        # SAFE state, not just an emergency shout (council: Opus+Copilot). Keep the
        # Czech diacritics here for the same semantic polish as the other key labels.
        stop_w = canvas.text_width(txt, bold=True)
        canvas.set_text_size(1)
        canvas.draw_string_vcenter("ZAJIŠTĚNO", 12 + stop_w + 9, STATUS_H // 2, 0xCFE6FF, bold=True)
        draw_battery(canvas, view)
        return

    # KLID (idle/safe): green-slate chip + a small green 'ready' LED so the safe state has
    # a POSITIVE identity (council: a blank dark screen reads as 'broken', not 'safe').
    canvas.fill_rect(0, 0, SCREEN_W, STATUS_H, COLOR_BG)
    pad_x = 11
    chip_x = 8
    chip_y = 6
    chip_h = 20
    dot_r = 4
    dot_gap = 7
    chip_w = pad_x * 2 + dot_r * 2 + dot_gap + canvas.text_width(txt, bold=True)
    cy = chip_y + chip_h // 2
    canvas.fill_round_rect(chip_x, chip_y, chip_w, chip_h, 6, CHIP_KLID_BG)
    canvas.fill_circle(chip_x + pad_x + dot_r, cy, dot_r, COLOR_GOOD)
    canvas.draw_string_vcenter(txt, chip_x + pad_x + dot_r * 2 + dot_gap, cy, CHIP_KLID_TEXT, bold=True)
    draw_battery(canvas, view)


def draw_thick_line(canvas: Canvas, x0: int, y0: int, x1: int, y1: int, color: int) -> None:
    canvas.line(x0, y0, x1, y1, color, width=3)
    canvas.fill_circle(x1, y1, 1.5, color)  # round joints so square-wave corners aren't chopped off


def draw_palette_swatch(canvas: Canvas, view: View) -> None:
    cell_w = 16
    cell_h = 5
    gap = 2
    x0 = PLOT_X
    cell_y = PALETTE_Y                           # palette lane, just below the 0% floor line
    tag = "PŘECHOD" if view.palette_fade else "SKOK"
    accent = COLOR_TEAL if view.palette_fade else COLOR_WARN    # teal = fade, amber = step

    for i, color in enumerate(view.palette):
        cell_x = x0 + i * (cell_w + gap)
        canvas.fill_rect(cell_x, cell_y, cell_w, cell_h, rgb_int(color))
        canvas.draw_rect(cell_x, cell_y, cell_w, cell_h, 0x0A0C10)

    # Fade/step pill grouped right AFTER the swatch cells as one legend strip. Right-aligning
    # it collided with the xN multiplier divider and sat on the 0% floor line (council r3:
    # Opus); the backing is a dark tint of the accent so it reads as a real chip, not
    # floating text, even at 240x135 (council r3: Copilot).
    canvas.set_text_size(1)
    tag_w = canvas.text_width(tag, bold=True)
    pill_w = tag_w + 10
    pill_h = 8
    pill_x = min(x0 + len(view.palette) * (cell_w + gap) + 5, PLOT_X + PLOT_W - pill_w)
    pill_y = cell_y - 1
    canvas.fill_round_rect(pill_x, pill_y, pill_w, pill_h, 2, dim_rgb(accent, 55))
    canvas.draw_string_vcenter(tag, pill_x + 5, pill_y + pill_h // 2, accent, bold=True)


def draw_plot(canvas: Canvas, view: View) -> None:
    config = view.config
    canvas.fill_rect(0, STATUS_H, SCREEN_W, ROW_Y - STATUS_H, COLOR_BG)
    top = PLOT_TOP
    baseline = PLOT_Y + PLOT_H
    peak_y = top + PLOT_PEAK_PAD            # wave maxes out BELOW the 100% line, never on it
    height = baseline - peak_y
    span = plot_span_pixels(config)
    duration = plot_duration_ms(config)
    more = plot_has_multiplier(config)
    firing = view.mode == "fire"

    # Gridlines were near-invisible (council: Opus/Copilot/Gemini). Lift contrast and make
    # the 0% FLOOR brighter than the 100% CEILING so 'bottom vs top' is unambiguous.
    grid_top = dim_rgb(COLOR_TEXT if firing else COLOR_MUTED, 150 if firing else 120)
    grid_base = dim_rgb(COLOR_TEXT if firing else COLOR_MUTED, 205 if firing else 175)
    canvas.draw_fast_hline(PLOT_X, top, PLOT_W, grid_top)        # 100% ceiling
    canvas.draw_fast_hline(PLOT_X, baseline, PLOT_W, grid_base)  # 0% floor

    floor = plot_floor_level(config)
    if floor > 0:
        floor_y = baseline - (floor * height // 255)
        canvas.draw_fast_hline(PLOT_X, floor_y, span, dim_rgb(COLOR_WARN, 150))
        canvas.draw_fast_hline(PLOT_X, floor_y - 1, span, dim_rgb(COLOR_WARN, 105))

    samples = max(2, span)
    led_draw_ms = plot_visible_cycles(config) * config.period_ms
    dim = dim_rgb(COLOR_TEXT if firing else COLOR_MUTED, 80 if firing else 70)

    def seg_at(led: int, sample_ms: int) -> tuple[bool, int]:
        """(is_active_hump, colour). The hump uses the LED's IDENTITY colour so the four
        curves are tellable apart (red/green/blue/amber -- matching the Dial LED dots and
        the led_delays page); the effect palette is shown separately in the swatch."""
        if sample_ms < config.led_delay_ms[led]:
            return False, dim
        local_ms = sample_ms - config.led_delay_ms[led]
        if local_ms >= led_draw_ms:
            return False, dim
        return True, ui_color_for_led(view, led)

    # Two layers, so a later LED's flat 'off' baseline never lands on top of an
    # earlier LED's coloured hump (that caused the 4th curve's start to poke out
    # in the wrong layer): pass 1 = all dim/off segments, pass 2 = coloured humps.
    # The hump pass runs in reverse LED order so the earliest / most-advanced curve
    # stays in front and a just-starting later curve emerges from behind.
    for want_active in (False, True):
        led_seq = range(LED_COUNT - 1, -1, -1) if want_active else range(LED_COUNT)
        for led in led_seq:
            previous_x = PLOT_X
            previous_y = baseline - (plot_level_at(config, led, 0) * height // 255)
            for sample in range(1, samples + 1):
                sample_ms = sample * duration // samples
                x = PLOT_X + sample * span // samples
                level = plot_level_at(config, led, sample_ms)
                y = baseline - (level * height // 255)
                active, seg_color = seg_at(led, sample_ms)
                if firing and active:
                    # boost ONLY the live humps; brightening the dim OFF baseline too made a
                    # white smear along the 0% floor in PALI (council r3: Opus spotted it).
                    seg_color = full_luma(seg_color)
                if active == want_active:
                    draw_thick_line(canvas, previous_x, previous_y, x, y, seg_color)
                previous_x = x
                previous_y = y

    if more:
        divider_x = PLOT_X + span + 3
        divider_color = dim_rgb(COLOR_MUTED, 150)
        for y in range(top, baseline, 6):
            canvas.draw_fast_vline(divider_x, y, min(3, baseline - y), divider_color)
        mult = "xINF" if config.repeat == 0 else f"x{config.repeat}"
        canvas.set_text_size(2)
        canvas.set_text_color(COLOR_TEXT, COLOR_BG)
        canvas.draw_string(mult, divider_x + 6, top + (height - 16) // 2)

    if view.has_palette and not firing:
        draw_palette_swatch(canvas, view)

    draw_playhead(canvas, view)


PARAM_ROWS = ("Pre", "Period", "Shape", "ShapeParam", "Repeat", "Intensity", "LedDelays", "Preview")
LABEL_DIM = dim_rgb(COLOR_TEXT, 150)
SELECT_BG = 0x26313B


def param_label(row: int, config: EffectConfig) -> str:
    key = PARAM_ROWS[row]
    if key == "Pre":
        return "PŘED"
    if key == "Period":
        return "DOBA"
    if key == "Shape":
        return "TVAR"
    if key == "ShapeParam":
        if config.shape == EFFECT_SHAPE_SQUARE:
            return "DUTY"
        if config.shape == EFFECT_SHAPE_SAWTOOTH:
            return "SMĚR"
        if config.shape == EFFECT_SHAPE_EXP:
            return "OSTROST"
        return "-"
    if key == "Repeat":
        return "OPAK"
    if key == "Intensity":
        return "JAS"
    if key == "LedDelays":
        return "LED"
    if key == "Preview":
        return "START"
    return "-"


def param_value(row: int, config: EffectConfig) -> str:
    key = PARAM_ROWS[row]
    if key == "Pre":
        return "SVIT" if config.pre_trigger else "VYP"
    if key == "Period":
        return f"{config.period_ms}ms"
    if key == "Shape":
        return {
            EFFECT_SHAPE_SQUARE: "HRANA",
            EFFECT_SHAPE_SAWTOOTH: "PILA",
            EFFECT_SHAPE_TRIANGLE: "TROJÚH",
            EFFECT_SHAPE_EXP: "EXP",
            EFFECT_SHAPE_SINE2: "SIN2",
        }.get(config.shape, "SIN2")
    if key == "ShapeParam":
        if config.shape == EFFECT_SHAPE_SQUARE:
            return f"{max(5, min(95, config.shape_param))}%"
        if config.shape == EFFECT_SHAPE_SAWTOOTH:
            return "NAHORU" if config.shape_param >= 50 else "DOLŮ"
        if config.shape == EFFECT_SHAPE_EXP:
            return f"{config.shape_param}"
        return "-"
    if key == "Repeat":
        return "INF" if config.repeat == 0 else f"{config.repeat}x"
    if key == "Intensity":
        return f"{config.intensity}%"
    if key == "LedDelays":
        return "prodlevy >"
    if key == "Preview":
        return "náhled"
    return "-"


def param_slider_fraction(row: int, config: EffectConfig) -> float | None:
    key = PARAM_ROWS[row]
    if key == "Pre":
        return 1.0 if config.pre_trigger else 0.0
    if key == "Period":
        return min(1.0, max(0.0, config.period_ms / 3000.0))
    if key == "Shape":
        return min(1.0, max(0.0, config.shape / 4.0))
    if key == "ShapeParam":
        return clamp_percent(config.shape_param) / 100.0
    if key == "Repeat":
        return 1.0 if config.repeat == 0 else min(1.0, max(0.0, config.repeat / 6.0))
    if key == "Intensity":
        return clamp_percent(config.intensity) / 100.0
    if key == "LedDelays":
        return min(1.0, max_delay_ms(config) / 500.0)
    return None


def draw_value_row(
    canvas: Canvas,
    y: int,
    label: str,
    value: str,
    selected: bool,
    editing: bool,
    fraction: float | None,
    dot_color: int,
) -> None:
    canvas.fill_rect(0, y, SCREEN_W, ROW_H, COLOR_BG)
    edit = selected and editing
    if selected:
        canvas.fill_rect(4, y, SCREEN_W - 8, ROW_H - 2, SELECT_BG)
    if edit:
        # EDIT mode = a full amber BOX (not just a thin bar) so 'turning now changes THIS
        # value' is never mistaken for 'turning moves the selection' -- on NABITO an
        # accidental value change is a misfire (council r4 operator lens: Opus).
        canvas.draw_rect(4, y, SCREEN_W - 8, ROW_H - 2, COLOR_WARN, width=2)

    bg = SELECT_BG if selected else COLOR_BG
    mid_y = y + ROW_H // 2
    canvas.set_text_size(1)
    canvas.draw_string(label, 11, y + 4, LABEL_DIM, bg)

    track_x = 78
    track_w = 82
    if fraction is not None:
        frac = max(0.0, min(1.0, fraction))
        # Real fill bar: the FILLED portion (in the param's colour) encodes the value, knob
        # at the end. A slider must communicate its value, not be a decorative dot pair
        # (council: Opus; Filip's 'functional depth over decorative noise').
        bar_y = mid_y - 1
        canvas.fill_rect(track_x, bar_y, track_w, 3, dim_rgb(COLOR_MUTED, 55))
        fill_w = int(frac * track_w)
        if fill_w > 0:
            canvas.fill_rect(track_x, bar_y, fill_w, 3, dot_color)
        knob_x = track_x + fill_w
        canvas.fill_circle(knob_x, mid_y, 5 if selected else 4, COLOR_TEXT if selected else dot_color)

    canvas.set_text_size(2)
    val_color = COLOR_WARN if edit else COLOR_TEXT
    if edit:
        # up/down carets beside the value: 'the encoder is turning THIS value right now'.
        vw = canvas.text_width(value, bold=True, mono=True)
        cxi = SCREEN_W - 8 - vw - 9
        canvas.polygon(((cxi, mid_y - 6), (cxi - 4, mid_y - 1), (cxi + 4, mid_y - 1)), COLOR_WARN)
        canvas.polygon(((cxi, mid_y + 6), (cxi - 4, mid_y + 1), (cxi + 4, mid_y + 1)), COLOR_WARN)
    canvas.draw_right_string(value, SCREEN_W - 8, y + 1, val_color, bg, bold=True, mono=True)


def draw_main_rows(canvas: Canvas, view: View) -> None:
    canvas.fill_rect(0, ROW_Y, SCREEN_W, SCREEN_H - ROW_Y, COLOR_BG)
    for visible in range(ROW_VISIBLE):
        row = view.row_scroll + visible
        if row >= len(PARAM_ROWS):
            continue
        draw_main_row(canvas, view, row, ROW_Y + visible * ROW_H)


def draw_main_row(canvas: Canvas, view: View, row: int, y: int) -> None:
    selected = row == view.selected_row
    dot_color = ui_color_for_led(view, row % LED_COUNT)
    draw_value_row(
        canvas,
        y,
        param_label(row, view.config),
        param_value(row, view.config),
        selected,
        view.editing,
        param_slider_fraction(row, view.config),
        dot_color,
    )


def draw_main_info_area(canvas: Canvas, view: View) -> None:
    canvas.fill_rect(0, ROW_Y, SCREEN_W, SCREEN_H - ROW_Y, COLOR_BG)
    if view.mode == "fire":
        draw_firing_readout(canvas, view)
        return
    if view.mode == "preview":
        return
    draw_plot_readout(canvas, view.config)


def total_time_text(config: EffectConfig) -> str:
    finite, total_ms = finite_effect_total_ms(config)
    if finite:
        tenths = (total_ms + 50) // 100
        return f"{tenths // 10}.{tenths % 10}s"
    return "nekon."


def draw_firing_readout(canvas: Canvas, view: View) -> None:
    rows = (
        ("JAS", f"{view.config.intensity}%", clamp_percent(view.config.intensity) / 100.0, COLOR_WARN),
        ("DOBA", f"{view.config.period_ms}ms", min(1.0, view.config.period_ms / 3000.0), COLOR_BLUE),
        ("Celkem", total_time_text(view.config), None, COLOR_TEXT),
    )
    for idx, (label, value, fraction, dot_color) in enumerate(rows):
        draw_value_row(canvas, ROW_Y + idx * ROW_H, label, value, False, False, fraction, dot_color)


def draw_plot_readout(canvas: Canvas, config: EffectConfig) -> None:
    # Idle readout as a labelled stat (caption + value) so it reads as deliberate info,
    # not a giant lone number competing with the STAV chip (council: Gemini).
    value = total_time_text(config)
    canvas.set_text_size(1)
    canvas.draw_center_string("CELKOVÁ DOBA", SCREEN_W // 2, 95, dim_rgb(COLOR_MUTED, 210), COLOR_BG)
    canvas.set_text_size(3)
    canvas.draw_center_string(value, SCREEN_W // 2, 104, COLOR_TEXT, COLOR_BG)


def draw_playhead(canvas: Canvas, view: View) -> None:
    if view.mode not in ("preview", "fire"):
        return
    config = view.config
    duration = plot_duration_ms(config)
    elapsed = view.elapsed_ms % duration if duration > 0 else 0
    top = PLOT_TOP
    baseline = PLOT_Y + PLOT_H
    span = plot_span_pixels(config)
    x = PLOT_X + elapsed * span // max(1, duration)
    if view.mode == "fire":
        # Slim white head with a dark halo so it reads over the red flood WITHOUT occluding
        # the curves it tracks (council: Opus -- was a 4px bar + big funnel cap). The
        # across-the-room 'firing' signal is the red flood/border, not this fine cursor.
        canvas.line(x, top - 7, x, baseline + 3, 0x0A0C10, width=3)   # dark halo
        canvas.line(x, top - 7, x, baseline + 3, 0xFFFFFF, width=1)   # 1px white core
        canvas.polygon(((x - 4, top - 10), (x + 4, top - 10), (x, top - 4)), 0xFFFFFF, outline=0x0A0C10)
    else:
        canvas.draw_fast_vline(x, top - 2, baseline - top + 5, COLOR_TEXT)


def draw_delay_timeline(canvas: Canvas, view: View) -> None:
    canvas.fill_screen(COLOR_BG)
    canvas.set_text_size(2)
    canvas.set_text_color(COLOR_TEXT, COLOR_BG)
    canvas.draw_string("PRODLEVY LED", 6, 2)
    draw_battery(canvas, view)

    track_x = 44
    track_w = 104
    first_y = 30
    max_offset = max(1, max_delay_ms(view.config))

    for led in range(LED_COUNT):
        y = first_y + led * 25
        line_y = y + 6
        selected = led == view.selected_delay_led
        label = f"L{led + 1}"
        led_color = ui_color_for_led(view, led)
        canvas.set_text_color(led_color, COLOR_BG)
        canvas.draw_string(label, 8, line_y - 8)
        canvas.draw_fast_hline(track_x, line_y, track_w, dim_rgb(COLOR_MUTED, 100))
        knob_x = track_x + 3 + view.config.led_delay_ms[led] * (track_w - 6) // max_offset
        canvas.fill_circle(knob_x, line_y, 5, COLOR_TEXT if selected else led_color)

        value = f"{view.config.led_delay_ms[led]}ms"
        text_color = COLOR_TEXT if selected else COLOR_MUTED
        canvas.draw_right_string(value, SCREEN_W - 8, line_y - 8, text_color, COLOR_BG)


def render(view: View, page: str = "main", hires: bool = False) -> Image.Image:
    # hires=True returns the full supersampled buffer (SCREEN*S) instead of the
    # device-native 240x135 downscale -- crisp max-resolution export for review.
    canvas = Canvas(COLOR_BG)
    canvas.fill_screen(COLOR_BG)
    if page == "delays":
        draw_delay_timeline(canvas, view)
        return canvas.img if hires else canvas.raw()

    draw_status_bar(canvas, view)
    draw_plot(canvas, view)
    # Subtle frame around the EFEKT block (plot + palette) so it reads as one cohesive
    # "effect" panel instead of floating lines. Drawn AFTER the plot (which fills its
    # own COLOR_BG background) so the outline survives.
    canvas.draw_rect(6, EFEKT_TOP, SCREEN_W - 12, EFEKT_BOT - EFEKT_TOP, dim_rgb(COLOR_MUTED, 70))
    if view.rows_visible:
        draw_main_rows(canvas, view)
    else:
        draw_main_info_area(canvas, view)
    # Frame the whole screen in the alarm colour for the dangerous live states, so they
    # are screen-dominant while the effect plot/config stays visible (no full takeover).
    if view.mode == "fire":
        canvas.draw_rect(0, 0, SCREEN_W, SCREEN_H, COLOR_BAD, width=6)
    elif view.armed:
        canvas.draw_rect(0, 0, SCREEN_W, SCREEN_H, COLOR_WARN, width=4)
    # 4px state-colour SPINE down the left edge -- a calm peripheral / at-an-angle state
    # cue that persists even when the status bar is a quiet chip (KLID). Drawn LAST so
    # nothing (status fill, plot fill, alarm border) paints over it.
    canvas.fill_rect(0, 0, SPINE_W, SCREEN_H, state_spine_color(view))
    return canvas.img if hires else canvas.raw()


# ----------------------------------------------------------------------------
# Scenes + contact sheet.
# ----------------------------------------------------------------------------


def scenes() -> dict[str, tuple[View, str]]:
    default_config = EffectConfig()
    representative = replace(
        default_config,
        pre_trigger=True,
        shape=EFFECT_SHAPE_SQUARE,
        shape_param=55,
        repeat=2,
        intensity=80,
    )
    long_repeat = replace(representative, repeat=5)

    return {
        "main_idle": (
            View(status="KLID", mode="idle", config=default_config, battery_percent=76, rows_visible=False),
            "main",
        ),
        "main_armed": (
            View(
                status="NABITO",
                mode="idle",
                armed=True,
                config=representative,
                battery_percent=64,
                rows_visible=True,
                row_scroll=0,
                selected_row=1,
            ),
            "main",
        ),
        "main_firing": (
            View(
                status="PALI",
                mode="fire",
                config=representative,
                battery_percent=58,
                elapsed_ms=plot_duration_ms(representative) // 2,
                rows_visible=False,
            ),
            "main",
        ),
        "main_stop": (
            View(
                status="STOP",
                mode="idle",
                armed=False,
                config=long_repeat,
                battery_percent=18,
                rows_visible=True,
                row_scroll=3,
                selected_row=-1,      # latched: read-only readout, no selection / no editing
                editing=False,
            ),
            "main",
        ),
        "main_editing": (
            View(
                status="NABITO",
                mode="idle",
                armed=True,
                config=representative,
                battery_percent=60,
                rows_visible=True,
                row_scroll=0,
                selected_row=1,       # DOBA being edited -> amber box + carets demonstrate edit mode
                editing=True,
            ),
            "main",
        ),
        "shape_sine": (
            View(status="KLID", mode="idle", config=replace(representative, shape=EFFECT_SHAPE_SINE2),
                 battery_percent=70, rows_visible=False),
            "main",
        ),
        "shape_saw": (
            View(status="KLID", mode="idle",
                 config=replace(representative, shape=EFFECT_SHAPE_SAWTOOTH, shape_param=80),
                 battery_percent=70, rows_visible=False),
            "main",
        ),
        "shape_tri": (
            View(status="KLID", mode="idle", config=replace(representative, shape=EFFECT_SHAPE_TRIANGLE),
                 battery_percent=70, rows_visible=False),
            "main",
        ),
        "shape_exp": (
            View(status="KLID", mode="idle",
                 config=replace(representative, shape=EFFECT_SHAPE_EXP, shape_param=60),
                 battery_percent=70, rows_visible=False),
            "main",
        ),
        "main_preview": (
            View(status="NABITO", mode="preview", armed=True, config=representative,
                 battery_percent=66, rows_visible=False, elapsed_ms=plot_duration_ms(representative) // 3),
            "main",
        ),
        "edge_inf": (   # repeat=0 -> xINF multiplier path
            View(status="KLID", mode="idle", config=replace(representative, repeat=0),
                 battery_percent=70, rows_visible=False),
            "main",
        ),
        "edge_pal1": (  # single-cell palette (no fade between cells)
            View(status="KLID", mode="idle", config=representative, battery_percent=70,
                 rows_visible=False, palette=((255, 40, 35),)),
            "main",
        ),
        "led_delays": (
            View(
                status="KLID",
                mode="idle",
                config=replace(representative, led_delay_ms=(0, 80, 160, 360)),
                battery_percent=52,
                selected_delay_led=2,
            ),
            "delays",
        ),
    }


def contact_sheet(imgs: list[tuple[str, Image.Image]]) -> Image.Image:
    cols = 2
    rows = (len(imgs) + cols - 1) // cols
    pad = 10
    label_h = 14
    cell_w = SCREEN_W
    cell_h = SCREEN_H + label_h
    sheet = Image.new(
        "RGB",
        (cols * cell_w + (cols + 1) * pad, rows * cell_h + (rows + 1) * pad),
        (20, 22, 26),
    )
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype(str(FONT_REGULAR), 11)
    except OSError:
        font = ImageFont.load_default()
    for idx, (name, im) in enumerate(imgs):
        row, col = divmod(idx, cols)
        x = pad + col * (cell_w + pad)
        y = pad + row * (cell_h + pad)
        sheet.paste(im, (x, y))
        draw.text((x, y + SCREEN_H + 2), name, font=font, fill=rgb(COLOR_MUTED))
    return sheet


def main() -> None:
    out = ROOT / "build" / "preview_dinrx"
    os.makedirs(out, exist_ok=True)

    imgs: list[tuple[str, Image.Image]] = []
    written: list[Path] = []
    for name, (view, page) in scenes().items():
        im = render(view, page)
        path = out / f"{name}.png"
        im.save(path)
        imgs.append((name, im))
        written.append(path)

    sheet = contact_sheet(imgs)
    contact_path = out / "contact.png"
    sheet.save(contact_path)
    written.append(contact_path)

    print("PNG files written:")
    for path in written:
        print(path)


if __name__ == "__main__":
    main()
