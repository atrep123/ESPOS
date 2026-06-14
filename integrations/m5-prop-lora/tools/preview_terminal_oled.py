"""Render the M5StickS3 Terminal external OLED operator view.

The firmware-side contract is `terminal_external_display.h`: five framed rows
inside 128x64, no status/menu text. This preview mirrors the deterministic host
test fixture so Gemini and local visual checks can review the large display.
"""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

from PIL import Image, ImageDraw


OLED_W = 128
OLED_H = 64
SCALE = 4
ROW_START = 2
ROW_H = 12
TEXT = (235, 245, 240)
BG = (0, 0, 0)
DIM = (64, 82, 78)
FILLED = (235, 245, 240)
INVERT = (0, 0, 0)

GLYPHS_5X7 = {
    " ": (0x00, 0x00, 0x00, 0x00, 0x00),
    "-": (0x08, 0x08, 0x08, 0x08, 0x08),
    "%": (0x63, 0x13, 0x08, 0x64, 0x63),
    "0": (0x3E, 0x51, 0x49, 0x45, 0x3E),
    "1": (0x00, 0x42, 0x7F, 0x40, 0x00),
    "2": (0x42, 0x61, 0x51, 0x49, 0x46),
    "3": (0x21, 0x41, 0x45, 0x4B, 0x31),
    "4": (0x18, 0x14, 0x12, 0x7F, 0x10),
    "5": (0x27, 0x45, 0x45, 0x45, 0x39),
    "6": (0x3C, 0x4A, 0x49, 0x49, 0x30),
    "7": (0x01, 0x71, 0x09, 0x05, 0x03),
    "8": (0x36, 0x49, 0x49, 0x49, 0x36),
    "9": (0x06, 0x49, 0x49, 0x29, 0x1E),
    "A": (0x7E, 0x11, 0x11, 0x11, 0x7E),
    "B": (0x7F, 0x49, 0x49, 0x49, 0x36),
    "C": (0x3E, 0x41, 0x41, 0x41, 0x22),
    "D": (0x7F, 0x41, 0x41, 0x22, 0x1C),
    "E": (0x7F, 0x49, 0x49, 0x49, 0x41),
    "F": (0x7F, 0x09, 0x09, 0x09, 0x01),
    "G": (0x3E, 0x41, 0x49, 0x49, 0x7A),
    "H": (0x7F, 0x08, 0x08, 0x08, 0x7F),
    "I": (0x00, 0x41, 0x7F, 0x41, 0x00),
    "J": (0x20, 0x40, 0x41, 0x3F, 0x01),
    "K": (0x7F, 0x08, 0x14, 0x22, 0x41),
    "L": (0x7F, 0x40, 0x40, 0x40, 0x40),
    "M": (0x7F, 0x02, 0x0C, 0x02, 0x7F),
    "N": (0x7F, 0x04, 0x08, 0x10, 0x7F),
    "O": (0x3E, 0x41, 0x41, 0x41, 0x3E),
    "P": (0x7F, 0x09, 0x09, 0x09, 0x06),
    "R": (0x7F, 0x09, 0x19, 0x29, 0x46),
    "S": (0x46, 0x49, 0x49, 0x49, 0x31),
    "T": (0x01, 0x01, 0x7F, 0x01, 0x01),
    "U": (0x3F, 0x40, 0x40, 0x40, 0x3F),
    "V": (0x1F, 0x20, 0x40, 0x20, 0x1F),
    "Y": (0x07, 0x08, 0x70, 0x08, 0x07),
    "Z": (0x61, 0x51, 0x49, 0x45, 0x43),
}


class Row(NamedTuple):
    lane: int
    color: str
    brightness: int
    label: str
    on: bool
    effect: bool
    effect_label: str


ROWS = (
    Row(1, "CERVENA", 100, "100%", True, False, "---"),
    Row(2, "ORANZ", 80, "80%", True, True, "ODP"),
    Row(3, "TYRKYS", 45, "45%", True, False, "---"),
    Row(4, "BILA", 0, "VYP", False, True, "ODP"),
    Row(5, "MODRA", 75, "75%", True, False, "---"),
)


def _box(draw: ImageDraw.ImageDraw, rect: tuple[int, int, int, int], scale: int, fill=None) -> None:
    xy = tuple(v * scale for v in rect)
    if fill is None:
        draw.rectangle(xy, outline=DIM, width=max(1, scale))
    else:
        draw.rectangle(xy, fill=fill)


def _text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, scale: int, fill=TEXT) -> None:
    cursor_x, cursor_y = xy
    for char in text:
        glyph = GLYPHS_5X7.get(char, GLYPHS_5X7[" "])
        for glyph_x, column in enumerate(glyph):
            for glyph_y in range(7):
                if column & (1 << glyph_y):
                    x0 = (cursor_x + glyph_x) * scale
                    y0 = (cursor_y + glyph_y) * scale
                    draw.rectangle((x0, y0, x0 + scale - 1, y0 + scale - 1), fill=fill)
        cursor_x += 6


def render_terminal_oled(scale: int = SCALE) -> Image.Image:
    img = Image.new("RGB", (OLED_W * scale, OLED_H * scale), BG)
    draw = ImageDraw.Draw(img)
    _box(draw, (0, 0, OLED_W - 1, OLED_H - 1), scale)

    for index, row in enumerate(ROWS):
        y = ROW_START + index * ROW_H
        _box(draw, (3, y, 12, y + 10), scale)
        _text(draw, (5, y + 2), str(row.lane), scale)
        _text(draw, (15, y + 2), row.color[:7], scale)
        _text(draw, (60, y + 2), row.label, scale)

        bar_x, bar_y, bar_w, bar_h = 60, y + 9, 40, 3
        _box(draw, (bar_x, bar_y, bar_x + bar_w - 1, bar_y + bar_h - 1), scale)
        if row.on and row.brightness > 0:
            fill_w = round((bar_w - 2) * row.brightness / 100)
            _box(draw, (bar_x + 1, bar_y + 1, bar_x + fill_w, bar_y + bar_h - 2), scale, FILLED)

        effect_rect = (104, y + 1, 123, y + 10)
        if row.effect:
            _box(draw, effect_rect, scale, FILLED)
            _text(draw, (105, y + 2), row.effect_label, scale, BG)
        else:
            _text(draw, (105, y + 2), row.effect_label, scale, DIM)
    return img


def main() -> None:
    out = Path(__file__).resolve().parents[1] / "build" / "preview"
    out.mkdir(parents=True, exist_ok=True)
    path = out / "terminal_external_oled_128x64_x4.png"
    render_terminal_oled().save(path)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
