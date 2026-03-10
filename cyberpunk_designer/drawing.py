from __future__ import annotations

import time
from typing import List, Optional, Tuple

import pygame

from ui_designer import HARDWARE_PROFILES, WidgetConfig

from . import font6x8, text_metrics
from .constants import GRID, PALETTE, color_to_rgb, snap


def draw_frame(app) -> None:
    """Draw background scanlines (used by headless tests)."""
    target = app.window if app.window is not None else app.logical_surface
    if target is None:
        return
    base = PALETTE["bg"]
    line_color = app._shade(base, 8)
    target.fill(base)
    height = target.get_height()
    width = target.get_width()
    for y in range(height):
        if y < 3 or y % (GRID * 2) == 0:
            pygame.draw.line(target, line_color, (0, y), (width - 1, y))


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
    pygame.draw.line(
        app.logical_surface, br, (rect.right - 1, rect.top), (rect.right - 1, rect.bottom - 1)
    )
    pygame.draw.line(
        app.logical_surface, br, (rect.left, rect.bottom - 1), (rect.right - 1, rect.bottom - 1)
    )


def draw_pixel_panel_bg(app, rect: pygame.Rect) -> None:
    """Fill a panel with subtle 8px grid for pixel-art aesthetic."""
    pygame.draw.rect(app.logical_surface, PALETTE["panel"], rect)
    shade_h = app._shade(PALETTE["panel"], -6)
    shade_v = app._shade(PALETTE["panel"], 4)
    for x in range(rect.x, rect.right, GRID):
        pygame.draw.line(app.logical_surface, shade_v, (x, rect.y), (x, rect.bottom - 1))
    for y in range(rect.y, rect.bottom, GRID):
        pygame.draw.line(app.logical_surface, shade_h, (rect.x, y), (rect.right - 1, y))
    draw_pixel_frame(app, rect)


def draw_scrollbar(
    app,
    rect: pygame.Rect,
    *,
    scroll: int,
    max_scroll: int,
    content_h: int,
) -> None:
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
    fill = app._shade(PALETTE["panel"], -4 if is_pressed else -2)
    if is_hover and not is_pressed:
        fill = app._shade(fill, 8)
    pygame.draw.rect(app.logical_surface, fill, rect)
    draw_pixel_frame(app, rect, pressed=is_pressed, hover=is_hover)
    app.logical_surface.blit(
        txt,
        (
            rect.x + padding // 2,
            rect.centery - txt.get_height() // 2 + (1 if is_pressed else 0),
        ),
    )
    return rect


