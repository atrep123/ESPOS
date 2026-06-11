"""Desktop preview for the M5Dial prop_tx GUI.

This is a design harness, NOT the firmware. It mirrors the LovyanGFX drawing
primitives used by gui_prop_tx.cpp closely enough to iterate on the round-display
layout on a PC, then port the final look back to C++.

LovyanGFX angle convention (matches PIL): 0 deg = East (3 o'clock), angles grow
clockwise (y points down), so 90 = bottom, 180 = left, 270 = top.

Run:  python tools/preview_prop_tx.py
Out:  build/preview/*.png  and  build/preview/contact.png
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ----------------------------------------------------------------------------
# Canvas: supersampled wrapper exposing LovyanGFX-like primitives.
# ----------------------------------------------------------------------------

S = 4  # supersample factor for antialiasing
SIZE = 240
ROOT = Path(__file__).resolve().parents[1]
FONT_REGULAR = ROOT / "firmware/dial-tx/components/lvgl/scripts/built_in_font/DejaVuSans.ttf"
FONT_BOLD = ROOT / "firmware/dial-tx/components/lvgl/scripts/built_in_font/Montserrat-Medium.ttf"


def rgb(c: int):
    return ((c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF)


@dataclass(frozen=True)
class DrawOp:
    kind: str
    role: str
    color: int | None = None
    bbox: tuple[float, float, float, float] | None = None
    center: tuple[float, float] | None = None
    outer_radius: float | None = None
    inner_radius: float | None = None
    width: float | None = None
    angles: tuple[float, float] | None = None
    text: str | None = None
    points: tuple[tuple[float, float], tuple[float, float]] | None = None
    index: int | None = None


def _font(size: int, bold: bool = True):
    candidates = [
        str(FONT_BOLD if bold else FONT_REGULAR),
        str(FONT_REGULAR),
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size * S)
        except OSError:
            continue
    return ImageFont.load_default()


class Canvas:
    def __init__(self, bg: int):
        self.img = Image.new("RGB", (SIZE * S, SIZE * S), rgb(bg))
        self.d = ImageDraw.Draw(self.img)
        self.ops: list[DrawOp] = []

    def _record(self, op: DrawOp):
        self.ops.append(op)

    @staticmethod
    def _bbox_from_circle(cx, cy, r):
        return (cx - r, cy - r, cx + r, cy + r)

    @staticmethod
    def _scaled_bbox(bbox):
        return tuple(v / S for v in bbox)

    def fill_screen(self, color: int, role="screen"):
        self.d.rectangle([0, 0, SIZE * S, SIZE * S], fill=rgb(color))
        self._record(DrawOp("rect", role, color=color, bbox=(0.0, 0.0, float(SIZE), float(SIZE))))

    def fill_circle(self, cx, cy, r, color: int, role="circle", index=None):
        bbox = self._bbox_from_circle(cx, cy, r)
        sx, sy, sr = cx * S, cy * S, r * S
        self.d.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=rgb(color))
        self._record(
            DrawOp(
                "circle",
                role,
                color=color,
                bbox=bbox,
                center=(float(cx), float(cy)),
                outer_radius=float(r),
                index=index,
            )
        )

    def draw_circle(self, cx, cy, r, color: int, width=1, role="circle", index=None):
        bbox = self._bbox_from_circle(cx, cy, r + width / 2)
        sx, sy, sr = cx * S, cy * S, r * S
        self.d.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], outline=rgb(color), width=width * S)
        self._record(
            DrawOp(
                "ring",
                role,
                color=color,
                bbox=bbox,
                center=(float(cx), float(cy)),
                outer_radius=float(r + width / 2),
                inner_radius=float(max(0, r - width / 2)),
                width=float(width),
                angles=(0.0, 360.0),
                index=index,
            )
        )

    def fill_round_rect(self, x, y, w, h, r, color: int, role="round_rect"):
        sx, sy, sw, sh, sr = x * S, y * S, w * S, h * S, r * S
        self.d.rounded_rectangle([sx, sy, sx + sw, sy + sh], radius=sr, fill=rgb(color))
        self._record(DrawOp("rect", role, color=color, bbox=(x, y, x + w, y + h)))

    def polygon(self, points, fill: int, outline: int | None = None, width=1, role="polygon", index=None):
        scaled = [(x * S, y * S) for x, y in points]
        self.d.polygon(scaled, fill=rgb(fill))
        if outline is not None and width > 0:
            closed = scaled + [scaled[0]]
            self.d.line(closed, fill=rgb(outline), width=max(1, int(width * S)), joint="curve")
        xs = [float(x) for x, _ in points]
        ys = [float(y) for _, y in points]
        self._record(
            DrawOp(
                "polygon",
                role,
                color=fill,
                bbox=(min(xs), min(ys), max(xs), max(ys)),
                index=index,
            )
        )

    def ring_band(self, cx, cy, r_out, r_in, a0, a1, color: int, role="ring", index=None):
        r = (r_out + r_in) / 2.0
        width = r_out - r_in
        sx, sy = cx * S, cy * S
        sr, sw = r * S, width * S
        bbox = [sx - sr, sy - sr, sx + sr, sy + sr]
        self.d.arc(bbox, a0, a1, fill=rgb(color), width=max(1, int(sw)))
        self._record(
            DrawOp(
                "ring",
                role,
                color=color,
                bbox=self._bbox_from_circle(cx, cy, r_out),
                center=(float(cx), float(cy)),
                outer_radius=float(r_out),
                inner_radius=float(r_in),
                width=float(width),
                angles=(float(a0), float(a1)),
                index=index,
            )
        )

    def ring(self, cx, cy, r, width, a0, a1, color: int, rounded=True, role="ring", index=None):
        """Annular arc from a0 to a1 (degrees, clockwise) at radius r."""
        self.ring_band(cx, cy, r + width / 2.0, r - width / 2.0, a0, a1, color, role=role, index=index)
        cx, cy = cx * S, cy * S
        rr, w = r * S, width * S
        if rounded:
            cap = w / 2.0
            for a in (a0, a1):
                px = cx + rr * math.cos(math.radians(a))
                py = cy + rr * math.sin(math.radians(a))
                self.d.ellipse([px - cap, py - cap, px + cap, py + cap], fill=rgb(color))

    def line(self, x0, y0, x1, y1, color: int, width=1, role="line", index=None):
        self.d.line([x0 * S, y0 * S, x1 * S, y1 * S], fill=rgb(color), width=width * S)
        pad = width / 2.0
        self._record(
            DrawOp(
                "line",
                role,
                color=color,
                bbox=(min(x0, x1) - pad, min(y0, y1) - pad, max(x0, x1) + pad, max(y0, y1) + pad),
                width=float(width),
                points=((float(x0), float(y0)), (float(x1), float(y1))),
                index=index,
            )
        )

    def text_center(self, text, x, y_top, size, color: int, bold=True, tracking=0.0, role="text", index=None):
        f = _font(size, bold)
        bboxes = []
        if tracking:
            # manual letter spacing
            widths = [self.d.textlength(ch, font=f) for ch in text]
            total = sum(widths) + tracking * S * (len(text) - 1)
            cursor = x * S - total / 2
            for ch, wch in zip(text, widths):
                xy = (cursor, y_top * S)
                self.d.text(xy, ch, font=f, fill=rgb(color))
                bboxes.append(self.d.textbbox(xy, ch, font=f))
                cursor += wch + tracking * S
        else:
            bbox = self.d.textbbox((0, 0), text, font=f)
            tw = bbox[2] - bbox[0]
            xy = (x * S - tw / 2 - bbox[0], y_top * S)
            self.d.text(xy, text, font=f, fill=rgb(color))
            bboxes.append(self.d.textbbox(xy, text, font=f))
        if bboxes:
            bbox = (
                min(b[0] for b in bboxes),
                min(b[1] for b in bboxes),
                max(b[2] for b in bboxes),
                max(b[3] for b in bboxes),
            )
            self._record(DrawOp("text", role, color=color, bbox=self._scaled_bbox(bbox), text=str(text), index=index))

    def text_width(self, text, size, bold=True):
        f = _font(size, bold)
        bbox = self.d.textbbox((0, 0), text, font=f)
        return (bbox[2] - bbox[0]) / S

    def raw(self):
        small = self.img.resize((SIZE, SIZE), Image.LANCZOS)
        return small

    def finish(self):
        small = self.raw()
        # round-display mask on a neutral page so the circle edge is visible
        page = Image.new("RGB", (SIZE + 32, SIZE + 32), (38, 40, 44))
        mask = Image.new("L", (SIZE, SIZE), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, SIZE - 1, SIZE - 1], fill=255)
        page.paste(small, (16, 16), mask)
        ImageDraw.Draw(page).ellipse(
            [16, 16, 16 + SIZE - 1, 16 + SIZE - 1], outline=(70, 74, 80), width=2
        )
        return page


# ----------------------------------------------------------------------------
# View model (mirrors PROP_TX::View_t).
# ----------------------------------------------------------------------------


@dataclass
class View:
    action_label: str = "PREVIEW"
    field_label: str = "akce"          # akce / jas / LED / HUE
    status: str = "ready"
    field_value: str = "PREVIEW"
    armed: bool = False
    awaiting_ack: bool = False
    brightness_percent: int = 59
    selected_led: int = 0
    palette_count: int = 4   # B4b: active palette length 1..8 (mirrors firmware)
    selected_hue_degrees: int = 0
    shot_count: int = 0
    colors: list = field(default_factory=lambda: [
        (255, 0, 0), (0, 255, 0), (0, 0, 255), (0, 128, 255), (255, 255, 0)])
    # 5 LED dots, mirroring firmware gui_prop_tx.h View::colors = DEFAULT_COLORS[0..4]
    # (4->5 LEDs this session). The lower-ring renderer is count-driven off len(colors).


@dataclass(frozen=True)
class RenderedFrame:
    image: Image.Image
    ops: list[DrawOp]


# ----------------------------------------------------------------------------
# Theme
# ----------------------------------------------------------------------------

# dark premium palette -- single source tools/m5_theme.json ("dial" section);
# generated into firmware ui_theme_dial_generated.h. Pixels/colours only (no logic).
_DIAL_THEME = json.loads(
    (Path(__file__).resolve().parent / "m5_theme.json").read_text(encoding="utf-8")
)["dial"]
_D = {k: int(v, 16) for k, v in _DIAL_THEME.items()}
P_GREEN = _D["P_GREEN"]        # ready / ok
P_AMBER = _D["P_AMBER"]        # waiting / no-ack, intentionally not red
P_RED = _D["P_RED"]            # armed / error
WHITE = _D["WHITE"]
BG_BASE = _D["BG_BASE"]        # deep anthracite
RING_TRK = _D["RING_TRK"]      # ring track (reads as a gauge)
SOCKET = _D["SOCKET"]          # recessed indicator socket
TEXT_HI = _D["TEXT_HI"]
TEXT_DIM = _D["TEXT_DIM"]
ACCENT = _D["ACCENT"]          # near-white selection accent (never reads as red)
MODE_SETUP = _D["MODE_SETUP"]  # cool cyan: SETUP (tuning) mode accent
TOP = 270.0  # top of the dial


def apply_theme(colors: dict) -> None:
    """Runtime override of the Dial theme colours for the live Studio preview.

    `colors` = {NAME: "0xRRGGBB"|int}; only known theme colours are applied and
    missing/unknown keys keep their current value. No-op (pixel-identical) when
    given the values already in m5_theme.json's "dial" section.
    """
    g = globals()
    for name, value in (colors or {}).items():
        if name in _DIAL_THEME and name in g:
            g[name] = int(value, 16) if isinstance(value, str) else int(value)


def mix(a: int, b: int, t: float) -> int:
    ar, ag, ab = rgb(a)
    br, bg, bb = rgb(b)
    return (
        (int(ar + (br - ar) * t) << 16)
        | (int(ag + (bg - ag) * t) << 8)
        | int(ab + (bb - ab) * t)
    )


def state_color(v: View) -> int:
    s = v.status or ""
    if v.armed:
        return P_RED
    if v.awaiting_ack or s.startswith("sent "):
        return P_AMBER
    if s in ("no ack", "timeout"):
        return P_AMBER
    if s.startswith("ERR "):
        return P_RED
    return P_GREEN


def status_word(v: View) -> str:
    s = v.status or ""
    if v.armed:
        return "ARMED"
    if v.awaiting_ack or s.startswith("sent "):
        return "WAIT"
    if s == "ready":
        return "READY"
    if s in ("no ack", "timeout"):
        return "NO ACK"
    if s.startswith("ACK "):
        return "ACK"
    if s.startswith("ERR "):
        return "ERROR"
    if s == "RX ignored":
        return "RX"
    if s.startswith("ARM "):
        return "ARM"
    if s.startswith("LED "):
        return "READY"
    return s.upper()[:8]


def is_editing(v: View, key: str) -> bool:
    lbl = v.field_label or ""
    if key in ("a", "akce"):
        return lbl.startswith("a")
    if key in ("j", "jas"):
        return lbl.startswith("j")
    if key in ("L", "LED"):
        return lbl == "LED"
    if key in ("H", "HUE"):
        return lbl == "HUE"
    return False


def field_caption(v: View) -> str:
    lbl = v.field_label or ""
    if lbl.startswith("a"):
        return "AKCE"
    if lbl.startswith("j"):
        return "JAS"
    if lbl == "LED":
        return "LED"
    if lbl == "HUE":
        return "ODSTIN"
    return lbl.upper()


def is_command_mode(v: View) -> bool:
    return is_editing(v, "akce") or v.awaiting_ack


def led_rgb(v: View, i: int) -> int:
    return (v.colors[i][0] << 16) | (v.colors[i][1] << 8) | v.colors[i][2]


def luminance(col: int) -> float:
    r, g, b = rgb(col)
    return 0.299 * r + 0.587 * g + 0.114 * b


def on_color(col: int) -> int:
    return 0x0E1116 if luminance(col) > 150 else WHITE


# ----------------------------------------------------------------------------
# Render
# ----------------------------------------------------------------------------

RING_OUT = 116
RING_IN = 110
RING_CAP = 113
RING_R = RING_CAP
ORB_CX, ORB_CY, ORB_R = 120, 120, 43        # setup orb diameter stays in the 80-90px range
COMMAND_RING_R = 54                         # hollow command target (~108px); small enough that the dot band clears it
COMMAND_RING_W = 10
LED_R = 80                                  # dots centred in their band: orb edge (r~51) .. brightness ring (inner r110) -> mid ~80
LED_ANGLES = [126.0, 102.0, 78.0, 54.0]     # legacy 4-slot angles (kept for reference)


def led_angle(i: int, count: int) -> float:
    """B4b: evenly distribute `count` palette dots on the lower ring arc. count=4
    reproduces LED_ANGLES (72deg span, 24deg apart); the span widens (cap 144deg) for
    more slots; a single slot sits dead-centre at 90deg. Mirrors gui_prop_tx.cpp."""
    if count <= 1:
        return 90.0
    span = min((count - 1) * 24.0, 144.0)
    spacing = span / (count - 1)
    return 90.0 + span / 2.0 - i * spacing


def draw_setup_grid(c: Canvas, color: int):
    for x in range(24, SIZE, 24):
        c.line(x, 14, x, SIZE - 14, color, 1, role="setup_grid")
    for y in range(24, SIZE, 24):
        c.line(14, y, SIZE - 14, y, color, 1, role="setup_grid")


def draw_orb(c: Canvas, cx, cy, r, color, accent, label):
    # flat, emissive lens (no glossy highlight)
    c.fill_circle(cx, cy, r + 10, mix(BG_BASE, color, 0.18), role="orb_outer_glow")
    c.fill_circle(cx, cy, r + 5, mix(BG_BASE, color, 0.34), role="orb_inner_glow")
    c.fill_circle(cx, cy, r, color, role="orb_lens")
    # subtle emissive core — a faint brighter centre gives premium depth (a lit
    # lens) without a glossy highlight; text is drawn on top afterwards
    c.fill_circle(cx, cy, int(r * 0.62), mix(color, WHITE, 0.09), role="orb_core")
    c.fill_circle(cx, cy, int(r * 0.30), mix(color, WHITE, 0.16), role="orb_core")
    c.ring_band(cx, cy, r + 1, r - 1, 0, 360, mix(color, WHITE, 0.22), role="orb_rim")
    c.ring_band(cx, cy, r + 8, r + 5, 0, 360, accent, role="orb_selection")
    if label:
        n = len(label)
        size = 42 if n <= 1 else (34 if n <= 3 else 28)       # edited value lives in the orb
        c.text_center(label, cx, cy - size * 0.46, size, on_color(color), role="orb_text")


def command_label_size(label: str) -> int:
    n = len(label)
    # sized to sit cleanly INSIDE the target ring (no crossing the side segments)
    return 26 if n <= 4 else (22 if n == 5 else (19 if n == 6 else 17))


def draw_segmented_target(c: Canvas, cx, cy, r, width, color):
    for start in (285, 15, 105, 195):
        c.ring_band(cx, cy, r + width / 2, r - width / 2, start, start + 58, color, role="command_ring")


def draw_polyline_round(c: Canvas, pts, width, color, role="line"):
    # Connected polyline with rounded joints AND rounded ends, so the outer
    # contour stays continuous (no butt-cap notch at the vertex, no vanishing
    # edge at the tips).
    spts = [(px * S, py * S) for px, py in pts]
    c.d.line(spts, fill=rgb(color), width=int(width * S), joint="curve")
    r = width / 2.0
    for px, py in (pts[0], pts[-1]):
        c.fill_circle(px, py, r, color)


def draw_x_glyph(c: Canvas, cx, cy, color):
    draw_polyline_round(c, ((cx - 17, cy - 17), (cx + 17, cy + 17)), 8, color, role="no_ack_x")
    draw_polyline_round(c, ((cx + 17, cy - 17), (cx - 17, cy + 17)), 8, color, role="no_ack_x")


def draw_check_glyph(c: Canvas, cx, cy, color):
    pts = ((cx - 22, cy + 2), (cx - 7, cy + 17), (cx + 26, cy - 18))
    draw_polyline_round(c, pts, 9, color, role="ack_check")            # solid, continuous body
    draw_polyline_round(c, pts, 3, WHITE, role="ack_check_highlight")  # bright core stripe


def draw_chevron(c: Canvas, tip_x, tip_y, arm_dx, half_h, color, w=5):
    # One connected polyline with a rounded joint -> the tip is a clean point,
    # not the bitten-off notch you get from two separate butt-capped segments.
    pts = [(tip_x + arm_dx, tip_y - half_h), (tip_x, tip_y), (tip_x + arm_dx, tip_y + half_h)]
    c.d.line([(px * S, py * S) for px, py in pts], fill=rgb(color), width=int(w * S), joint="curve")


def draw_wait_sweep(c: Canvas, cx, cy, color):
    c.ring_band(cx, cy, 38, 30, 0, 360, mix(BG_BASE, color, 0.35), role="wait_track")
    c.ring_band(cx, cy, 42, 30, 294, 36 + 360, color, role="wait_sweep")
    c.fill_circle(cx, cy, 4, color, role="wait_pivot")


def draw_command_token(c: Canvas, cx, cy, sc, label, variant="normal"):
    # Hollow segmented target: command mode reads structurally different from setup.
    draw_segmented_target(c, cx, cy, COMMAND_RING_R, COMMAND_RING_W, sc)

    if variant == "wait":
        draw_wait_sweep(c, cx, cy, sc)
        return
    if variant == "ack":
        draw_check_glyph(c, cx, cy, sc)
        return
    if variant == "no_ack":
        draw_x_glyph(c, cx, cy, sc)
        return

    ls = command_label_size(label)
    # Action word in clean high-contrast white. The fire caution is carried by the
    # dedicated red ARMED screen, not by tinting this word red on a green ring
    # (that read as half-armed and looked off).
    c.text_center(label, cx, cy - ls * 0.42, ls, TEXT_HI, role="command_text")


def draw_warning_glyph(c: Canvas, cx, cy, size, color):
    h = size * 1.72
    pts = ((cx, cy - h / 2), (cx - size, cy + h / 2), (cx + size, cy + h / 2))
    c.polygon(pts, color, role="armed_hazard_triangle")
    c.text_center("!", cx, cy - size * 0.74, int(size * 1.45), P_RED, role="armed_hazard_bang")


def render_armed_frame(v: View) -> RenderedFrame:
    c = Canvas(P_RED)
    c.fill_screen(P_RED, role="screen")
    c.ring_band(120, 120, 119, 111, 0, 360, WHITE, role="armed_outer_ring")
    c.ring_band(120, 120, 109, 106, 0, 360, mix(P_RED, WHITE, 0.42), role="armed_pulse_ring")
    # minimal hazard cue at the top (not a big generic centre triangle + bangs)
    draw_warning_glyph(c, 120, 48, 14, WHITE)
    # hero action word
    c.text_center("ODPAL", 120, 84, 44, WHITE, role="armed_fire_text")
    # ARMED as a clean tracked label (no flanking rules -- they read as a broken
    # line across the screen)
    c.text_center("ARMED", 120, 142, 24, mix(P_RED, WHITE, 0.92), tracking=5.0, role="armed_state_text")
    # loaded channel colours -> shows WHAT will fire (specific to this prop, not generic)
    for i in range(4):
        chx = 96 + i * 16
        col = led_rgb(v, i)
        c.fill_circle(chx, 188, 7, mix(P_RED, WHITE, 0.85), role="armed_chip_rim")
        c.fill_circle(chx, 188, 5, col, role="armed_chip")
    return RenderedFrame(image=c.raw(), ops=c.ops)


def draw_leader(c: Canvas, angle_deg: float, color: int):
    # Tapered pointer from the selected channel dot inward to the centre orb, so
    # SETUP mode shows at a glance which channel the orb is currently editing.
    a = math.radians(angle_deg)
    px, py = math.cos(a), math.sin(a)
    qx, qy = -py, px
    bx, by = 120 + px * (LED_R - 12), 120 + py * (LED_R - 12)   # base: tucked under the dot
    ax, ay = 120 + px * (ORB_R + 9), 120 + py * (ORB_R + 9)     # apex: touches the orb edge
    c.polygon(((bx + qx * 7.5, by + qy * 7.5), (bx - qx * 7.5, by - qy * 7.5), (ax, ay)),
              SOCKET, role="led_leader_outline")
    c.polygon(((bx + qx * 5.0, by + qy * 5.0), (bx - qx * 5.0, by - qy * 5.0), (ax, ay)),
              color, role="led_leader")


def render_frame(v: View, accent: int = ACCENT) -> RenderedFrame:
    if v.armed:
        return render_armed_frame(v)

    sc = state_color(v)
    s = v.status or ""
    command = is_command_mode(v)
    ack = s.startswith("ACK ")
    no_ack = s in ("no ack", "timeout")
    bg_tint = 0.25 if ack else (0.10 if command else 0.06)
    bg_src = sc if command else MODE_SETUP
    bg = mix(BG_BASE, bg_src, bg_tint)  # neutral base with a subtle state/mode tint
    c = Canvas(bg)
    c.fill_screen(bg, role="screen")

    if not command:
        draw_setup_grid(c, mix(BG_BASE, MODE_SETUP, 0.26))

    # --- brightness ring --------------------------------------------------
    c.ring_band(120, 120, RING_OUT, RING_IN, 0, 360, RING_TRK, role="brightness_track")
    bp = int(v.brightness_percent)
    if bp > 100:
        bp = 100
    if bp > 0:
        sweep = bp / 100.0 * 352.0
        if sweep < 8.0:
            sweep = 8.0
        a0 = TOP          # start cap sits exactly at top-centre (12 o'clock)
        a1 = a0 + sweep
        c.ring_band(120, 120, RING_OUT, RING_IN, a0, a1, sc, role="brightness_value")
        for a in (a0, a1):
            x = int(120 + RING_CAP * math.cos(math.radians(a)))
            y = int(120 + RING_CAP * math.sin(math.radians(a)))
            c.fill_circle(x, y, 3, sc, role="brightness_cap")

    # SETUP threads the cool mode accent through its selection rings so the
    # whole screen — not just the caption — reads as "tuning" mode at a glance.
    if not command:
        accent = MODE_SETUP

    # --- mode caption (top) — the single clearest mode signal -------------
    # colour-coded so SETUP vs COMMAND read at a glance even before the text:
    # cool cyan = NASTAVENI (tuning), neutral near-white = PRIKAZ (transmit).
    mode_caption = "PRIKAZ" if command else "NASTAVENI"
    mode_color = ACCENT if command else MODE_SETUP
    # padded clear of the brightness ring so the caption doesn't collide with it
    c.text_center(mode_caption, 120, 36, 14, mode_color, tracking=4.0, role="mode_caption")

    # --- status word REMOVED ---------------------------------------------
    # The big status word collided with the brightness ring and the command
    # token / orb in the crowded upper band. It was redundant: the ring colour
    # already conveys ready/wait/error, the command-token variant shows
    # WAIT/ACK/NO-ACK, and the orb shows the edited value. Dropping it clears
    # the collision and de-clutters the round face.

    # --- centrepiece ------------------------------------------------------
    if command:
        label = v.action_label
        variant = "normal"
        if v.awaiting_ack:
            variant = "wait"
        elif ack:
            variant = "ack"
        elif no_ack:
            variant = "no_ack"
        draw_command_token(c, 120, ORB_CY, sc, label, variant)
        # Safety: once ARMED the only on-screen choice is ODPAL (fire) / cancel.
        # Hide the action-scroll chevrons so a stressed user can't dial to a
        # different action while the controller is live.
        if not v.awaiting_ack and not v.armed:
            cyc = ORB_CY
            chev = COMMAND_RING_R + 14               # sit just outside the command ring
            draw_chevron(c, 120 - chev, cyc, 9, 9, sc, 5)    # left  "<"
            draw_chevron(c, 120 + chev, cyc, -9, 9, sc, 5)   # right ">"
    else:
        col = 0xDDE2E8 if is_editing(v, "jas") else led_rgb(v, v.selected_led)
        if is_editing(v, "HUE"):
            oval = f"{v.selected_hue_degrees}°"
        elif is_editing(v, "jas"):
            oval = f"{v.brightness_percent}%"
        else:
            oval = f"{v.selected_led + 1}"
        draw_orb(c, ORB_CX, ORB_CY, ORB_R, col, accent, oval)
    # setup value lives inside the orb; command state is shown by the status word

    # --- palette dots on a concentric bottom arc (echoes the round shape) --
    # the selected slot is brought forward: larger, full-bright, with a glow.
    # B4b: draws palette_count (1..8) dots; dense palettes shrink the dots.
    slot_count = max(1, min(8, v.palette_count))
    dense = slot_count > 5
    dot_r = 8 if dense else 10
    sock_r = 11 if dense else 13
    for i in range(slot_count):
        ang = led_angle(i, slot_count)
        a = math.radians(ang)
        x = 120 + LED_R * math.cos(a)
        y = 120 + LED_R * math.sin(a)
        col = led_rgb(v, i)
        sel = i == v.selected_led
        if sel:
            if not command:
                draw_leader(c, ang, col)   # pointer from selected dot -> orb (setup)
            c.fill_circle(x, y, sock_r + 3, mix(BG_BASE, col, 0.30), role="led_glow", index=i)
            c.fill_circle(x, y, sock_r, SOCKET, role="led_socket", index=i)
            c.fill_circle(x, y, dot_r, col, role="led_lens", index=i)
            c.ring_band(x, y, sock_r + 2, sock_r, 0, 360, WHITE, role="led_selection", index=i)
        else:
            c.fill_circle(x, y, sock_r, SOCKET, role="led_socket", index=i)
            c.ring_band(x, y, sock_r, sock_r - 1, 0, 360, mix(BG_BASE, WHITE, 0.12), role="led_outer_rim", index=i)
            tint = mix(col, BG_BASE, 0.30) if command else mix(col, BG_BASE, 0.62)
            c.fill_circle(x, y, dot_r, tint, role="led_lens", index=i)
    # (bottom chevron removed — the system already draws a back/down arrow)

    return RenderedFrame(image=c.raw(), ops=c.ops)


def render(v: View, accent: int = ACCENT) -> Image.Image:
    frame = render_frame(v, accent=accent)
    page = Image.new("RGB", (SIZE + 32, SIZE + 32), (38, 40, 44))
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, SIZE - 1, SIZE - 1], fill=255)
    page.paste(frame.image, (16, 16), mask)
    ImageDraw.Draw(page).ellipse(
        [16, 16, 16 + SIZE - 1, 16 + SIZE - 1], outline=(70, 74, 80), width=2
    )
    return page


# ----------------------------------------------------------------------------
# Scenes + contact sheet
# ----------------------------------------------------------------------------


def scenes():
    cols = [(255, 30, 30), (30, 220, 90), (40, 120, 255), (255, 180, 0)]
    cols8 = [(255, 30, 30), (30, 220, 90), (40, 120, 255), (255, 180, 0),
             (200, 40, 255), (0, 220, 220), (255, 80, 160), (150, 255, 40)]
    return {
        "01_ready_action": View(action_label="PREVIEW", field_label="akce", status="ready",
                                 field_value="PREVIEW", colors=cols),
        "02_action_fire": View(action_label="ODPAL", field_label="akce", status="ready",
                               field_value="ODPAL", colors=cols),
        "03_armed": View(action_label="ODPAL", field_label="akce", status="ARM ready",
                         field_value="ODPAL", armed=True, colors=cols),
        "04_wait_ack": View(action_label="ODPAL", field_label="akce", status="sent FIRE wait",
                            field_value="ODPAL", awaiting_ack=True, colors=cols),
        "05_ack": View(action_label="PREVIEW", field_label="akce", status="ACK 42",
                       field_value="PREVIEW", colors=cols),
        "06_no_ack": View(action_label="PING", field_label="akce", status="no ack",
                          field_value="PING", colors=cols),
        "07_edit_jas": View(field_label="jas", status="ready", field_value="59%",
                            brightness_percent=59, colors=cols),
        "08_edit_led": View(field_label="LED", status="LED 3 BARVA", field_value="3",
                            selected_led=2, selected_hue_degrees=240, colors=cols),
        "09_edit_hue": View(field_label="HUE", status="ready", field_value="120°",
                            selected_led=1, selected_hue_degrees=120, brightness_percent=80, colors=cols),
        # B4b: variable palette length (1..8) on the dot ring.
        "10_palette1": View(field_label="BARVY", status="1 barva", field_value="1",
                            palette_count=1, selected_led=0, colors=cols8),
        "11_palette6": View(field_label="BARVY", status="6 barev", field_value="6",
                            palette_count=6, selected_led=4, colors=cols8),
        "12_palette8": View(field_label="BARVY", status="8 barev", field_value="8",
                            palette_count=8, selected_led=6, colors=cols8),
    }


def main():
    out = os.path.join(os.path.dirname(__file__), "..", "build", "preview")
    out = os.path.abspath(out)
    os.makedirs(out, exist_ok=True)

    imgs = []
    for name, v in scenes().items():
        im = render(v)
        im.save(os.path.join(out, f"{name}.png"))
        imgs.append((name, im))

    # contact sheet
    cols = 3
    rows = (len(imgs) + cols - 1) // cols
    w, h = imgs[0][1].size
    pad = 10
    sheet = Image.new("RGB", (cols * w + (cols + 1) * pad, rows * h + (rows + 1) * pad), (20, 22, 26))
    for idx, (_, im) in enumerate(imgs):
        r, cidx = divmod(idx, cols)
        sheet.paste(im, (pad + cidx * (w + pad), pad + r * (h + pad)))
    sheet.save(os.path.join(out, "contact.png"))
    print("wrote", len(imgs), "frames +", os.path.join(out, "contact.png"))


if __name__ == "__main__":
    main()
