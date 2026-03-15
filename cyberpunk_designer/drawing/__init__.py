"""drawing package — split from monolithic drawing.py."""

from .canvas import (
    draw_canvas,
    draw_distance_indicators,
    draw_overflow_marker,
    draw_rulers,
    draw_selection_info,
    draw_widget_preview,
)
from .frame import (
    auto_adjust_quality,
    optimized_draw_frame,
    smart_dirty_tracking,
)
from .overlays import (
    TOOLBAR_TOOLTIPS,
    draw_context_menu,
    draw_help_overlay,
    draw_shortcuts_panel,
    draw_tooltip,
)
from .panels import (
    draw_inspector,
    draw_palette,
    draw_status,
)
from .primitives import (
    draw_bevel_frame,
    draw_border_style,
    draw_dashed_rect,
    draw_frame,
    draw_pixel_frame,
    draw_pixel_panel_bg,
    load_pixel_font,
    render_pixel_text,
    shade,
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
    "auto_adjust_quality",
    "button",
    "draw_bevel_frame",
    "draw_border_style",
    "draw_canvas",
    "draw_context_menu",
    "draw_dashed_rect",
    "draw_distance_indicators",
    "draw_frame",
    "draw_help_overlay",
    "draw_inspector",
    "draw_overflow_marker",
    "draw_palette",
    "draw_pixel_frame",
    "draw_pixel_panel_bg",
    "draw_rulers",
    "draw_scene_tabs",
    "draw_scrollbar",
    "draw_selection_info",
    "draw_shortcuts_panel",
    "draw_status",
    "draw_text_clipped",
    "draw_text_in_rect",
    "draw_toolbar",
    "draw_tooltip",
    "draw_widget_preview",
    "ellipsize_text_px",
    "load_pixel_font",
    "optimized_draw_frame",
    "panel",
    "render_pixel_text",
    "shade",
    "smart_dirty_tracking",
    "text_width_px",
    "wrap_text_px",
]
