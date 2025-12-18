from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

# Keep default aligned with the main designer entrypoint (`run_designer.py`).
DEFAULT_JSON = Path("main_scene.json")
SCALE = 2  # preferred scale; UI starts larger and stays integer-scaled
FPS = 60
GRID = 8
GUIDE_TOL = 4
PROFILE_ORDER = [
    "esp32os_256x128_gray4",
    "esp32os_240x128_mono",
    "esp32os_240x128_rgb565",
    "oled_128x64",
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


def hex_to_rgb(value: str) -> Tuple[int, int, int]:
    """Parse hex like #RRGGBB or fallback to white."""
    try:
        value = str(value).strip()
        if value.startswith("#") and len(value) == 7:
            return int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16)
    except Exception:
        pass
    return 255, 255, 255


_NAMED_COLORS: Dict[str, Tuple[int, int, int]] = {
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


def color_to_rgb(value: object, default: Tuple[int, int, int] = (255, 255, 255)) -> Tuple[int, int, int]:
    s = str(value or "").strip()
    if not s:
        return default
    low = s.lower()
    if low in _NAMED_COLORS:
        return _NAMED_COLORS[low]
    if low.startswith("0x") and len(low) == 8:
        try:
            v = int(low, 16) & 0xFFFFFF
            return (v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF
        except Exception:
            return default
    if low.startswith("#"):
        return hex_to_rgb(low)
    return default
