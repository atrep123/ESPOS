from __future__ import annotations

from typing import Optional, Tuple

import pygame

from ..constants import GRID, PALETTE


def draw_frame(app) -> None:
    """Draw background."""
    target = app.window if app.window is not None else app.logical_surface
    if target is None:
        return
    target.fill(PALETTE["bg"])


def render_pixel_text(
    app,
    text: str,
    color: Tuple[int, int, int],
    shadow: Optional[Tuple[int, int, int]] = None,
    scale: Optional[int] = None,
) -> pygame.Surface:
    """Render text without upscaling - keep 1:1 for clarity."""
    font = app.pixel_font
    _ = scale
    base = font.render(text, True, color).convert_alpha()
    if shadow:
        composed = pygame.Surface((base.get_width() + 1, base.get_height() + 1), pygame.SRCALPHA)
        shadow_surf = font.render(text, True, shadow).convert_alpha()
        composed.blit(shadow_surf, (1, 1))
        composed.blit(base, (0, 0))
        return composed
    return base


def draw_pixel_frame(app, rect: pygame.Rect, pressed: bool = False, hover: bool = False) -> None:
    """1px pixel-perfect frame with retro highlight/shadow."""
    light = app._shade(PALETTE["panel_border"], 32 if hover else 20)
    dark = app._shade(PALETTE["panel_border"], -42 if pressed else -28)
    tl = dark if pressed else light
    br = light if pressed else dark
    pygame.draw.line(app.logical_surface, tl, (rect.left, rect.top), (rect.right - 1, rect.top))
    pygame.draw.line(app.logical_surface, tl, (rect.left, rect.top), (rect.left, rect.bottom - 1))
    pygame.draw.line(app.logical_surface, br, (rect.right - 1, rect.top), (rect.right - 1, rect.bottom - 1))
    pygame.draw.line(app.logical_surface, br, (rect.left, rect.bottom - 1), (rect.right - 1, rect.bottom - 1))


def draw_pixel_panel_bg(app, rect: pygame.Rect) -> None:
    """Fill a panel with flat dark background and a thin border."""
    pygame.draw.rect(app.logical_surface, PALETTE["panel"], rect)
    pygame.draw.rect(app.logical_surface, PALETTE["panel_border"], rect, 1)


def _draw_dashed_rect(
    surface: pygame.Surface,
    color: Tuple[int, int, int],
    rect: pygame.Rect,
    dash: int = 3,
    gap: int = 3,
) -> None:
    """Draw a dashed rectangle outline."""
    for start_x in range(rect.left, rect.right, dash + gap):
        end_x = min(rect.right, start_x + dash)
        pygame.draw.line(surface, color, (start_x, rect.top), (end_x - 1, rect.top))
        pygame.draw.line(surface, color, (start_x, rect.bottom - 1), (end_x - 1, rect.bottom - 1))
    for start_y in range(rect.top, rect.bottom, dash + gap):
        end_y = min(rect.bottom, start_y + dash)
        pygame.draw.line(surface, color, (rect.left, start_y), (rect.left, end_y - 1))
        pygame.draw.line(surface, color, (rect.right - 1, start_y), (rect.right - 1, end_y - 1))


def draw_border_style(
    app,
    surface: pygame.Surface,
    rect: pygame.Rect,
    style: str,
    color: Tuple[int, int, int],
) -> None:
    st = str(style or "single").lower()
    if st in {"none", ""}:
        return
    if st == "bold":
        pygame.draw.rect(surface, color, rect, 2)
        return
    if st == "double":
        pygame.draw.rect(surface, color, rect, 1)
        inner = rect.inflate(-4, -4)
        if inner.width > 2 and inner.height > 2:
            pygame.draw.rect(surface, color, inner, 1)
        return
    if st == "rounded":
        radius = max(0, min(6, rect.width // 4, rect.height // 4))
        pygame.draw.rect(surface, color, rect, 1, border_radius=radius)
        return
    if st == "dashed":
        dash = max(2, GRID // 2)
        gap = max(2, dash // 2)
        x = rect.left
        while x < rect.right:
            x2 = min(rect.right - 1, x + dash)
            pygame.draw.line(surface, color, (x, rect.top), (x2, rect.top))
            pygame.draw.line(surface, color, (x, rect.bottom - 1), (x2, rect.bottom - 1))
            x += dash + gap
        y = rect.top
        while y < rect.bottom:
            y2 = min(rect.bottom - 1, y + dash)
            pygame.draw.line(surface, color, (rect.left, y), (rect.left, y2))
            pygame.draw.line(surface, color, (rect.right - 1, y), (rect.right - 1, y2))
            y += dash + gap
        return
    pygame.draw.rect(surface, color, rect, 1)


def draw_bevel_frame(
    app,
    surface: pygame.Surface,
    rect: pygame.Rect,
    base_color: Tuple[int, int, int],
    pressed: bool = False,
) -> None:
    light = app._shade(base_color, 28)
    dark = app._shade(base_color, -28)
    tl = dark if pressed else light
    br = light if pressed else dark
    pygame.draw.line(surface, tl, (rect.left, rect.top), (rect.right - 1, rect.top))
    pygame.draw.line(surface, tl, (rect.left, rect.top), (rect.left, rect.bottom - 1))
    pygame.draw.line(surface, br, (rect.right - 1, rect.top), (rect.right - 1, rect.bottom - 1))
    pygame.draw.line(surface, br, (rect.left, rect.bottom - 1), (rect.right - 1, rect.bottom - 1))
