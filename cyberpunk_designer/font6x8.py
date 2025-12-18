from __future__ import annotations

from typing import Dict, Optional, Tuple

import pygame

# Keep in sync with firmware font cell (src/ui_render.h)
CHAR_W = 6
CHAR_H = 8


def _row5(bits5: int) -> int:
    return (int(bits5) & 0x1F) << 1


_GLYPH_SPACE = (0, 0, 0, 0, 0, 0, 0, 0)

_GLYPH_DOT = (0x00, 0x00, 0x00, 0x00, 0x00, _row5(0x04), _row5(0x04), 0x00)
_GLYPH_COLON = (0x00, _row5(0x04), _row5(0x04), 0x00, _row5(0x04), _row5(0x04), 0x00, 0x00)
_GLYPH_MINUS = (0x00, 0x00, 0x00, _row5(0x1F), 0x00, 0x00, 0x00, 0x00)
_GLYPH_UNDERSCORE = (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, _row5(0x1F), 0x00)
_GLYPH_SLASH = (_row5(0x01), _row5(0x02), _row5(0x04), _row5(0x08), _row5(0x10), 0x00, 0x00, 0x00)
_GLYPH_QMARK = (_row5(0x0E), _row5(0x11), _row5(0x01), _row5(0x02), _row5(0x04), 0x00, _row5(0x04), 0x00)
_GLYPH_PERCENT = (_row5(0x19), _row5(0x1A), _row5(0x04), _row5(0x08), _row5(0x16), _row5(0x06), 0x00, 0x00)

_GLYPH_0 = (_row5(0x0E), _row5(0x11), _row5(0x11), _row5(0x11), _row5(0x11), _row5(0x11), _row5(0x0E), 0x00)
_GLYPH_1 = (_row5(0x04), _row5(0x0C), _row5(0x04), _row5(0x04), _row5(0x04), _row5(0x04), _row5(0x0E), 0x00)
_GLYPH_2 = (_row5(0x0E), _row5(0x11), _row5(0x01), _row5(0x02), _row5(0x04), _row5(0x08), _row5(0x1F), 0x00)
_GLYPH_3 = (_row5(0x0E), _row5(0x11), _row5(0x01), _row5(0x06), _row5(0x01), _row5(0x11), _row5(0x0E), 0x00)
_GLYPH_4 = (_row5(0x02), _row5(0x06), _row5(0x0A), _row5(0x12), _row5(0x1F), _row5(0x02), _row5(0x02), 0x00)
_GLYPH_5 = (_row5(0x1F), _row5(0x10), _row5(0x1E), _row5(0x01), _row5(0x01), _row5(0x11), _row5(0x0E), 0x00)
_GLYPH_6 = (_row5(0x06), _row5(0x08), _row5(0x10), _row5(0x1E), _row5(0x11), _row5(0x11), _row5(0x0E), 0x00)
_GLYPH_7 = (_row5(0x1F), _row5(0x01), _row5(0x02), _row5(0x04), _row5(0x08), _row5(0x08), _row5(0x08), 0x00)
_GLYPH_8 = (_row5(0x0E), _row5(0x11), _row5(0x11), _row5(0x0E), _row5(0x11), _row5(0x11), _row5(0x0E), 0x00)
_GLYPH_9 = (_row5(0x0E), _row5(0x11), _row5(0x11), _row5(0x0F), _row5(0x01), _row5(0x02), _row5(0x0C), 0x00)

