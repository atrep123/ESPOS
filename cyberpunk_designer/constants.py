"""Designer UI constants: palette, colors, grid, and scale settings."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

from constants import GRID_SIZE_MEDIUM

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

# Keep default aligned with the main designer entrypoint (`run_designer.py`).
DEFAULT_JSON = Path("main_scene.json")
SCALE = 2  # preferred scale; UI starts larger and stays integer-scaled
FPS = 60
GRID: int = GRID_SIZE_MEDIUM  # single source of truth: root constants.py
GUIDE_TOL = 4

# Panel dimensions (pixels)
TOOLBAR_H = 24
SCENE_TABS_H = 14
STATUS_H = 18
DEFAULT_PALETTE_W = 120
DEFAULT_INSPECTOR_W = 200

# Window margins for non-maximized startup
WIN_MARGIN_W = 24
WIN_MARGIN_H = 64

# Timing & serial
BAUD_DEFAULT = 115200
AUTOSAVE_SEC = 10.0
MAX_AUTO_SCALE_DEFAULT = 4
MIN_FPS = 30

# Double-click detection
DBLCLICK_SEC = 0.4
DBLCLICK_PX = 6

# --------------------------------------------------------------------------- #
# Shade offsets — used by drawing.py/_shade() to lighten (+) or darken (-)
# --------------------------------------------------------------------------- #
SHADE_SCANLINE = 8          # subtle scanline / bg highlight
SHADE_GRID_H = -6           # horizontal grid lines inside panels
SHADE_GRID_V = 4            # vertical grid lines inside panels
SHADE_TRACK = -18           # scrollbar track background
SHADE_THUMB = 24            # scrollbar thumb fill
SHADE_THUMB_BORDER = -28    # scrollbar thumb outline
SHADE_HOVER = 32            # pixel-frame highlight on hover
SHADE_NORMAL = 20           # pixel-frame highlight at rest
SHADE_PRESSED = -42         # pixel-frame shadow when pressed
SHADE_SHADOW = -28          # pixel-frame shadow at rest
SHADE_TOOLBAR_LIGHT = 24    # toolbar border light edge
SHADE_TOOLBAR_DARK = -32    # toolbar border dark edge
SHADE_TOOLBAR_SEP = 12      # toolbar bottom separator
SHADE_TITLE_SHADOW = -24    # palette / section title shadow
SHADE_PALETTE_HOVER = 10    # palette item hover fill
SHADE_BTN_FILL_PRESS = -4   # button fill when pressed
SHADE_BTN_FILL = -2         # button fill at rest
SHADE_BTN_HOVER = 8         # button hover brighten
SHADE_SEL_FILL = -80        # selection color fill
SHADE_WIDGET_BG_OFF = -6    # widget default bg offset
SHADE_WIDGET_HOVER = 10     # widget bg hover brighten
SHADE_WIDGET_PRESS = -22    # widget bg pressed darken
SHADE_GRID_CANVAS = 14      # canvas grid fallback
PROFILE_ORDER = [
    "esp32os_256x128_gray4",
    "esp32os_240x128_mono",
    "esp32os_240x128_rgb565",
    "oled_128x64",
    "oled_128x32",
    "oled_72x40",
    "oled_128x128_sh1107",
    "oled_256x64_ssd1322",
    "tft_160x128_st7735",
    "tft_160x80_st7735",
    "tft_240x135_st7789",
    "tft_240x240_st7789",
    "tft_320x240",
    "tft_480x320",
]
PREFS_PATH = Path("designer_prefs.json")

# Device-first palette (OLED-friendly dark UI; keep keys stable for older code)
PALETTE = {
    "bg": (0, 0, 0),
    "panel": (18, 18, 18),
    "panel_border": (72, 72, 72),
    "canvas_bg": (0, 0, 0),
    "accent_magenta": (220, 220, 220),
    "accent_cyan": (255, 255, 255),
    "accent_yellow": (200, 200, 200),
    "text": (245, 245, 245),
    "muted": (160, 160, 160),
    "grid": (32, 32, 32),
    "selection": (255, 255, 255),
    "locked": (200, 200, 200),
    "guide": (220, 220, 220),
}


def snap(v: int, g: int = GRID) -> int:
    return g * round(v / g)


def clamp(v: int, lo: int, hi: int) -> int:
    """Clamp integer v to [lo, hi]."""
    return max(lo, min(hi, v))


def hex_to_rgb(value: str) -> Tuple[int, int, int]:
    """Parse hex like #RRGGBB or fallback to white."""
    try:
        value = str(value).strip()
        if value.startswith("#") and len(value) == 7:
            return int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16)
    except ValueError:
        pass
    return 255, 255, 255


NAMED_COLORS: Dict[str, Tuple[int, int, int]] = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
    "orange": (255, 165, 0),
    "purple": (128, 0, 128),
}


def safe_save_state(designer: object) -> None:
    """Call designer._save_state() silently catching expected errors."""
    try:
        designer._save_state()  # type: ignore[attr-defined]
    except (TypeError, ValueError, OSError):
        pass


def color_to_rgb(
    value: object, default: Tuple[int, int, int] = (255, 255, 255)
) -> Tuple[int, int, int]:
    s = str(value or "").strip()
    if not s:
        return default
    low = s.lower()
    if low in NAMED_COLORS:
        return NAMED_COLORS[low]
    if low.startswith("0x") and len(low) == 8:
        try:
            v = int(low, 16) & 0xFFFFFF
            return (v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF
        except ValueError:
            return default
    if low.startswith("#"):
        return hex_to_rgb(low)
    return default
