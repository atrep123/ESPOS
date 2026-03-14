"""Toolbar buttons and scene tab strip rendering."""

from __future__ import annotations

import pygame

from ..constants import GRID, PALETTE, snap
from .primitives import render_pixel_text
from .widgets import button


def draw_toolbar(app) -> None:
    """Render the top toolbar row with file, view, and action buttons."""
    r = app.layout.toolbar_rect
    pygame.draw.rect(app.logical_surface, PALETTE["panel"], r)
    pygame.draw.line(
        app.logical_surface,
        PALETTE["panel_border"],
        (r.left, r.bottom - 1),
        (r.right, r.bottom - 1),
    )
    app.toolbar_hitboxes = []
    x = snap(r.x + GRID)
    y = snap(r.y + GRID)
    for lab, _action in app.toolbar_actions:
        rect = button(app, lab, (x, y))
        app.toolbar_hitboxes.append((rect, lab.lower()))
        x += rect.width + GRID
    ref_rect = button(app, "Refresh Ports", (x, y))
    app.toolbar_hitboxes.append((ref_rect, "refresh_ports"))


def draw_scene_tabs(app) -> None:
    """Draw a horizontal scene tab bar below the toolbar."""
    r = app.layout.scene_tabs_rect
    if r.height <= 0:
        return
    # Background
    fill = app._shade(PALETTE["panel"], 4)
    pygame.draw.rect(app.logical_surface, fill, r)
    # Bottom border
    pygame.draw.line(
        app.logical_surface,
        PALETTE["panel_border"],
        (r.left, r.bottom - 1),
        (r.right, r.bottom - 1),
    )

    app.tab_hitboxes = []
    app.tab_close_hitboxes = []
    app.tab_scroll_hitboxes = []
    try:
        names = list(app.designer.scenes.keys())
    except AttributeError:
        return
    if not names:
        return

    current = getattr(app.designer, "current_scene", "")
    multi = len(names) > 1
    pad = max(2, app.pixel_padding // 2)
    y = r.y + 1
    tab_h = r.height - 2

    # Pre-measure total tabs width to detect overflow
    dirty_scenes = getattr(app, "_dirty_scenes", set())
    tab_widths = []
    tab_labels = []
    for name in names:
        label = f"*{name}" if name in dirty_scenes else name
        tab_labels.append(label)
        txt_surf = render_pixel_text(app, label, PALETTE["text"])
        tw = txt_surf.get_width()
        close_w = pad * 3 if multi else 0
        tab_widths.append(tw + pad * 4 + close_w)
    total_w = sum(tab_widths) + pad * (len(names) + 1)

    # "+ New" hint width
    hint_surf = render_pixel_text(app, "+ New", PALETTE["muted"])
    hint_total_w = hint_surf.get_width() + pad * 5

    overflow = total_w + hint_total_w > r.width
    arrow_w = pad * 4 if overflow else 0

    # Scroll offset
    tab_scroll = int(getattr(app, "_tab_scroll", 0) or 0)
    content_w = r.width - 2 * arrow_w - pad
    max_scroll = max(0, total_w + hint_total_w - content_w)
    tab_scroll = max(0, min(max_scroll, tab_scroll))
    app._tab_scroll = tab_scroll

    # Auto-scroll to keep active tab visible
    offset = pad
    for i, name in enumerate(names):
        if name == current:
            tab_left = offset - tab_scroll
            tab_right = tab_left + tab_widths[i]
            if tab_left < 0:
                tab_scroll = max(0, offset - pad)
                app._tab_scroll = tab_scroll
            elif tab_right > content_w:
                tab_scroll = max(0, offset + tab_widths[i] - content_w + pad)
                app._tab_scroll = tab_scroll
            break
        offset += tab_widths[i] + pad

    # Draw scroll arrows if overflow
    if overflow:
        # Left arrow
        left_rect = pygame.Rect(r.x, y, arrow_w, tab_h)
        left_hover = app._is_pointer_over(left_rect)
        left_fg = PALETTE["text"] if tab_scroll > 0 else PALETTE["muted"]
        if left_hover and tab_scroll > 0:
            left_fg = PALETTE["accent_cyan"]
        arr_surf = render_pixel_text(app, "<", left_fg)
        ax = left_rect.x + (arrow_w - arr_surf.get_width()) // 2
        ay = left_rect.y + (tab_h - arr_surf.get_height()) // 2
        app.logical_surface.blit(arr_surf, (ax, ay))
        app.tab_scroll_hitboxes.append((left_rect, -1))  # -1 = scroll left

        # Right arrow
        right_rect = pygame.Rect(r.right - arrow_w, y, arrow_w, tab_h)
        right_hover = app._is_pointer_over(right_rect)
        right_fg = PALETTE["text"] if tab_scroll < max_scroll else PALETTE["muted"]
        if right_hover and tab_scroll < max_scroll:
            right_fg = PALETTE["accent_cyan"]
        arr_surf = render_pixel_text(app, ">", right_fg)
        ax = right_rect.x + (arrow_w - arr_surf.get_width()) // 2
        ay = right_rect.y + (tab_h - arr_surf.get_height()) // 2
        app.logical_surface.blit(arr_surf, (ax, ay))
        app.tab_scroll_hitboxes.append((right_rect, 1))  # 1 = scroll right

    # Clip and draw tabs
    content_x = r.x + arrow_w
    content_rect = pygame.Rect(content_x, r.y, r.width - 2 * arrow_w, r.height)
    old_clip = app.logical_surface.get_clip()
    app.logical_surface.set_clip(content_rect)

    x = content_x + pad - tab_scroll
    for i, name in enumerate(names):
        is_active = name == current
        tab_w = tab_widths[i]
        tab_rect = pygame.Rect(x, y, tab_w, tab_h)

        if is_active:
            active_bg = app._shade(PALETTE["panel"], 20)
            pygame.draw.rect(app.logical_surface, active_bg, tab_rect)
            light = app._shade(PALETTE["panel_border"], 20)
            pygame.draw.line(
                app.logical_surface,
                light,
                (tab_rect.left, tab_rect.top),
                (tab_rect.right - 1, tab_rect.top),
            )
            pygame.draw.line(
                app.logical_surface,
                light,
                (tab_rect.left, tab_rect.top),
                (tab_rect.left, tab_rect.bottom - 1),
            )
            pygame.draw.line(
                app.logical_surface,
                light,
                (tab_rect.right - 1, tab_rect.top),
                (tab_rect.right - 1, tab_rect.bottom - 1),
            )
            fg = PALETTE["text"]
        else:
            fg = PALETTE["muted"]

        txt_surf = render_pixel_text(app, tab_labels[i], fg)
        tx = tab_rect.x + pad * 2
        ty = tab_rect.y + (tab_h - txt_surf.get_height()) // 2
        app.logical_surface.blit(txt_surf, (tx, ty))

        if multi:
            cx = tab_rect.right - pad * 2 - 2
            cy = tab_rect.y + 2
            cw = pad * 2
            ch = tab_h - 4
            close_rect = pygame.Rect(cx, cy, cw, ch)
            close_hover = app._is_pointer_over(close_rect)
            close_fg = PALETTE["locked"] if close_hover else PALETTE["muted"]
            x_surf = render_pixel_text(app, "x", close_fg)
            x_tx = cx + (cw - x_surf.get_width()) // 2
            x_ty = cy + (ch - x_surf.get_height()) // 2
            app.logical_surface.blit(x_surf, (x_tx, x_ty))
            app.tab_close_hitboxes.append((close_rect, i, name))

        app.tab_hitboxes.append((tab_rect, i, name))
        x += tab_w + pad

    # "+ New" hint
    hint_w = hint_surf.get_width() + pad * 4
    hint_rect = pygame.Rect(x, y, hint_w, tab_h)
    hx = hint_rect.x + (hint_w - hint_surf.get_width()) // 2
    hy = hint_rect.y + (tab_h - hint_surf.get_height()) // 2
    app.logical_surface.blit(hint_surf, (hx, hy))
    app.tab_hitboxes.append((hint_rect, -1, "_new"))

    # Draw drag indicator when dragging a tab
    drag_idx = getattr(app, "_tab_drag_idx", None)
    if drag_idx is not None:
        for rect, tab_idx, _name in app.tab_hitboxes:
            if tab_idx == drag_idx and tab_idx >= 0:
                # Underline the dragged tab with cyan
                pygame.draw.line(
                    app.logical_surface,
                    PALETTE["accent_cyan"],
                    (rect.left, rect.bottom - 1),
                    (rect.right - 1, rect.bottom - 1),
                )
                break

    app.logical_surface.set_clip(old_clip)
