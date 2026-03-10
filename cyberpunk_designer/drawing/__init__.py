"""drawing package — split from monolithic drawing.py."""

from .canvas import (
    _draw_distance_indicators,
    _draw_rulers,
    _draw_selection_info,
    draw_canvas,
    draw_overflow_marker,
    draw_widget_preview,
)
from .overlays import (
    TOOLBAR_TOOLTIPS,
    draw_context_menu,
    draw_help_overlay,
    draw_tooltip,
)
from .panels import (
    draw_inspector,
    draw_palette,
    draw_status,
)
from .primitives import (
    _draw_dashed_rect,
    draw_bevel_frame,
    draw_border_style,
    draw_frame,
    draw_pixel_frame,
    draw_pixel_panel_bg,
    render_pixel_text,
)
from .text import (
    draw_text_clipped,
    draw_text_in_rect,
    ellipsize_text_px,
    text_width_px,
    wrap_text_px,
)
from .toolbar import (
    draw_scene_tabs,
    draw_toolbar,
)
from .widgets import (
    button,
    draw_scrollbar,
    panel,
)

__all__ = [
    "TOOLBAR_TOOLTIPS",
    "draw_canvas",
    "_draw_rulers",
    "_draw_selection_info",
    "_draw_distance_indicators",
    "draw_widget_preview",
    "draw_overflow_marker",
    "draw_context_menu",
    "draw_tooltip",
    "draw_help_overlay",
    "draw_palette",
    "draw_inspector",
    "draw_status",
    "draw_frame",
    "render_pixel_text",
    "draw_pixel_frame",
    "draw_pixel_panel_bg",
    "_draw_dashed_rect",
    "draw_border_style",
    "draw_bevel_frame",
    "text_width_px",
    "ellipsize_text_px",
    "wrap_text_px",
    "draw_text_clipped",
    "draw_text_in_rect",
    "draw_toolbar",
    "draw_scene_tabs",
    "draw_scrollbar",
    "panel",
    "button",
]
