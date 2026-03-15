"""Window management: zoom, pan, resize, hit-testing."""

from __future__ import annotations

from typing import Optional, Tuple

import pygame

from .constants import GRID, PALETTE, SCALE, snap
from .layout import Layout


def screen_to_logical(app, x: int, y: int) -> Tuple[int, int]:
    """Convert physical window coordinates to logical (1:1 editor) coordinates."""
    sx = app._render_scale_x if app._render_scale_x > 0 else 1.0
    sy = app._render_scale_y if app._render_scale_y > 0 else 1.0
    ox = app._render_offset_x
    oy = app._render_offset_y
    lx = int((x - ox) / sx)
    ly = int((y - oy) / sy)
    return lx, ly


def _base_layout_size(app, palette_w: int, inspector_w: int) -> Tuple[int, int]:
    """Return minimum (width,height) needed for the editor UI at 1:1 logical scale."""
    canvas_w = int(getattr(app.designer, "width", 0) or 0)
    canvas_h = int(getattr(app.designer, "height", 0) or 0)
    base_w = max(1, canvas_w + int(palette_w) + int(inspector_w))
    base_h = max(
        1,
        canvas_h
        + int(getattr(app, "toolbar_h", 0) or 0)
        + int(getattr(app, "scene_tabs_h", 0) or 0)
        + int(getattr(app, "status_h", 0) or 0),
    )
    return base_w, base_h


def _fit_scale(app, max_w: int, max_h: int, base_w: int, base_h: int) -> int:
    """Compute best-effort integer scale that fits base editor UI into (max_w,max_h)."""
    max_w = max(1, int(max_w))
    max_h = max(1, int(max_h))
    base_w = max(1, int(base_w))
    base_h = max(1, int(base_h))
    fit_w = max_w // base_w
    fit_h = max_h // base_h
    return max(1, min(int(getattr(app, "max_auto_scale", 4) or 4), fit_w, fit_h))


