"""Frame rendering pipeline — extracted from app.py."""
# pyright: reportPrivateUsage=false

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from .. import windowing
from ..constants import PALETTE
from ..perf import RenderCache, compute_dirty_rects
from .canvas import draw_canvas
from .overlays import draw_context_menu, draw_help_overlay, draw_shortcuts_panel, draw_tooltip
from .panels import draw_inspector, draw_palette, draw_status
from .toolbar import draw_scene_tabs, draw_toolbar

if TYPE_CHECKING:
    from ..app import CyberpunkEditorApp


def optimized_draw_frame(app: CyberpunkEditorApp) -> None:
    """Highly optimized frame drawing with caching and dirty rect tracking."""
    cache_key = RenderCache.frame_cache_key(
        app.scale,
        app.state.selected_idx,
        app.state.selected,
        app.show_help_overlay,
        app.designer.current_scene,
        len(app.state.current_scene().widgets),
    )
    cached = app.render_cache.get(cache_key)

    if cached and not app._dirty:
        app.window.blit(cached, (0, 0))
        pygame.display.flip()
        return

    # Smart dirty tracking
    smart_dirty_tracking(app)

    # Only redraw dirty regions
    if len(app.dirty_rects) == 1 and app.dirty_rects[0] == app.layout.canvas_rect:
        # Only canvas changed - keep rest from cache
        draw_canvas(app)
    else:
        # Full redraw needed
        app.logical_surface.fill(PALETTE["bg"])
        if app.clean_preview:
            draw_canvas(app)
        else:
            draw_toolbar(app)
            draw_scene_tabs(app)
            draw_palette(app)
            draw_canvas(app)
            draw_inspector(app)
            draw_status(app)

    if app.show_help_overlay:
        draw_help_overlay(app)

    draw_shortcuts_panel(app)
    draw_context_menu(app)
    draw_tooltip(app)

    # Apply scaling with hardware acceleration if available
    windowing.hardware_accelerated_scale(app)

    # Cache result
    app.render_cache.set(cache_key, app.window.copy())

    # Update display
    if app.vsync_enabled:
        pygame.display.flip()
    else:
        pygame.display.update(app.dirty_rects)
    app._dirty = False
    app._force_full_redraw = False


def smart_dirty_tracking(app: CyberpunkEditorApp) -> None:
    """Track only changed regions for optimized rendering."""
    app.dirty_rects = compute_dirty_rects(
        app.layout,
        app.state,
        force_full=bool(getattr(app, "_force_full_redraw", False)),
        show_help=bool(getattr(app, "show_help_overlay", False)),
    )


def auto_adjust_quality(app: CyberpunkEditorApp) -> None:
    """Automatically adjust quality settings based on performance."""
    if not app.auto_optimize or len(app.fps_history) < 30:
        return

    avg_fps = sum(app.fps_history) / len(app.fps_history)

    if avg_fps < app.min_acceptable_fps:
        # Reduce quality for better performance
        if app.show_grid:
            app.show_grid = False
        elif app.scale > 1:
            app.scale = max(1, app.scale - 1)
        elif not app.panels_collapsed:
            app._toggle_panels()
    elif avg_fps > app.min_acceptable_fps * 2:
        # Can afford higher quality
        if not app.show_grid:
            app.show_grid = True
