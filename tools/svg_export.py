"""SVG export utility for scenes.

Minimal vector export preserving widget geometry & text.
"""
from __future__ import annotations

from html import escape
from typing import List

# Public API
__all__ = ["export_scene_to_svg", "scene_to_svg_string"]


def _svg_header(width: int, height: int) -> str:
    return (f"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            f"<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{width}\" height=\"{height}\" viewBox=\"0 0 {width} {height}\" "+
            "stroke-linejoin=\"round\" font-family=\"monospace\" font-size=\"12\">\n")


def _svg_footer() -> str:
    return "</svg>\n"


_COLOR_MAP = {
    "black": "#000000",
    "white": "#ffffff",
    "red": "#d32f2f",
    "green": "#388e3c",
    "blue": "#1976d2",
    "yellow": "#fbc02d",
    "magenta": "#c2185b",
    "cyan": "#0097a7",
    "gray": "#666666"
}


def _color(c: str, default: str = "#333333") -> str:
    if not c:
        return default
    c_low = c.lower()
    return _COLOR_MAP.get(c_low, default if len(c_low) < 3 else c_low)


def _widget_to_svg(widget, scale: float = 1.0) -> List[str]:
    if not getattr(widget, "visible", True):
        return []
    x = int(widget.x * scale)
    y = int(widget.y * scale)
    w = int(widget.width * scale)
    h = int(widget.height * scale)
    fg = _color(getattr(widget, "color_fg", "white"))
    bg = _color(getattr(widget, "color_bg", "black"))
    lines: List[str] = []
    base_style = f"fill:{bg};stroke:{fg};stroke-width:1"
    tag = escape(getattr(widget, "type", "widget"))
    # Basic rectangle for almost all widgets
    if tag in ("label", "button", "panel", "textbox", "checkbox", "radiobutton", "gauge", "progressbar", "slider", "chart", "icon"):
        lines.append(f"<rect x=\"{x}\" y=\"{y}\" width=\"{w}\" height=\"{h}\" style=\"{base_style}\" rx=\"3\" ry=\"3\" />")
    # Text overlay
    text = escape(getattr(widget, "text", ""))
    if text:
        # Center text inside widget
        tx = x + w / 2
        ty = y + h / 2 + 4  # approx vertical centering adjustment
        lines.append(f"<text x=\"{tx}\" y=\"{ty}\" text-anchor=\"middle\" fill=\"{fg}\">{text}</text>")
    # Gauge / progress representation
    if tag in ("gauge", "progressbar", "slider"):
        try:
            pct = 0
            if widget.max_value > widget.min_value:
                pct = (widget.value - widget.min_value) / (widget.max_value - widget.min_value)
                pct = max(0.0, min(1.0, pct))
            bar_w = int((w - 4) * pct)
            lines.append(f"<rect x=\"{x+2}\" y=\"{y + h//2}\" width=\"{bar_w}\" height=\"4\" fill=\"{fg}\" />")
        except Exception:
            pass
    return lines


def scene_to_svg_string(scene, scale: float = 1.0) -> str:
    """Return SVG string for a scene (non-persistent)."""
    width = int(scene.width * scale)
    height = int(scene.height * scale)
    parts: List[str] = [_svg_header(width, height)]
    # Background
    parts.append(f"<rect x=\"0\" y=\"0\" width=\"{width}\" height=\"{height}\" fill=\"{_color(getattr(scene,'bg_color','black'))}\" />")
    for w in getattr(scene, 'widgets', []):
        parts.extend(_widget_to_svg(w, scale))
    parts.append(_svg_footer())
    return "".join(parts)


def export_scene_to_svg(scene, filename: str, scale: float = 1.0) -> str:
    """Export the given scene to an SVG file. Returns output path."""
    svg = scene_to_svg_string(scene, scale)
    with open(filename, 'w', encoding='utf-8') as f:  # type: TextIO
        f.write(svg)
    return filename
