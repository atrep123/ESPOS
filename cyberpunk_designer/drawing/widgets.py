"""Widget-specific drawing: buttons, scrollbars, checkboxes."""

from __future__ import annotations

from typing import Tuple

import pygame

from ..constants import GRID, PALETTE, snap
from .primitives import draw_pixel_panel_bg, render_pixel_text
from .text import draw_text_clipped


def draw_scrollbar(
    app,
    rect: pygame.Rect,
    *,
    scroll: int,
    max_scroll: int,
    content_h: int,
) -> None:
    """Draw a vertical scrollbar thumb inside *rect* proportional to scroll position."""
    if max_scroll <= 0 or rect.width <= 0 or rect.height <= 0:
        return
    scroll = max(0, min(int(scroll), int(max_scroll)))
    content_h = max(int(rect.height), int(content_h))

    track_w = 4
    track = pygame.Rect(rect.right - track_w, rect.y, track_w, rect.height)
    pygame.draw.rect(app.logical_surface, app._shade(PALETTE["panel"], -18), track)

    thumb_h = int((rect.height * rect.height) / max(1, content_h))
    thumb_h = max(GRID, min(int(rect.height), thumb_h))
    travel = max(1, int(rect.height) - thumb_h)
    thumb_y = int(rect.y) + int(travel * (scroll / max(1, int(max_scroll))))
    thumb = pygame.Rect(track.x, thumb_y, track_w, thumb_h)
    pygame.draw.rect(app.logical_surface, app._shade(PALETTE["panel_border"], 24), thumb)
    pygame.draw.rect(app.logical_surface, app._shade(PALETTE["panel_border"], -28), thumb, 1)


def panel(app, rect: pygame.Rect, title: str = "") -> None:
    """Draw a panel background with an optional *title* in the top-left."""
    draw_pixel_panel_bg(app, rect)
    if title:
        title_rect = pygame.Rect(
            rect.x + app.pixel_padding,
            rect.y,
            max(0, rect.width - 2 * app.pixel_padding),
            app.pixel_row_height,
        )
        draw_text_clipped(
            app,
            surface=app.logical_surface,
            text=title,
            rect=title_rect,
            fg=PALETTE["text"],
            padding=0,
            align="left",
            valign="top",
            max_lines=1,
        )


def button(app, label: str, pos: Tuple[int, int]) -> pygame.Rect:
    """Render a small pixel-style button and return its rect."""
    txt = render_pixel_text(app, label, PALETTE["text"])
    padding = max(4, app.pixel_padding // 2)
    width = max(48, txt.get_width() + padding * 2)
    height = max(app.toolbar_h - 4, txt.get_height() + padding)
    rect = pygame.Rect(snap(pos[0]), snap(pos[1]), width, height)
    is_hover = app._is_pointer_over(rect)
    is_pressed = is_hover and app.pointer_down
    fill = app._shade(PALETTE["panel"], 12 if is_hover else 4)
    if is_pressed:
        fill = app._shade(PALETTE["panel"], -4)
    pygame.draw.rect(app.logical_surface, fill, rect)
    pygame.draw.rect(app.logical_surface, PALETTE["panel_border"], rect, 1)
    app.logical_surface.blit(
        txt,
        (
            rect.x + padding // 2,
            rect.centery - txt.get_height() // 2 + (1 if is_pressed else 0),
        ),
    )
    return rect