def draw_toolbar(app) -> None:
    r = app.layout.toolbar_rect
    line_color = app._shade(PALETTE["bg"], 8)
    pygame.draw.rect(app.logical_surface, line_color, r)
    border_light = app._shade(PALETTE["panel_border"], 24)
    border_dark = app._shade(PALETTE["panel_border"], -32)
    pygame.draw.rect(app.logical_surface, border_light, r, 8)
    pygame.draw.rect(app.logical_surface, border_dark, r.inflate(-8, -8), 4)
    pygame.draw.line(
        app.logical_surface,
        app._shade(PALETTE["panel_border"], 12),
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


def draw_palette(app) -> None:
    r = app.layout.palette_rect
    draw_pixel_panel_bg(app, r)
    title = render_pixel_text(
        app, "Widgets", PALETTE["text"], shadow=app._shade(PALETTE["panel_border"], -24)
    )
    app.logical_surface.blit(title, (r.x + app.pixel_padding, r.y + (app.pixel_padding // 2)))

    row_h = int(app.pixel_row_height)
    content_rect = pygame.Rect(r.x, r.y + row_h, r.width, max(0, r.height - row_h))

    try:
        content_h = int(app._palette_content_height())
    except Exception:
        content_h = 0
    view_h = max(0, int(content_rect.height))
    max_scroll = max(0, content_h - view_h)
    try:
        app.state.palette_scroll = max(
            0, min(max_scroll, int(getattr(app.state, "palette_scroll", 0) or 0))
        )
    except Exception:
        app.state.palette_scroll = 0

    y = content_rect.y - int(getattr(app.state, "palette_scroll", 0) or 0)
    app.palette_hitboxes = []
    app.palette_widget_hitboxes = []
    alt_stride = False

    old_clip = app.logical_surface.get_clip()
    app.logical_surface.set_clip(content_rect)
    try:
        for label, action in app.palette_actions:
            rect = pygame.Rect(r.x + app.pixel_padding, y, r.width - 2 * app.pixel_padding, row_h)
            rect = app._snap_rect(rect)
            hit_rect = rect.clip(content_rect)
            is_hover = app._is_pointer_over(hit_rect)
            is_pressed = is_hover and app.pointer_down
            fill = app._shade(PALETTE["panel"], -8 if alt_stride else -4)
            if is_hover:
                fill = app._shade(fill, 10)
            pygame.draw.rect(app.logical_surface, fill, rect)
            draw_pixel_frame(app, rect, pressed=is_pressed, hover=is_hover)
            draw_rect = rect.move(0, (1 if is_pressed else 0))
            draw_text_clipped(
                app,
                surface=app.logical_surface,
                text=label,
                rect=draw_rect,
                fg=PALETTE["text"],
                padding=app.pixel_padding // 2,
                align="left",
                valign="middle",
                max_lines=1,
            )
            app.palette_hitboxes.append((hit_rect, label.lower(), bool(action)))
            alt_stride = not alt_stride
            y += row_h

        sc = app.state.current_scene()
        y += app.pixel_padding
        for idx, w in enumerate(sc.widgets):
            rect = pygame.Rect(r.x + app.pixel_padding, y, r.width - 2 * app.pixel_padding, row_h)
            rect = app._snap_rect(rect)
            hit_rect = rect.clip(content_rect)
            is_hover = app._is_pointer_over(hit_rect)
            is_pressed = is_hover and app.pointer_down
            fill = app._shade(PALETTE["panel"], -14 if idx % 2 else -10)
            if idx in app.state.selected:
                fill = app._shade(PALETTE["selection"], -80)
            if is_hover:
                fill = app._shade(fill, 8)
            pygame.draw.rect(app.logical_surface, fill, rect)
            draw_pixel_frame(app, rect, pressed=is_pressed, hover=is_hover)
            label = f"[{idx}] {w.type}"
            draw_rect = rect.move(0, (1 if is_pressed else 0))
            draw_text_clipped(
                app,
                surface=app.logical_surface,
                text=label,
                rect=draw_rect,
                fg=PALETTE["text"],
                padding=app.pixel_padding // 2,
                align="left",
                valign="middle",
                max_lines=1,
            )
            app.palette_widget_hitboxes.append((hit_rect, idx))
            y += row_h

        draw_scrollbar(
            app,
            content_rect,
            scroll=int(getattr(app.state, "palette_scroll", 0) or 0),
            max_scroll=max_scroll,
            content_h=content_h,
        )
    finally:
        app.logical_surface.set_clip(old_clip)


def draw_canvas(app) -> None:
    """Draw canvas background + widgets."""
    r = app.layout.canvas_rect
    base = PALETTE.get("canvas_bg", PALETTE["bg"])
    sc = app.state.current_scene()
    try:
        scene_w = int(getattr(sc, "width", 0) or 0)
        scene_h = int(getattr(sc, "height", 0) or 0)
    except Exception:
        scene_w, scene_h = 0, 0

    # If the editor canvas is larger than the target scene, show a clear "device viewport"
    # and keep it centered for nicer maximize/resize behavior.
    scene_rect = getattr(app, "scene_rect", None)
    if not isinstance(scene_rect, pygame.Rect):
        scene_rect = pygame.Rect(r.x, r.y, max(1, scene_w), max(1, scene_h))
    scene_rect.width = min(max(1, scene_rect.width), max(1, r.width))
    scene_rect.height = min(max(1, scene_rect.height), max(1, r.height))
    if not r.contains(scene_rect):
        scene_rect.x = max(r.x, min(r.right - scene_rect.width, scene_rect.x))
        scene_rect.y = max(r.y, min(r.bottom - scene_rect.height, scene_rect.y))
    outside = PALETTE.get("panel", (18, 18, 18))
    pygame.draw.rect(app.logical_surface, outside, r)
    pygame.draw.rect(app.logical_surface, base, scene_rect)
    if scene_rect != r:
        pygame.draw.rect(app.logical_surface, PALETTE["panel_border"], scene_rect, 1)

    if app.show_grid:
        grid_c = PALETTE.get("grid", app._shade(base, 14))
        for x in range(scene_rect.left, scene_rect.right, GRID):
            pygame.draw.line(
                app.logical_surface, grid_c, (x, scene_rect.top), (x, scene_rect.bottom - 1)
            )
        for y in range(scene_rect.top, scene_rect.bottom, GRID):
            pygame.draw.line(
                app.logical_surface, grid_c, (scene_rect.left, y), (scene_rect.right - 1, y)
            )

    origin_x = int(scene_rect.x)
    origin_y = int(scene_rect.y)
    padding = max(2, app.pixel_padding // 2)

    items = list(enumerate(sc.widgets))
    items.sort(key=lambda t: int(getattr(t[1], "z_index", 0) or 0))

    old_clip = app.logical_surface.get_clip()
    app.logical_surface.set_clip(scene_rect)
    try:
        guides = list(getattr(getattr(app, "state", None), "active_guides", []) or [])
        for orient, pos in guides:
            if orient == "v":
                x = origin_x + int(pos)
                pygame.draw.line(
                    app.logical_surface,
                    PALETTE["guide"],
                    (x, scene_rect.top),
                    (x, scene_rect.bottom - 1),
                )
            elif orient == "h":
                y = origin_y + int(pos)
                pygame.draw.line(
                    app.logical_surface,
                    PALETTE["guide"],
                    (scene_rect.left, y),
                    (scene_rect.right - 1, y),
                )

        for idx, w in items:
            if not getattr(w, "visible", True):
                continue
            ww = max(GRID, int(getattr(w, "width", GRID) or GRID))
            wh = max(GRID, int(getattr(w, "height", GRID) or GRID))
            wx = origin_x + int(w.x)
            wy = origin_y + int(w.y)
            rect = pygame.Rect(wx, wy, ww, wh)
            draw_widget_preview(
                app,
                surface=app.logical_surface,
                w=w,
                rect=rect,
                base_bg=base,
                padding=padding,
                is_selected=idx in app.state.selected,
            )

            if idx in app.state.selected:
                pygame.draw.rect(app.logical_surface, PALETTE["selection"], rect, 1)

        if app.state.selected:
            bounds = app._selection_bounds(app.state.selected)
            if bounds is not None:
                sel_rect = pygame.Rect(
                    origin_x + bounds.x, origin_y + bounds.y, bounds.width, bounds.height
                )
                pygame.draw.rect(app.logical_surface, PALETTE["selection"], sel_rect, 2)
                handle = pygame.Rect(sel_rect.right - GRID, sel_rect.bottom - GRID, GRID, GRID)
                pygame.draw.rect(app.logical_surface, PALETTE["selection"], handle)

        if app.sim_input_mode:
            app._ensure_focus()
            if app.focus_idx is not None and 0 <= int(app.focus_idx) < len(sc.widgets):
                fw = sc.widgets[int(app.focus_idx)]
                if app._is_widget_focusable(fw) and bool(getattr(fw, "visible", True)):
                    fx = origin_x + int(getattr(fw, "x", 0) or 0)
                    fy = origin_y + int(getattr(fw, "y", 0) or 0)
                    fw_w = max(GRID, int(getattr(fw, "width", GRID) or GRID))
                    fw_h = max(GRID, int(getattr(fw, "height", GRID) or GRID))
                    frect = pygame.Rect(fx, fy, fw_w, fw_h)
                    c = (
                        PALETTE["accent_yellow"]
                        if not app.focus_edit_value
                        else PALETTE["accent_cyan"]
                    )
                    pygame.draw.rect(app.logical_surface, c, frect.inflate(2, 2), 2)
    finally:
        app.logical_surface.set_clip(old_clip)


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


def text_width_px(app, text: str) -> int:
    try:
        return int(app.pixel_font.size(str(text or ""))[0])
    except Exception:
        return 0


def ellipsize_text_px(app, text: str, max_width_px: int, ellipsis: str = "...") -> str:
    s = str(text or "")
    max_width_px = int(max_width_px)
    if max_width_px <= 0 or not s:
        return ""
    if text_width_px(app, s) <= max_width_px:
        return s
    if text_width_px(app, ellipsis) > max_width_px:
        out = ""
        for ch in s:
            if text_width_px(app, out + ch) <= max_width_px:
                out += ch
            else:
                break
        return out

    lo = 0
    hi = len(s)
    while lo < hi:
        mid = (lo + hi) // 2
        candidate = s[:mid] + ellipsis
        if text_width_px(app, candidate) <= max_width_px:
            lo = mid + 1
        else:
            hi = mid
    cut = max(0, lo - 1)
    return s[:cut] + ellipsis


def wrap_text_px(
    app, text: str, max_width_px: int, max_lines: int, ellipsis: str = "..."
) -> List[str]:
    s = str(text or "").replace("\t", " ").strip()
    max_width_px = int(max_width_px)
    max_lines = max(1, int(max_lines))
    if not s or max_width_px <= 0:
        return []
    if max_lines == 1:
        return [ellipsize_text_px(app, s, max_width_px, ellipsis=ellipsis)]

    paras = [p.strip() for p in s.splitlines() if p.strip()]
    if not paras:
        paras = [s]

    lines: List[str] = []
    truncated = False

    def _push_line(line: str) -> None:
        nonlocal truncated
        if len(lines) >= max_lines:
            truncated = True
            return
        lines.append(line)

    for para in paras:
        words = para.split()
        current = ""
        for word in words:
            cand = word if not current else f"{current} {word}"
            if text_width_px(app, cand) <= max_width_px:
                current = cand
                continue
            if current:
                _push_line(current)
                if len(lines) >= max_lines:
                    break
                current = word
                continue

            chunk = ""
            for ch in word:
                cand2 = chunk + ch
                if text_width_px(app, cand2) <= max_width_px:
                    chunk = cand2
                else:
                    if chunk:
                        _push_line(chunk)
                        if len(lines) >= max_lines:
                            break
                    chunk = ch if text_width_px(app, ch) <= max_width_px else ""
            if len(lines) >= max_lines:
                break
            current = chunk

        if len(lines) >= max_lines:
            break
        if current:
            _push_line(current)
        if len(lines) >= max_lines:
            break

    if truncated and lines:
        lines[-1] = ellipsize_text_px(app, lines[-1], max_width_px, ellipsis=ellipsis)
    return lines[:max_lines]


def draw_text_clipped(
    app,
    surface: pygame.Surface,
    text: str,
    rect: pygame.Rect,
    fg: Tuple[int, int, int],
    padding: int,
    align: str = "left",
    valign: str = "middle",
    max_lines: int = 1,
    ellipsis: str = "...",
    use_device_font: Optional[bool] = None,
) -> None:
    s = str(text or "")
    if not s:
        return
    padding = max(0, int(padding))
    clip_rect = rect.inflate(-padding * 2, -padding * 2)
    if clip_rect.width <= 0 or clip_rect.height <= 0:
        return
    if use_device_font is None:
        use_device = text_metrics.is_device_profile(getattr(app, "hardware_profile", None))
    else:
        use_device = bool(use_device_font)

    if use_device:
        line_h = max(1, int(font6x8.CHAR_H))
        max_chars = int(clip_rect.width) // max(1, int(font6x8.CHAR_W))
        if max_chars <= 0:
            return
        max_lines = max(1, int(max_lines))
        max_lines = min(max_lines, max(1, clip_rect.height // line_h))
        if max_lines > 1:
            lines, _trunc = text_metrics.wrap_text_chars(
                s, max_chars=max_chars, max_lines=max_lines, ellipsis=ellipsis
            )
        else:
            flat = " ".join(s.replace("\t", " ").replace("\r", "").replace("\n", " ").split())
            lines = [text_metrics.ellipsize_chars(flat, max_chars=max_chars, ellipsis=ellipsis)]
    else:
        line_h = max(1, int(app.pixel_font.get_height()))
        max_lines = max(1, int(max_lines))
        max_lines = min(max_lines, max(1, clip_rect.height // line_h))
        if max_lines > 1:
            lines = wrap_text_px(app, s, clip_rect.width, max_lines=max_lines, ellipsis=ellipsis)
        else:
            lines = [ellipsize_text_px(app, s, clip_rect.width, ellipsis=ellipsis)]
    if not lines:
        return

    total_h = len(lines) * line_h
    v = str(valign or "middle").lower()
    if v == "top":
        start_y = clip_rect.y
    elif v == "bottom":
        start_y = clip_rect.bottom - total_h
    else:
        start_y = clip_rect.centery - total_h // 2

    a = str(align or "left").lower()
    old_clip = surface.get_clip()
    # Intersect with any existing clip (palette/inspector/canvas) to avoid drawing outside panels.
    try:
        new_clip = clip_rect.clip(old_clip) if old_clip is not None else clip_rect
    except Exception:
        new_clip = clip_rect
    surface.set_clip(new_clip)
    try:
        y = start_y
        for line in lines:
            if use_device:
                txt = font6x8.render_text(line, fg)
            else:
                fitted = ellipsize_text_px(app, line, clip_rect.width, ellipsis=ellipsis)
                txt = render_pixel_text(app, fitted, fg)
            if a == "center":
                x = clip_rect.centerx - txt.get_width() // 2
            elif a == "right":
                x = clip_rect.right - txt.get_width()
            else:
                x = clip_rect.x
            surface.blit(txt, (x, y))
            y += line_h
    finally:
        surface.set_clip(old_clip)


def draw_text_in_rect(
    app,
    surface: pygame.Surface,
    text: str,
    rect: pygame.Rect,
    fg: Tuple[int, int, int],
    padding: int,
    w: WidgetConfig,
) -> None:
    align = str(getattr(w, "align", "left") or "left").lower()
    valign = str(getattr(w, "valign", "middle") or "middle").lower()
    line_h = max(1, int(app.pixel_font.get_height()))
    # Use one deterministic text path for widget text on device profiles.
    # Avoid per-rect gating that can make top rows render with a different font.
    use_device = text_metrics.is_device_profile(getattr(app, "hardware_profile", None))
    overflow = str(getattr(w, "text_overflow", "ellipsis") or "ellipsis").strip().lower()
    if overflow not in {"ellipsis", "wrap", "clip", "auto"}:
        overflow = "ellipsis"

    use_wrap = overflow == "wrap"
    if overflow == "auto":
        raw = str(text or "")
        flat = raw.replace("\t", " ").replace("\n", " ").strip()
        clip_rect = rect.inflate(-max(0, int(padding)) * 2, -max(0, int(padding)) * 2)
        if use_device:
            max_chars = max(1, int(clip_rect.width) // max(1, int(text_metrics.DEVICE_CHAR_W)))
            use_wrap = clip_rect.height >= int(text_metrics.DEVICE_CHAR_H) * 2 and (
                ("\n" in raw) or (len(flat) > max_chars)
            )
        else:
            use_wrap = clip_rect.height >= line_h * 2 and (
                ("\n" in raw) or (text_width_px(app, flat) > clip_rect.width)
            )

    if use_wrap:
        clip_rect = rect.inflate(-max(0, int(padding)) * 2, -max(0, int(padding)) * 2)
        if use_device:
            max_lines = max(1, int(clip_rect.height) // max(1, int(text_metrics.DEVICE_CHAR_H)))
        else:
            max_lines = max(1, int(clip_rect.height) // line_h)
        try:
            ml = getattr(w, "max_lines", None)
            if ml is not None and str(ml) != "":
                ml_i = int(ml)
                if ml_i > 0:
                    max_lines = min(max_lines, ml_i)
        except Exception:
            pass
    else:
        max_lines = 1

    ell = "" if overflow == "clip" else "..."
    # Keep text rendering mode deterministic for widget labels: either device 6x8
    # on device profiles or pixel pygame font otherwise. This avoids mixed-looking
    # glyphs when auto-detection flips per-rect.
    draw_text_clipped(
        app,
        surface=surface,
        text=text,
        rect=rect,
        fg=fg,
        padding=padding,
        align=align,
        valign=valign,
        max_lines=max_lines,
        ellipsis=ell,
        use_device_font=use_device,
    )


def draw_widget_preview(
    app,
    surface: pygame.Surface,
    w: WidgetConfig,
    rect: pygame.Rect,
    base_bg: Tuple[int, int, int],
    padding: int,
    is_selected: bool,
) -> None:
    kind = str(getattr(w, "type", "") or "").lower()
    style = str(getattr(w, "style", "default") or "default").lower()
    border_style = str(getattr(w, "border_style", "single") or "single").lower()
    locked = bool(getattr(w, "locked", False))
    enabled = bool(getattr(w, "enabled", True))
    border_on = bool(getattr(w, "border", True)) and border_style not in {"none", ""}

    bg = color_to_rgb(getattr(w, "color_bg", ""), default=app._shade(base_bg, -6))
    fg = color_to_rgb(getattr(w, "color_fg", ""), default=PALETTE["text"])

    if "inverse" in style:
        fg, bg = bg, fg
    if "highlight" in style:
        bg = app._shade(bg, 10)
    if not enabled:
        bg = app._shade(bg, -22)
        fg = app._shade(fg, -90)

    label = str(getattr(w, "text", "") or "")

    if kind in {"label", "icon"} and not border_on:
        pass
    else:
        pygame.draw.rect(surface, bg, rect)

    if kind == "panel":
        shade = app._shade(bg, 8)
        y = rect.top + 2
        step = GRID * 2
        while y < rect.bottom - 2:
            pygame.draw.line(surface, shade, (rect.left + 2, y), (rect.right - 3, y))
            y += step

    pressed = str(getattr(w, "state", "default") or "default").lower() in {"pressed", "down"}
    use_device_font = text_metrics.is_device_profile(getattr(app, "hardware_profile", None))

    if kind == "label":
        if label:
            align = str(getattr(w, "align", "left") or "left").lower()
            valign = str(getattr(w, "valign", "middle") or "middle").lower()
            if use_device_font:
                clip_rect = rect.inflate(-padding * 2, -padding * 2)
                if clip_rect.width > 0 and clip_rect.height > 0:
                    max_chars = max(1, int(clip_rect.width) // max(1, int(font6x8.CHAR_W)))
                    flat = " ".join(
                        str(label).replace("\t", " ").replace("\r", "").replace("\n", " ").split()
                    )
                    line = text_metrics.ellipsize_chars(flat, max_chars=max_chars, ellipsis="...")
                    txt = font6x8.render_text(line, fg)
                    if align == "center":
                        x = clip_rect.centerx - txt.get_width() // 2
                    elif align == "right":
                        x = clip_rect.right - txt.get_width()
                    else:
                        x = clip_rect.x
                    if valign == "top":
                        y = clip_rect.y
                    elif valign == "bottom":
                        y = clip_rect.bottom - txt.get_height()
                    else:
                        y = clip_rect.centery - txt.get_height() // 2
                    old_clip = surface.get_clip()
                    try:
                        surface.set_clip(clip_rect)
                        surface.blit(txt, (x, y))
                    finally:
                        surface.set_clip(old_clip)
            else:
                draw_text_clipped(
                    app,
                    surface=surface,
                    text=label,
                    rect=rect,
                    fg=fg,
                    padding=padding,
                    align=align,
                    valign=valign,
                    max_lines=1,
                    ellipsis="...",
                    use_device_font=False,
                )
    elif kind == "checkbox":
        box = pygame.Rect(rect.x + padding, rect.y + padding, GRID, GRID)
        pygame.draw.rect(surface, app._shade(bg, 16), box)
        draw_border_style(app, surface, box, "single", app._shade(fg, -40))
        if getattr(w, "checked", False):
            pygame.draw.line(surface, fg, box.topleft, box.bottomright, 2)
            pygame.draw.line(surface, fg, box.topright, box.bottomleft, 2)
        if label:
            label_rect = pygame.Rect(
                box.right + padding,
                rect.y,
                max(0, rect.right - (box.right + padding)),
                rect.height,
            )
            draw_text_clipped(
                app,
                surface=surface,
                text=label,
                rect=label_rect,
                fg=fg,
                padding=0,
                align="left",
                valign="middle",
                max_lines=1,
                use_device_font=use_device_font,
            )
    elif kind == "progressbar":
        pct = app._value_ratio(w)
        inner = rect.inflate(-2, -2)
        fill_w = int(inner.width * pct)
        fill_rect = pygame.Rect(inner.x, inner.y, fill_w, inner.height)
        pygame.draw.rect(surface, app._shade(fg, -40), fill_rect)
        if label:
            draw_text_in_rect(app, surface, label, rect, fg, padding, w)
    elif kind == "button":
        draw_bevel_frame(app, surface, rect, bg, pressed=pressed)
        if label:
            draw_text_in_rect(app, surface, label, rect, fg, padding, w)
    elif kind == "textbox":
        inner = rect.inflate(-2, -2)
        pygame.draw.rect(surface, app._shade(bg, -10), inner)
        draw_bevel_frame(app, surface, rect, bg, pressed=True)
        if label:
            left_w = WidgetConfig(
                type="label", x=0, y=0, width=0, height=0, text=label, align="left", valign="middle"
            )
            draw_text_in_rect(app, surface, label, rect, fg, padding, left_w)
        if is_selected:
            caret_x = rect.x + padding
            if label:
                shown = ellipsize_text_px(app, label, max(0, rect.width - padding * 2))
                caret_x += app.font.size(shown)[0]
            caret_x = min(rect.right - 3, max(rect.left + 2, caret_x))
            pygame.draw.line(
                surface, fg, (caret_x, rect.y + padding), (caret_x, rect.bottom - padding)
            )
    elif kind == "slider":
        pct = app._value_ratio(w)
        track = rect.inflate(-padding * 2, -padding * 2)
        track_h = max(2, GRID // 3)
        track_y = rect.centery - track_h // 2
        track_rect = pygame.Rect(track.left, track_y, track.width, track_h)
        pygame.draw.rect(surface, app._shade(bg, -18), track_rect)
        fill_rect = pygame.Rect(
            track_rect.left, track_rect.top, int(track_rect.width * pct), track_rect.height
        )
        pygame.draw.rect(surface, app._shade(fg, -30), fill_rect)
        knob_w = max(GRID, GRID * 2)
        knob_x = track_rect.left + int((track_rect.width - knob_w) * pct)
        knob = pygame.Rect(knob_x, rect.y + padding, knob_w, rect.height - padding * 2)
        pygame.draw.rect(surface, app._shade(bg, 10), knob)
        draw_bevel_frame(app, surface, knob, app._shade(bg, 8), pressed=False)
        if label:
            draw_text_in_rect(app, surface, label, rect, fg, padding, w)
    elif kind == "gauge":
        pct = app._value_ratio(w)
        if rect.width >= GRID * 5 and rect.height >= GRID * 5:
            rr = rect.inflate(-padding * 2, -padding * 2)
            pygame.draw.arc(surface, app._shade(bg, -22), rr, 3.14159 * 0.75, 3.14159 * 2.25, 2)
            pygame.draw.arc(
                surface, app._shade(fg, -10), rr, 3.14159 * 0.75, 3.14159 * (0.75 + 1.5 * pct), 3
            )
            if label:
                draw_text_in_rect(app, surface, label, rect, fg, padding, w)
        else:
            inner = rect.inflate(-2, -2)
            fill_w = int(inner.width * pct)
            fill_rect = pygame.Rect(inner.x, inner.y, fill_w, inner.height)
            pygame.draw.rect(surface, app._shade(fg, -40), fill_rect)
    elif kind == "chart":
        inner = rect.inflate(-padding * 2, -padding * 2)
        pygame.draw.rect(surface, app._shade(bg, -8), inner)
        points = list(getattr(w, "data_points", []) or [])
        if not points:
            points = [0, 10, 5, 12, 8, 14]
        chart_mode = (
            style if style in {"bar", "line"} else ("bar" if "bar" in label.lower() else "line")
        )
        p_min = min(points)
        p_max = max(points)
        denom = max(1, p_max - p_min)
        n = max(1, len(points))
        if chart_mode == "bar":
            bar_w = max(1, (inner.width // n) - 2)
            for i, v in enumerate(points):
                x = inner.left + i * (inner.width // n) + 1
                h = int((v - p_min) / denom * max(1, inner.height - 2))
                bar = pygame.Rect(x, inner.bottom - 1 - h, bar_w, h)
                pygame.draw.rect(surface, app._shade(fg, -20), bar)
        else:
            coords: List[Tuple[int, int]] = []
            for i, v in enumerate(points):
                x = inner.left + int(i * (inner.width - 1) / max(1, n - 1))
                y = inner.bottom - 1 - int((v - p_min) / denom * max(1, inner.height - 2))
                coords.append((x, y))
            if len(coords) >= 2:
                pygame.draw.lines(surface, app._shade(fg, -10), False, coords, 2)
            for x, y in coords:
                pygame.draw.rect(surface, app._shade(fg, -10), pygame.Rect(x - 1, y - 1, 3, 3))
        if label:
            head = pygame.Rect(rect.x, rect.y, rect.width, GRID * 2)
            head_w = WidgetConfig(
                type="label", x=0, y=0, width=0, height=0, text=label, align="left", valign="top"
            )
            draw_text_in_rect(app, surface, label, head, fg, padding, head_w)
    elif kind == "icon":
        icon = str(getattr(w, "icon_char", "") or label or "@")
        draw_text_clipped(
            app,
            surface=surface,
            text=icon,
            rect=rect,
            fg=fg,
            padding=padding,
            align="center",
            valign="middle",
            max_lines=1,
            use_device_font=use_device_font,
        )
    else:
        if label:
            draw_text_in_rect(app, surface, label, rect, fg, padding, w)

    if border_on:
        border_c = PALETTE["locked"] if locked else app._shade(fg, -40)
        draw_border_style(app, surface, rect, border_style, border_c)
    if locked:
        hatch = app._shade(PALETTE["locked"], -40)
        step = GRID
        x = rect.left - rect.height
        while x < rect.right + rect.height:
            pygame.draw.line(surface, hatch, (x, rect.top), (x + rect.height, rect.bottom))
            x += step

    if app.show_overflow_warnings and text_metrics.is_device_profile(app.hardware_profile):
        txt = str(getattr(w, "text", "") or "")
        if kind == "icon":
            txt = str(getattr(w, "icon_char", "") or txt or "@")
        if txt.strip() and text_metrics.text_truncates_in_widget(w, txt):
            draw_overflow_marker(app, surface, rect)


def draw_overflow_marker(app, surface: pygame.Surface, rect: pygame.Rect) -> None:
    if surface is None or rect.width <= 0 or rect.height <= 0:
        return
    _ = app
    size = max(6, min(10, rect.width, rect.height))
    x1 = rect.right - 2
    y1 = rect.top + 1
    points = [(x1, y1), (x1 - size, y1), (x1, y1 + size)]
    pygame.draw.polygon(surface, (255, 80, 80), points)


def draw_inspector(app) -> None:
    """Inspector panel with cached hitboxes (click row to edit)."""
    r = app.layout.inspector_rect
    draw_pixel_panel_bg(app, r)
    rows, warning, _sel = app._compute_inspector_rows()

    row_h = int(app.pixel_row_height)
    content_rect = pygame.Rect(r.x, r.y + row_h, r.width, max(0, r.height - row_h))

    try:
        content_h = int(app._inspector_content_height())
    except Exception:
        content_h = 0
    view_h = max(0, int(content_rect.height))
    max_scroll = max(0, content_h - view_h)
    try:
        app.state.inspector_scroll = max(
            0, min(max_scroll, int(getattr(app.state, "inspector_scroll", 0) or 0))
        )
    except Exception:
        app.state.inspector_scroll = 0

    y = content_rect.y - int(getattr(app.state, "inspector_scroll", 0) or 0)
    app.inspector_hitboxes = []
    alt_stride = False

    title = render_pixel_text(
        app, "Inspector", PALETTE["text"], shadow=app._shade(PALETTE["panel_border"], -24)
    )
    app.logical_surface.blit(title, (r.x + app.pixel_padding, r.y + (app.pixel_padding // 2)))

    edit_key = app.state.inspector_selected_field
    edit_buf = app.state.inspector_input_buffer

    old_clip = app.logical_surface.get_clip()
    app.logical_surface.set_clip(content_rect)
    try:
        for key, text in rows:
            rect = pygame.Rect(r.x + app.pixel_padding, y, r.width - 2 * app.pixel_padding, row_h)
            rect = app._snap_rect(rect)
            hit_rect = rect.clip(content_rect)
            is_hover = app._is_pointer_over(hit_rect)
            is_pressed = is_hover and app.pointer_down
            is_editing = bool(edit_key) and key == edit_key
            fill = app._shade(PALETTE["panel"], -8 if alt_stride else -4)
            if key == "resources" and warning:
                fill = app._shade(PALETTE["locked"], -80)
            if is_editing:
                fill = app._shade(PALETTE["accent_cyan"], -210)
            if is_hover:
                fill = app._shade(fill, 10)
            pygame.draw.rect(app.logical_surface, fill, rect)
            draw_pixel_frame(app, rect, pressed=is_pressed, hover=is_hover)
            display = str(text)
            if is_editing:
                display = f"{key}: {edit_buf}_"
            draw_rect = rect.move(0, (1 if is_pressed else 0))
            draw_text_clipped(
                app,
                surface=app.logical_surface,
                text=display,
                rect=draw_rect,
                fg=PALETTE["text"],
                padding=app.pixel_padding // 2,
                align="left",
                valign="middle",
                max_lines=1,
            )
            app.inspector_hitboxes.append((hit_rect, str(key)))
            alt_stride = not alt_stride
            y += row_h

        draw_scrollbar(
            app,
            content_rect,
            scroll=int(getattr(app.state, "inspector_scroll", 0) or 0),
            max_scroll=max_scroll,
            content_h=content_h,
        )
    finally:
        app.logical_surface.set_clip(old_clip)


def draw_status(app) -> None:
    """Status bar with file/selection info."""
    r = app.layout.status_rect
    fill = app._shade(PALETTE["panel"], -6)
    pygame.draw.rect(app.logical_surface, fill, r)
    draw_pixel_frame(app, r)
    try:
        sc = app.state.current_scene()
    except Exception:
        sc = None

    dirty_mark = "*" if app._dirty else ""
    file_label = getattr(app.json_path, "name", "scene.json")
    dim = ""
    if sc is not None:
        dim = f"{int(getattr(sc, 'width', 0))}x{int(getattr(sc, 'height', 0))}"
    left = f"{dirty_mark}{file_label}  {dim}".strip()

    w = app.state.selected_widget()
    if w is None:
        sel = "sel: -"
    else:
        sel = f"sel: {w.type} {int(w.x)},{int(w.y)} {int(w.width)}x{int(w.height)}"
    mode = "IN" if app.sim_input_mode else "ED"
    focus = ""
    if app.sim_input_mode and sc is not None:
        app._ensure_focus()
        if app.focus_idx is not None and 0 <= int(app.focus_idx) < len(sc.widgets):
            fw = sc.widgets[int(app.focus_idx)]
            focus = f" focus:{int(app.focus_idx)}:{fw.type}"
            if app.focus_edit_value:
                focus += ":edit"
    right = f"{sel}  snap:{int(app.snap_enabled)} grid:{int(app.show_grid)} mode:{mode}{focus}"

    msg = ""
    if app.dialog_message and time.time() < float(getattr(app, "_status_until_ts", 0.0)):
        msg = app.dialog_message

    pad = max(2, app.pixel_padding // 2)
    x0 = r.x + pad
    x1 = r.right - pad
    content_w = max(0, x1 - x0)
    third = max(1, content_w // 3)
    left_rect = pygame.Rect(x0, r.y, third, r.height)
    msg_rect = pygame.Rect(x0 + third, r.y, third, r.height)
    right_rect = pygame.Rect(x0 + (2 * third), r.y, max(0, content_w - (2 * third)), r.height)

    draw_text_clipped(
        app,
        surface=app.logical_surface,
        text=left,
        rect=left_rect,
        fg=PALETTE["text"],
        padding=0,
        align="left",
        valign="middle",
        max_lines=1,
    )
    if msg:
        draw_text_clipped(
            app,
            surface=app.logical_surface,
            text=str(msg),
            rect=msg_rect,
            fg=PALETTE["accent_yellow"],
            padding=0,
            align="center",
            valign="middle",
            max_lines=1,
        )
    draw_text_clipped(
        app,
        surface=app.logical_surface,
        text=right,
        rect=right_rect,
        fg=PALETTE["muted"],
        padding=0,
        align="right",
        valign="middle",
        max_lines=1,
    )


def draw_help_overlay(app) -> None:
    """Draw a modal help/self-check overlay (toggle via F1)."""
    if not bool(getattr(app, "show_help_overlay", False)):
        return
    surface = getattr(app, "logical_surface", None)
    if surface is None:
        return
    layout = getattr(app, "layout", None)
    if layout is None:
        return
    w = int(getattr(layout, "width", 0) or 0)
    h = int(getattr(layout, "height", 0) or 0)
    if w <= 0 or h <= 0:
        return

    # Dim background.
    dim = pygame.Surface((w, h), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 160))
    surface.blit(dim, (0, 0))

    pad = max(2, int(getattr(app, "pixel_padding", 0) or 0))
    row_h = max(1, int(getattr(app, "pixel_row_height", 0) or 0))

    margin = GRID * 2
    panel_w = max(GRID * 22, min(w - margin * 2, GRID * 70))
    panel_h = max(GRID * 18, min(h - margin * 2, GRID * 48))
    panel_w = max(GRID * 10, snap(panel_w))
    panel_h = max(GRID * 10, snap(panel_h))
    x = snap((w - panel_w) // 2)
    y = snap((h - panel_h) // 2)
    panel_rect = pygame.Rect(x, y, panel_w, panel_h)

    draw_pixel_panel_bg(app, panel_rect)

    title = "Help / Self-check"
    title_hint = "F1/Esc/click = close"
    title_rect = pygame.Rect(panel_rect.x + pad, panel_rect.y, panel_rect.width - 2 * pad, row_h)
    draw_text_clipped(
        app,
        surface=surface,
        text=f"{title} ({title_hint})",
        rect=title_rect,
        fg=PALETTE["accent_yellow"],
        padding=0,
        align="left",
        valign="middle",
        max_lines=1,
        use_device_font=False,
    )

    content_rect = pygame.Rect(
        panel_rect.x + pad,
        panel_rect.y + row_h,
        panel_rect.width - 2 * pad,
        panel_rect.height - row_h - pad,
    )
    if content_rect.width <= 0 or content_rect.height <= 0:
        return

    shortcuts = [
        "Mouse: LMB select/drag | handles resize",
        "Ctrl+S save | Ctrl+L load",
        "Ctrl+Z undo | Ctrl+Shift+Z redo",
        "Ctrl+Y redo | Ctrl+D duplicate",
        "Ctrl+C/X/V copy/cut/paste | Del delete",
        "Ctrl+F fit text | Ctrl+Shift+F fit widget",
        "F2 input-mode | F3 overflow warn",
        "G grid | X snap | Tab panels",
        "Ctrl+0 reset zoom | Ctrl+/- zoom",
        "F11 fullscreen | F12 screenshot",
        "Ctrl+Alt+Arrows align | Ctrl+Alt+H/V distribute",
        "Ctrl+Alt+W/T match size | Ctrl+Alt+C center",
    ]

    sc = None
    try:
        sc = app.state.current_scene()
    except Exception:
        sc = None

    profile_label = str(getattr(app, "hardware_profile", "") or "")
    if profile_label and profile_label in HARDWARE_PROFILES:
        try:
            profile_label = str(HARDWARE_PROFILES[profile_label].get("label") or profile_label)
        except Exception:
            pass
    if not profile_label:
        profile_label = "none"

    scene_dims = "?"
    widgets_count = "?"
    if sc is not None:
        try:
            scene_dims = f"{int(getattr(sc, 'width', 0))}x{int(getattr(sc, 'height', 0))}"
        except Exception:
            scene_dims = "?"
        try:
            widgets_count = str(len(getattr(sc, "widgets", []) or []))
        except Exception:
            widgets_count = "?"

    est = None
    try:
        est = app.designer.estimate_resources(profile=getattr(app, "hardware_profile", None))
    except Exception:
        est = None
    res_line = "resources: n/a"
    overlaps = 0
    if est:
        try:
            res_line = f"resources: FB {float(est.get('framebuffer_kb', 0.0)):.1f}KB | Flash {float(est.get('flash_kb', 0.0)):.1f}KB"
        except Exception:
            res_line = "resources: (error)"
        try:
            overlaps = int(est.get("overlaps", 0) or 0)
        except Exception:
            overlaps = 0

    sel_count = 0
    try:
        sel_count = int(len(getattr(app.state, "selected", []) or []))
    except Exception:
        sel_count = 0

    info = [
        f"file: {getattr(getattr(app, 'json_path', None), 'name', 'scene.json')}",
        f"profile: {profile_label}",
        f"scene: {scene_dims} | widgets: {widgets_count}",
        res_line,
        f"overlaps: {overlaps}" if overlaps else "overlaps: 0",
        f"scale: {int(getattr(app, 'scale', 1) or 1)} | locked: {int(bool(getattr(app, '_scale_locked', False)))}",
        f"snap: {int(bool(getattr(app, 'snap_enabled', True)))} | grid: {int(bool(getattr(app, 'show_grid', True)))}",
        f"selected: {sel_count} | panels: {'collapsed' if bool(getattr(app, 'panels_collapsed', False)) else 'open'}",
        f"mode: {'IN' if bool(getattr(app, 'sim_input_mode', False)) else 'ED'}",
    ]

    gap = pad
    use_cols = content_rect.width >= GRID * 70
    if use_cols:
        col_w = max(GRID * 18, (content_rect.width - gap) // 2)
        left = pygame.Rect(content_rect.x, content_rect.y, col_w, content_rect.height)
        right = pygame.Rect(
            content_rect.x + col_w + gap,
            content_rect.y,
            content_rect.width - col_w - gap,
            content_rect.height,
        )

        header_h = min(row_h, max(1, content_rect.height // 6))
        left_header = pygame.Rect(left.x, left.y, left.width, header_h)
        left_body = pygame.Rect(left.x, left.y + header_h, left.width, left.height - header_h)
        right_header = pygame.Rect(right.x, right.y, right.width, header_h)
        right_body = pygame.Rect(right.x, right.y + header_h, right.width, right.height - header_h)

        draw_text_clipped(
            app,
            surface=surface,
            text="Shortcuts",
            rect=left_header,
            fg=PALETTE["accent_cyan"],
            padding=0,
            align="left",
            valign="top",
            max_lines=1,
            use_device_font=False,
        )
        draw_text_clipped(
            app,
            surface=surface,
            text="\n".join(shortcuts),
            rect=left_body,
            fg=PALETTE["text"],
            padding=0,
            align="left",
            valign="top",
            max_lines=999,
            use_device_font=False,
        )
        draw_text_clipped(
            app,
            surface=surface,
            text="Self-check",
            rect=right_header,
            fg=PALETTE["accent_cyan"],
            padding=0,
            align="left",
            valign="top",
            max_lines=1,
            use_device_font=False,
        )
        draw_text_clipped(
            app,
            surface=surface,
            text="\n".join(info),
            rect=right_body,
            fg=PALETTE["text"],
            padding=0,
            align="left",
            valign="top",
            max_lines=999,
            use_device_font=False,
        )
    else:
        combined = "\n".join(["Shortcuts"] + shortcuts + ["", "Self-check"] + info)
        draw_text_clipped(
            app,
            surface=surface,
            text=combined,
            rect=content_rect,
            fg=PALETTE["text"],
            padding=0,
            align="left",
            valign="top",
            max_lines=999,
            use_device_font=False,
        )