_GLYPH_A = (_row5(0x0E), _row5(0x11), _row5(0x11), _row5(0x1F), _row5(0x11), _row5(0x11), _row5(0x11), 0x00)
_GLYPH_B = (_row5(0x1E), _row5(0x11), _row5(0x11), _row5(0x1E), _row5(0x11), _row5(0x11), _row5(0x1E), 0x00)
_GLYPH_C = (_row5(0x0E), _row5(0x11), _row5(0x10), _row5(0x10), _row5(0x10), _row5(0x11), _row5(0x0E), 0x00)
_GLYPH_D = (_row5(0x1E), _row5(0x11), _row5(0x11), _row5(0x11), _row5(0x11), _row5(0x11), _row5(0x1E), 0x00)
_GLYPH_E = (_row5(0x1F), _row5(0x10), _row5(0x10), _row5(0x1E), _row5(0x10), _row5(0x10), _row5(0x1F), 0x00)
_GLYPH_F = (_row5(0x1F), _row5(0x10), _row5(0x10), _row5(0x1E), _row5(0x10), _row5(0x10), _row5(0x10), 0x00)
_GLYPH_G = (_row5(0x0E), _row5(0x11), _row5(0x10), _row5(0x17), _row5(0x11), _row5(0x11), _row5(0x0E), 0x00)
_GLYPH_H = (_row5(0x11), _row5(0x11), _row5(0x11), _row5(0x1F), _row5(0x11), _row5(0x11), _row5(0x11), 0x00)
_GLYPH_I = (_row5(0x0E), _row5(0x04), _row5(0x04), _row5(0x04), _row5(0x04), _row5(0x04), _row5(0x0E), 0x00)
_GLYPH_J = (_row5(0x01), _row5(0x01), _row5(0x01), _row5(0x01), _row5(0x11), _row5(0x11), _row5(0x0E), 0x00)
_GLYPH_K = (_row5(0x11), _row5(0x12), _row5(0x14), _row5(0x18), _row5(0x14), _row5(0x12), _row5(0x11), 0x00)
_GLYPH_L = (_row5(0x10), _row5(0x10), _row5(0x10), _row5(0x10), _row5(0x10), _row5(0x10), _row5(0x1F), 0x00)
_GLYPH_M = (_row5(0x11), _row5(0x1B), _row5(0x15), _row5(0x15), _row5(0x11), _row5(0x11), _row5(0x11), 0x00)
_GLYPH_N = (_row5(0x11), _row5(0x19), _row5(0x15), _row5(0x13), _row5(0x11), _row5(0x11), _row5(0x11), 0x00)
_GLYPH_O = (_row5(0x0E), _row5(0x11), _row5(0x11), _row5(0x11), _row5(0x11), _row5(0x11), _row5(0x0E), 0x00)
_GLYPH_P = (_row5(0x1E), _row5(0x11), _row5(0x11), _row5(0x1E), _row5(0x10), _row5(0x10), _row5(0x10), 0x00)
_GLYPH_Q = (_row5(0x0E), _row5(0x11), _row5(0x11), _row5(0x11), _row5(0x15), _row5(0x12), _row5(0x0D), 0x00)
_GLYPH_R = (_row5(0x1E), _row5(0x11), _row5(0x11), _row5(0x1E), _row5(0x14), _row5(0x12), _row5(0x11), 0x00)
_GLYPH_S = (_row5(0x0F), _row5(0x10), _row5(0x10), _row5(0x0E), _row5(0x01), _row5(0x01), _row5(0x1E), 0x00)
_GLYPH_T = (_row5(0x1F), _row5(0x04), _row5(0x04), _row5(0x04), _row5(0x04), _row5(0x04), _row5(0x04), 0x00)
_GLYPH_U = (_row5(0x11), _row5(0x11), _row5(0x11), _row5(0x11), _row5(0x11), _row5(0x11), _row5(0x0E), 0x00)
_GLYPH_V = (_row5(0x11), _row5(0x11), _row5(0x11), _row5(0x11), _row5(0x0A), _row5(0x0A), _row5(0x04), 0x00)
_GLYPH_W = (_row5(0x11), _row5(0x11), _row5(0x11), _row5(0x15), _row5(0x15), _row5(0x1B), _row5(0x11), 0x00)
_GLYPH_X = (_row5(0x11), _row5(0x0A), _row5(0x0A), _row5(0x04), _row5(0x0A), _row5(0x0A), _row5(0x11), 0x00)
_GLYPH_Y = (_row5(0x11), _row5(0x0A), _row5(0x04), _row5(0x04), _row5(0x04), _row5(0x04), _row5(0x04), 0x00)
_GLYPH_Z = (_row5(0x1F), _row5(0x01), _row5(0x02), _row5(0x04), _row5(0x08), _row5(0x10), _row5(0x1F), 0x00)

