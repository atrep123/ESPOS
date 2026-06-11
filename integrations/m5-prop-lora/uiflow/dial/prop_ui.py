# prop_ui.py -- tiny UI-side helpers for the UIFlow2 Dial (kept OUT of prop_frame.py
# so that module stays protocol-only). Upload alongside prop_frame.py to /flash.
#
# Used by the custom "Prop TX" blocks (see blocks/prop_tx_blocks.md) for per-LED hue
# editing and for turning a colour into the 0xRRGGBB the M5 display wants.

def hsv(h, s=1.0, v=1.0):
    """Hue 0..359 deg (+ optional saturation/value 0..1) -> (r, g, b) 0..255."""
    h = h % 360
    c = v * s
    x = c * (1 - abs((h / 60.0) % 2 - 1))
    m = v - c
    if   h < 60:  r, g, b = c, x, 0
    elif h < 120: r, g, b = x, c, 0
    elif h < 180: r, g, b = 0, c, x
    elif h < 240: r, g, b = 0, x, c
    elif h < 300: r, g, b = x, 0, c
    else:         r, g, b = c, 0, x
    return (int((r + m) * 255), int((g + m) * 255), int((b + m) * 255))


def rgb888(c):
    """(r, g, b) -> 0xRRGGBB int for M5 display calls."""
    return (c[0] << 16) | (c[1] << 8) | c[2]


def palette_from_hues(hues):
    """List of hue degrees -> list of (r, g, b). Mirrors the Dial's per-slot palette."""
    return [hsv(h) for h in hues]