def hardware_accelerated_scale(app) -> None:
    """Use hardware acceleration for scaling if available."""
    win_w, win_h = app.window.get_size()
    render_scale = max(1, min(app.scale, app.max_auto_scale))

    # Check window bounds
    max_scale_w = max(1, win_w // max(1, app.layout.width))
    max_scale_h = max(1, win_h // max(1, app.layout.height))
    render_scale = min(render_scale, max_scale_w, max_scale_h)

    scaled_w = app.layout.width * render_scale
    scaled_h = app.layout.height * render_scale
    app._render_scale_x = float(render_scale)
    app._render_scale_y = float(render_scale)

    # Try hardware accelerated scaling
    try:
        # Use SDL2 hardware acceleration if available
        scaled = pygame.transform.scale(app.logical_surface, (scaled_w, scaled_h))
    except pygame.error:
        # Fallback to software scaling
        scaled = pygame.transform.scale(app.logical_surface, (scaled_w, scaled_h))

    # Center in window
    offset_x = max(0, (win_w - scaled_w) // 2)
    offset_y = max(0, (win_h - scaled_h) // 2)
    app._render_offset_x = offset_x
    app._render_offset_y = offset_y

    app.window.fill(PALETTE["bg"])
    app.window.blit(scaled, (offset_x, offset_y))


def handle_video_resize(app, win_w: int, win_h: int) -> None:
    """Respond to a window resize event by recalculating layout and scale."""
    lock = None
    try:
        if bool(getattr(app, "_scale_locked", False)):
            lock = int(getattr(app, "scale", 1) or 1)
    except (TypeError, ValueError):
        lock = None
    rebuild_layout(app, window_size=(win_w, win_h), force_scene_size=False, lock_scale=lock)


def toggle_fullscreen(app) -> None:
    """Toggle fullscreen."""
    app.fullscreen = not app.fullscreen
    if app.fullscreen:
        info = pygame.display.Info()
        win_w, win_h = (
            int(getattr(info, "current_w", 0) or 0),
            int(getattr(info, "current_h", 0) or 0),
        )
        if win_w <= 0 or win_h <= 0:
            win_w, win_h = app.window.get_size()
    else:
        # Restore to a reasonable windowed size based on current layout/scale.
        base_w, base_h = _base_layout_size(app, app._default_palette_w, app._default_inspector_w)
        scale = max(
            1,
            min(
                int(getattr(app, "scale", SCALE) or SCALE),
                int(getattr(app, "max_auto_scale", 4) or 4),
            ),
        )
        win_w, win_h = base_w * scale, base_h * scale

    lock = None
    try:
        if bool(getattr(app, "_scale_locked", False)):
            lock = int(getattr(app, "scale", 1) or 1)
    except (TypeError, ValueError):
        lock = None
    rebuild_layout(
        app, window_size=(int(win_w), int(win_h)), force_scene_size=False, lock_scale=lock
    )


def compute_scale(app, force_window: Optional[Tuple[int, int]] = None) -> int:
    """Compute the best integer scale factor to fit the editor in the window."""
    palette_w = (
        0 if getattr(app, "panels_collapsed", False) else getattr(app, "_default_palette_w", 0)
    )
    inspector_w = (
        0 if getattr(app, "panels_collapsed", False) else getattr(app, "_default_inspector_w", 0)
    )
    base_w, base_h = _base_layout_size(app, int(palette_w), int(inspector_w))
    margin_w, margin_h = 24, 64
    if force_window:
        max_w, max_h = force_window
    else:
        info = pygame.display.Info()
        max_w = max(1, info.current_w - margin_w)
        max_h = max(1, info.current_h - margin_h)
    return _fit_scale(app, max_w, max_h, base_w, base_h)


def set_scale(app, new_scale: int) -> None:
    """Set the editor zoom level and rebuild layout to match."""
    app.scale = max(1, min(new_scale, app.max_auto_scale))
    try:
        win_size = app.window.get_size() if app.window is not None else None
    except (AttributeError, pygame.error):
        win_size = None
    if win_size:
        rebuild_layout(app, window_size=win_size, force_scene_size=False, lock_scale=app.scale)
        return
    app._mark_dirty()


def recompute_scale_for_window(app, win_w: int, win_h: int) -> None:
    """Recalculate `app.scale` to fit the current base layout in a *win_w* x *win_h* window."""
    palette_w = (
        0 if getattr(app, "panels_collapsed", False) else getattr(app, "_default_palette_w", 0)
    )
    inspector_w = (
        0 if getattr(app, "panels_collapsed", False) else getattr(app, "_default_inspector_w", 0)
    )
    base_w, base_h = _base_layout_size(app, int(palette_w), int(inspector_w))
    app.scale = _fit_scale(app, int(win_w), int(win_h), base_w, base_h)


def rebuild_layout(
    app,
    window_size: Optional[Tuple[int, int]] = None,
    force_scene_size: bool = True,
    lock_scale: Optional[int] = None,
) -> None:
    """Rebuild UI layout."""
    palette_w = (
        0
        if getattr(app, "panels_collapsed", False)
        else int(getattr(app, "_default_palette_w", 0) or 0)
    )
    inspector_w = (
        0
        if getattr(app, "panels_collapsed", False)
        else int(getattr(app, "_default_inspector_w", 0) or 0)
    )

    base_w, base_h = _base_layout_size(app, palette_w, inspector_w)

    if window_size:
        win_w, win_h = int(window_size[0]), int(window_size[1])
        fit = _fit_scale(app, win_w, win_h, base_w, base_h)
        if lock_scale is not None:
            app.scale = max(1, min(int(lock_scale), fit))
        else:
            app.scale = fit
        flags = pygame.FULLSCREEN if getattr(app, "fullscreen", False) else pygame.RESIZABLE
        app.window = pygame.display.set_mode((max(1, win_w), max(1, win_h)), flags)
    else:
        app.scale = compute_scale(app)
        win_w, win_h = base_w * app.scale, base_h * app.scale
        app.window = pygame.display.set_mode((max(1, win_w), max(1, win_h)), pygame.RESIZABLE)

    # Expand logical layout to fill the available window at the chosen integer scale.
    # This removes most of the "black margins" when maximizing the window for small (e.g. 256x128) scenes.
    layout_w = max(base_w, max(1, win_w) // max(1, app.scale))
    layout_h = max(base_h, max(1, win_h) // max(1, app.scale))

    app.layout = Layout(
        layout_w,
        layout_h,
        palette_w=palette_w,
        inspector_w=inspector_w,
        toolbar_h=int(getattr(app, "toolbar_h", 24) or 24),
        status_h=int(getattr(app, "status_h", 18) or 18),
        scene_tabs_h=int(getattr(app, "scene_tabs_h", 0) or 0),
    )
    app.logical_surface = pygame.Surface((app.layout.width, app.layout.height))

    # Cache a centered "device viewport" rect inside the (potentially larger) canvas.
    # This keeps the artboard centered when the window is maximized while preserving
    # scene coordinates (widgets remain relative to 0,0 of the device).
    try:
        cr = app.layout.canvas_rect
        scene_w = int(getattr(getattr(app, "designer", None), "width", 0) or 0)
        scene_h = int(getattr(getattr(app, "designer", None), "height", 0) or 0)
        try:
            if getattr(app, "state", None) is not None:
                sc = app.state.current_scene()
                scene_w = int(getattr(sc, "width", scene_w) or scene_w)
                scene_h = int(getattr(sc, "height", scene_h) or scene_h)
        except (AttributeError, TypeError, ValueError):
            pass
        scene_w = max(1, int(scene_w))
        scene_h = max(1, int(scene_h))
        view_w = max(1, int(getattr(cr, "width", 1) or 1))
        view_h = max(1, int(getattr(cr, "height", 1) or 1))
        w = max(1, min(scene_w, view_w))
        h = max(1, min(scene_h, view_h))
        x = int(cr.x) + int((view_w - scene_w) // 2) if scene_w <= view_w else int(cr.x)
        y = int(cr.y) + int((view_h - scene_h) // 2) if scene_h <= view_h else int(cr.y)
        x = snap(int(x), GRID)
        y = snap(int(y), GRID)
        x = max(int(cr.x), min(int(cr.right) - w, int(x)))
        y = max(int(cr.y), min(int(cr.bottom) - h, int(y)))
        app.scene_rect = pygame.Rect(int(x), int(y), int(w), int(h))
    except (AttributeError, TypeError, ValueError):
        app.scene_rect = app.layout.canvas_rect

    try:
        if getattr(app, "state", None) is not None:
            app.state.layout = app.layout
    except AttributeError:
        pass

    try:
        app._mark_dirty()
    except AttributeError:
        pass

    del force_scene_size, lock_scale