_GLYPHS: Dict[str, Tuple[int, ...]] = {
    " ": _GLYPH_SPACE,
    ".": _GLYPH_DOT,
    ":": _GLYPH_COLON,
    "-": _GLYPH_MINUS,
    "_": _GLYPH_UNDERSCORE,
    "/": _GLYPH_SLASH,
    "%": _GLYPH_PERCENT,
    "?": _GLYPH_QMARK,
    "0": _GLYPH_0,
    "1": _GLYPH_1,
    "2": _GLYPH_2,
    "3": _GLYPH_3,
    "4": _GLYPH_4,
    "5": _GLYPH_5,
    "6": _GLYPH_6,
    "7": _GLYPH_7,
    "8": _GLYPH_8,
    "9": _GLYPH_9,
    "A": _GLYPH_A,
    "B": _GLYPH_B,
    "C": _GLYPH_C,
    "D": _GLYPH_D,
    "E": _GLYPH_E,
    "F": _GLYPH_F,
    "G": _GLYPH_G,
    "H": _GLYPH_H,
    "I": _GLYPH_I,
    "J": _GLYPH_J,
    "K": _GLYPH_K,
    "L": _GLYPH_L,
    "M": _GLYPH_M,
    "N": _GLYPH_N,
    "O": _GLYPH_O,
    "P": _GLYPH_P,
    "Q": _GLYPH_Q,
    "R": _GLYPH_R,
    "S": _GLYPH_S,
    "T": _GLYPH_T,
    "U": _GLYPH_U,
    "V": _GLYPH_V,
    "W": _GLYPH_W,
    "X": _GLYPH_X,
    "Y": _GLYPH_Y,
    "Z": _GLYPH_Z,
}

_CACHE: Dict[Tuple[str, Tuple[int, int, int], Optional[Tuple[int, int, int]]], pygame.Surface] = {}


def _glyph_for_char(ch: str) -> Tuple[int, ...]:
    if not ch:
        return _GLYPH_QMARK
    c = ch[0]
    if "a" <= c <= "z":
        c = chr(ord(c) - ord("a") + ord("A"))
    return _GLYPHS.get(c, _GLYPH_QMARK)


def render_text(text: str, color: Tuple[int, int, int], shadow: Optional[Tuple[int, int, int]] = None) -> pygame.Surface:
    """Render text using the firmware-like 6x8 bitmap font.

    Only a limited ASCII subset is supported (same as firmware); unsupported glyphs become '?'.
    """
    s = str(text or "")
    key = (s, tuple(color), tuple(shadow) if shadow else None)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached

    if len(_CACHE) > 512:
        _CACHE.clear()

    w = max(1, len(s)) * CHAR_W
    surf = pygame.Surface((w, CHAR_H), pygame.SRCALPHA)

    def _draw_at(dx: int, dy: int, c: Tuple[int, int, int]) -> None:
        x0 = dx
        for ch in s:
            glyph = _glyph_for_char(ch)
            for y, row in enumerate(glyph):
                mask = int(row) & 0x3F
                for x in range(CHAR_W):
                    if mask & (1 << (5 - x)):
                        surf.fill(c, pygame.Rect(x0 + x, dy + y, 1, 1))
            x0 += CHAR_W

    if shadow:
        _draw_at(1, 1, shadow)
    _draw_at(0, 0, color)

    _CACHE[key] = surf
    return surf

