from __future__ import annotations

from typing import List, Tuple

import pygame

from ui_designer import WidgetConfig

from .. import text_metrics
from ..constants import GRID, PALETTE, color_to_rgb
from .primitives import _draw_dashed_rect, draw_bevel_frame, draw_border_style, render_pixel_text
from .text import draw_text_clipped, draw_text_in_rect, ellipsize_text_px


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

    # Center crosshair guides
    if getattr(app, "show_center_guides", False):
        gc = PALETTE.get("guide", (80, 200, 220))
        cx = scene_rect.left + scene_rect.width // 2
        cy = scene_rect.top + scene_rect.height // 2
        pygame.draw.line(app.logical_surface, gc, (cx, scene_rect.top), (cx, scene_rect.bottom - 1))
        pygame.draw.line(app.logical_surface, gc, (scene_rect.left, cy), (scene_rect.right - 1, cy))

    # Pixel rulers on edges
    preview = bool(getattr(app, "clean_preview", False))
    if not preview and getattr(app, "show_rulers", True):
        _draw_rulers(app, scene_rect, scene_w, scene_h)

    origin_x = int(scene_rect.x)
    origin_y = int(scene_rect.y)
    padding = max(2, app.pixel_padding // 2)

    items = list(enumerate(sc.widgets))
    items.sort(key=lambda t: int(getattr(t[1], "z_index", 0) or 0))

    old_clip = app.logical_surface.get_clip()
    app.logical_surface.set_clip(scene_rect)
    preview = bool(getattr(app, "clean_preview", False))
    try:
        if not preview:
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
            is_selected = idx in app.state.selected
            draw_widget_preview(
                app,
                surface=app.logical_surface,
                w=w,
                rect=rect,
                base_bg=base,
                padding=padding,
                is_selected=is_selected,
            )

            if is_selected and getattr(w, "visible", True) and not preview:
                pygame.draw.rect(app.logical_surface, PALETTE["selection"], rect, 1)

        if app.state.selected and not preview:
            bounds = app._selection_bounds(app.state.selected)
            if bounds is not None:
                sel_rect = pygame.Rect(
                    origin_x + bounds.x, origin_y + bounds.y, bounds.width, bounds.height
                )
                pygame.draw.rect(app.logical_surface, PALETTE["selection"], sel_rect, 2)
                handle = pygame.Rect(sel_rect.right - GRID, sel_rect.bottom - GRID, GRID, GRID)
                pygame.draw.rect(app.logical_surface, PALETTE["selection"], handle)

                # Dimension / position label near selection
                _draw_selection_info(app, sel_rect, bounds, scene_rect)

        # Widget ID / z-index labels overlay
        if not preview and (
            getattr(app, "show_widget_ids", False) or getattr(app, "show_z_labels", False)
        ):
            tiny = app._load_pixel_font(max(8, int(GRID * 0.9)))
            for idx, w in items:
                if not getattr(w, "visible", True):
                    continue
                wx = origin_x + int(w.x)
                wy = origin_y + int(w.y)
                parts = []
                if getattr(app, "show_widget_ids", False):
                    wid = str(getattr(w, "id", "") or f"#{idx}")
                    parts.append(wid)
                if getattr(app, "show_z_labels", False):
                    z = int(getattr(w, "z_index", 0) or 0)
                    parts.append(f"z{z}")
                label_text = " ".join(parts)
                try:
                    lbl = tiny.render(label_text, True, (255, 200, 60))
                    bg_s = pygame.Surface((lbl.get_width() + 2, lbl.get_height()), pygame.SRCALPHA)
                    bg_s.fill((0, 0, 0, 180))
                    app.logical_surface.blit(bg_s, (wx, wy))
                    app.logical_surface.blit(lbl, (wx + 1, wy))
                except Exception:
                    pass

        # Focus order overlay
        if not preview and getattr(app, "show_focus_order", False):
            tiny = app._load_pixel_font(max(8, int(GRID * 0.9)))
            focusable = [
                (idx, w)
                for idx, w in items
                if getattr(w, "visible", True)
                and getattr(w, "enabled", True)
                and w.type
                in {
                    "button",
                    "checkbox",
                    "slider",
                    "gauge",
                    "progressbar",
                    "textbox",
                    "radiobutton",
                }
            ]
            for order, (_idx, w) in enumerate(focusable):
                wx = origin_x + int(w.x) + int(getattr(w, "width", 8) or 8) - GRID
                wy = origin_y + int(w.y)
                try:
                    lbl = tiny.render(str(order), True, (120, 255, 120))
                    bg_s = pygame.Surface((lbl.get_width() + 2, lbl.get_height()), pygame.SRCALPHA)
                    bg_s.fill((0, 60, 0, 200))
                    app.logical_surface.blit(bg_s, (wx, wy))
                    app.logical_surface.blit(lbl, (wx + 1, wy))
                except Exception:
                    pass

        # Hover highlight: subtle dashed outline on widget under cursor
        if not preview and not app.pointer_down and not app.sim_input_mode:
            hover_idx = app.state.hit_test_at(app.pointer_pos, scene_rect)
            if hover_idx is not None and hover_idx not in app.state.selected:
                hw = sc.widgets[hover_idx]
                hx = origin_x + int(hw.x)
                hy = origin_y + int(hw.y)
                hw_w = max(GRID, int(getattr(hw, "width", GRID) or GRID))
                hw_h = max(GRID, int(getattr(hw, "height", GRID) or GRID))
                hr = pygame.Rect(hx, hy, hw_w, hw_h)
                hover_c = PALETTE.get("accent_cyan", (80, 200, 220))
                _draw_dashed_rect(app.logical_surface, hover_c, hr, dash=3, gap=3)
                # Hover info tooltip: type + size
                try:
                    htype = getattr(hw, "type", "?")
                    htip = f"{htype} {hw_w}\u00d7{hw_h}"
                    tiny = app._load_pixel_font(max(8, int(GRID * 0.9)))
                    tip_lbl = tiny.render(htip, True, hover_c)
                    tx = hr.right + 2
                    ty = hr.top
                    if tx + tip_lbl.get_width() > scene_rect.right:
                        tx = hr.left - tip_lbl.get_width() - 2
                    tip_bg = pygame.Surface(
                        (tip_lbl.get_width() + 2, tip_lbl.get_height()), pygame.SRCALPHA
                    )
                    tip_bg.fill((0, 0, 0, 180))
                    app.logical_surface.blit(tip_bg, (tx, ty))
                    app.logical_surface.blit(tip_lbl, (tx + 1, ty))
                except Exception:
                    pass

        # Box select rubber band
        if not preview:
            # Distance indicators when dragging selection
            if app.state.dragging and app.state.selected:
                _draw_distance_indicators(app, sc, origin_x, origin_y, scene_rect)
            box_rect = getattr(app.state, "box_select_rect", None)
            if box_rect is not None and isinstance(box_rect, pygame.Rect):
                sel_c = PALETTE.get("selection", (100, 160, 255))
                fill = pygame.Surface((box_rect.width, box_rect.height), pygame.SRCALPHA)
                fill.fill((*sel_c, 40))
                app.logical_surface.blit(fill, box_rect.topleft)
                pygame.draw.rect(app.logical_surface, sel_c, box_rect, 1)

        if app.sim_input_mode and not preview:
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


def _draw_rulers(app, scene_rect: pygame.Rect, scene_w: int, scene_h: int) -> None:
    """Draw pixel-coordinate rulers on the top and left edges of the scene."""
    ruler_c = PALETTE.get("muted", (100, 100, 100))
    tick_step = 16  # pixels between major ticks
    tick_h = 3  # tick mark height
    surf = app.logical_surface
    sx, sy = scene_rect.x, scene_rect.y

    # Top ruler (horizontal)
    for px in range(tick_step, scene_w + 1, tick_step):
        x = sx + px
        if x > scene_rect.right:
            break
        pygame.draw.line(surf, ruler_c, (x, sy), (x, sy + tick_h))
        if px % (tick_step * 4) == 0:
            lbl = render_pixel_text(app, str(px), ruler_c)
            surf.blit(lbl, (x + 1, sy + 1))

    # Left ruler (vertical)
    for py in range(tick_step, scene_h + 1, tick_step):
        y = sy + py
        if y > scene_rect.bottom:
            break
        pygame.draw.line(surf, ruler_c, (sx, y), (sx + tick_h, y))
        if py % (tick_step * 4) == 0:
            lbl = render_pixel_text(app, str(py), ruler_c)
            surf.blit(lbl, (sx + 1, y + 1))


def _draw_selection_info(app, sel_rect: pygame.Rect, bounds, scene_rect: pygame.Rect) -> None:
    """Show W×H label when resizing, or X,Y when dragging."""
    resizing = getattr(app.state, "resizing", False)
    dragging = getattr(app.state, "dragging", False)
    if not resizing and not dragging:
        return
    if resizing:
        txt = f"{bounds.width}\u00d7{bounds.height}"
    else:
        txt = f"{bounds.x},{bounds.y}"
    try:
        tiny = app._load_pixel_font(max(8, int(GRID * 0.9)))
        lbl = tiny.render(txt, True, PALETTE.get("accent", (255, 220, 0)))
        lx = sel_rect.right + 2
        ly = sel_rect.bottom + 2
        # Keep inside scene rect
        if lx + lbl.get_width() > scene_rect.right:
            lx = sel_rect.left - lbl.get_width() - 2
        if ly + lbl.get_height() > scene_rect.bottom:
            ly = sel_rect.top - lbl.get_height() - 2
        bg_s = pygame.Surface((lbl.get_width() + 2, lbl.get_height()), pygame.SRCALPHA)
        bg_s.fill((0, 0, 0, 200))
        app.logical_surface.blit(bg_s, (lx, ly))
        app.logical_surface.blit(lbl, (lx + 1, ly))
    except Exception:
        pass


def _draw_distance_indicators(
    app, sc, origin_x: int, origin_y: int, scene_rect: pygame.Rect
) -> None:
    """Draw distance lines from dragged selection to scene edges."""
    bounds = app._selection_bounds(app.state.selected)
    if bounds is None:
        return
    sc_w = int(getattr(sc, "width", 0) or 0)
    sc_h = int(getattr(sc, "height", 0) or 0)
    if sc_w <= 0 or sc_h <= 0:
        return

    # Distances in scene coordinates
    left_d = int(bounds.x)
    right_d = int(sc_w - bounds.x - bounds.width)
    top_d = int(bounds.y)
    bottom_d = int(sc_h - bounds.y - bounds.height)

    color = PALETTE.get("accent_yellow", (255, 200, 60))
    surf = app.logical_surface

    # Screen positions of selection edges
    sx = origin_x + int(bounds.x)
    sy = origin_y + int(bounds.y)
    sw = int(bounds.width)
    sh = int(bounds.height)
    mid_y = sy + sh // 2
    mid_x = sx + sw // 2

    # Left distance line
    if left_d > 0:
        lx = origin_x
        pygame.draw.line(surf, color, (lx, mid_y), (sx - 1, mid_y))
        lbl = render_pixel_text(app, str(left_d), color)
        lbl_x = lx + (left_d - lbl.get_width()) // 2
        surf.blit(lbl, (max(lx, lbl_x), mid_y - lbl.get_height() - 1))

    # Right distance line
    if right_d > 0:
        rx = origin_x + sc_w
        pygame.draw.line(surf, color, (sx + sw, mid_y), (rx - 1, mid_y))
        lbl = render_pixel_text(app, str(right_d), color)
        lbl_x = sx + sw + (right_d - lbl.get_width()) // 2
        surf.blit(lbl, (min(rx - lbl.get_width(), lbl_x), mid_y - lbl.get_height() - 1))

    # Top distance line
    if top_d > 0:
        ty = origin_y
        pygame.draw.line(surf, color, (mid_x, ty), (mid_x, sy - 1))
        lbl = render_pixel_text(app, str(top_d), color)
        surf.blit(lbl, (mid_x + 2, ty + (top_d - lbl.get_height()) // 2))

    # Bottom distance line
    if bottom_d > 0:
        by = origin_y + sc_h
        pygame.draw.line(surf, color, (mid_x, sy + sh), (mid_x, by - 1))
        lbl = render_pixel_text(app, str(bottom_d), color)
        surf.blit(lbl, (mid_x + 2, sy + sh + (bottom_d - lbl.get_height()) // 2))


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

    if kind == "checkbox":
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
    elif kind == "radiobutton":
        radius = min(GRID // 2, rect.height // 2 - padding)
        cx = rect.x + padding + radius
        cy = rect.centery
        pygame.draw.circle(surface, app._shade(fg, -40), (cx, cy), radius, 1)
        if getattr(w, "checked", False):
            inner_r = max(2, radius - 3)
            pygame.draw.circle(surface, fg, (cx, cy), inner_r)
        if label:
            label_rect = pygame.Rect(
                cx + radius + padding,
                rect.y,
                max(0, rect.right - (cx + radius + padding)),
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
    elif kind == "box":
        pygame.draw.rect(surface, bg, rect)
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
