"""Per-widget-type rendering functions extracted from canvas.draw_widget_preview()."""

from __future__ import annotations

import math
from typing import List, Tuple

import pygame

from ui_designer import WidgetConfig

from .. import font6x8
from ..constants import GRID
from .primitives import draw_bevel_frame, draw_border_style
from .text import draw_text_clipped, draw_text_in_rect, ellipsize_text_px

# Bayer 4×4 ordered dither matrix (thresholds 0..1)
_BAYER4 = [
    [0.0000, 0.5000, 0.1250, 0.6250],
    [0.7500, 0.2500, 0.8750, 0.3750],
    [0.1875, 0.6875, 0.0625, 0.5625],
    [0.9375, 0.4375, 0.8125, 0.3125],
]


def _render_panel(app, surface, rect, w, fg, bg, label, padding):
    """Render a panel widget (hatching lines + label)."""
    shade = app._shade(bg, 8)
    y = rect.top + 2
    step = GRID * 2
    while y < rect.bottom - 2:
        pygame.draw.line(surface, shade, (rect.left + 2, y), (rect.right - 3, y))
        y += step
    if label:
        draw_text_in_rect(app, surface, label, rect, fg, padding, w)


def _render_checkbox(app, surface, rect, w, fg, label, padding, use_device_font):
    """Render a checkbox widget."""
    box_size = min(GRID, max(6, rect.height - padding * 2))
    box = pygame.Rect(rect.x + padding, rect.y + padding, box_size, box_size)
    draw_border_style(app, surface, box, "single", app._shade(fg, -40))
    if getattr(w, "checked", False):
        # Draw X strictly inside the box border (3px inset from border)
        x1 = box.x + 3
        y1 = box.y + 2
        x2 = box.x + box_size - 4
        y2 = box.y + box_size - 3
        if x2 > x1 and y2 > y1:
            pygame.draw.line(surface, fg, (x1, y1), (x2, y2), 2)
            pygame.draw.line(surface, fg, (x2, y1), (x1, y2), 2)
    if label:
        label_rect = pygame.Rect(
            box.right + max(padding, 2),
            rect.y,
            max(0, rect.right - (box.right + max(padding, 2))),
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


def _render_progressbar(app, surface, rect, w, fg, bg, label, padding):
    """Render a progressbar widget."""
    pct = app._value_ratio(w)
    inner = rect.inflate(-2, -2)
    fill_w = int(inner.width * pct)
    # Bayer 4x4 dithered fill — bright leading edge, gradient body
    hi_fill = app._shade(fg, -20)
    lo_fill = app._shade(fg, -55)
    for col_x in range(inner.x, inner.x + fill_w):
        col_ratio = (col_x - inner.x) / max(1, fill_w - 1) if fill_w > 1 else 1.0
        for row_y in range(inner.y, inner.bottom):
            threshold = _BAYER4[row_y % 4][col_x % 4]
            c = hi_fill if col_ratio > threshold else lo_fill
            surface.set_at((col_x, row_y), c)
    # Bright leading edge (1px vertical line)
    if fill_w > 0:
        edge_x = inner.x + fill_w - 1
        for row_y in range(inner.y, inner.bottom):
            surface.set_at((edge_x, row_y), app._shade(fg, 0))
    # Thin border around track
    pygame.draw.rect(surface, app._shade(bg, 20), inner, 1)
    if label:
        draw_text_in_rect(app, surface, label, rect, fg, padding, w)


def _render_button(app, surface, rect, w, fg, bg, label, padding, pressed):
    """Render a button widget."""
    draw_bevel_frame(app, surface, rect, bg, pressed=pressed)
    if label:
        draw_text_in_rect(app, surface, label, rect, fg, padding, w)


def _render_textbox(app, surface, rect, w, fg, bg, label, padding, is_selected):
    """Render a textbox widget."""
    inner = rect.inflate(-2, -2)
    pygame.draw.rect(surface, app._shade(bg, -10), inner)
    draw_bevel_frame(app, surface, rect, bg, pressed=True)
    if label:
        left_w = WidgetConfig(
            type="label", x=0, y=0, width=0, height=0, text=label, align="left", valign="middle"
        )
        draw_text_in_rect(app, surface, label, inner, fg, padding, left_w)
    if is_selected:
        caret_x = inner.x + padding
        if label:
            shown = ellipsize_text_px(app, label, max(0, inner.width - padding * 2))
            caret_x += app.font.size(shown)[0]
        caret_x = min(inner.right - 2, max(inner.left + 1, caret_x))
        pygame.draw.line(
            surface, fg, (caret_x, inner.y + padding), (caret_x, inner.bottom - padding)
        )


def _render_slider(app, surface, rect, w, fg, bg, label, padding):
    """Render a slider widget."""
    pct = app._value_ratio(w)
    track = rect.inflate(-padding * 2, -padding * 2)
    track_h = max(2, GRID // 3)
    track_y = rect.centery - track_h // 2
    track_rect = pygame.Rect(track.left, track_y, track.width, track_h)
    # Track groove: dark inset
    pygame.draw.rect(surface, app._shade(bg, -25), track_rect)
    pygame.draw.rect(surface, app._shade(bg, -10), track_rect, 1)
    # Filled portion with Bayer dither gradient
    fill_w = int(track_rect.width * pct)
    hi_tr = app._shade(fg, -20)
    lo_tr = app._shade(fg, -50)
    for col_x in range(track_rect.left, track_rect.left + fill_w):
        col_ratio = (col_x - track_rect.left) / max(1, fill_w - 1) if fill_w > 1 else 1.0
        for row_y in range(track_rect.top, track_rect.bottom):
            threshold = _BAYER4[row_y % 4][col_x % 4]
            c = hi_tr if col_ratio > threshold else lo_tr
            surface.set_at((col_x, row_y), c)
    # Knob
    knob_w = max(GRID, GRID * 2)
    knob_x = track_rect.left + int((track_rect.width - knob_w) * pct)
    knob = pygame.Rect(knob_x, rect.y + padding, knob_w, rect.height - padding * 2)
    pygame.draw.rect(surface, app._shade(bg, 12), knob)
    draw_bevel_frame(app, surface, knob, app._shade(bg, 10), pressed=False)
    # Knob center line (grip indicator)
    grip_x = knob.centerx
    grip_top = knob.top + 2
    grip_bot = knob.bottom - 2
    pygame.draw.line(surface, app._shade(bg, 30), (grip_x, grip_top), (grip_x, grip_bot), 1)
    if label:
        draw_text_in_rect(app, surface, label, rect, fg, padding, w)


def _render_gauge(app, surface, rect, w, fg, bg, label, padding, border_on, use_device_font):
    """Render a gauge widget."""
    pct = app._value_ratio(w)

    b_inset = 1 if border_on else 0
    # For small gauges, put label below the arc instead of above
    compact = rect.height < GRID * 4
    if compact:
        label_h = 0
        bottom_reserve = (font6x8.CHAR_H + 1) if label else 0
    else:
        label_h = (font6x8.CHAR_H + 1) if label else 0
        bottom_reserve = 0
    # Check if compact layout is viable (enough room for arc + label)
    natural_gauge_h = rect.height - (b_inset + padding) * 2 - label_h - bottom_reserve
    use_arc = True
    if compact and bottom_reserve > 0 and natural_gauge_h < 5:
        # Too small for compact arc + label — use fallback bar
        use_arc = False
    gauge_area = pygame.Rect(
        rect.x + b_inset + padding + 1,
        rect.y + b_inset + padding + label_h,
        rect.width - (b_inset + padding + 1) * 2,
        max(8, natural_gauge_h),
    )
    cx = gauge_area.centerx
    cy = gauge_area.bottom - 1
    radius = min(gauge_area.width // 2, gauge_area.height) - 1
    if radius < 4:
        radius = 4
    if use_arc and radius >= 5:
        old_clip = surface.get_clip()
        semi_clip = pygame.Rect(rect.x, rect.y, rect.width, cy - rect.y + 1)
        surface.set_clip(semi_clip)
        try:
            arc_thick = max(2, radius // 4) if compact else max(3, radius // 3)
            end_deg = int(180 * pct)
            # Outer rim — 1px bright outline defining the arc shape
            rim_c = app._shade(bg, 30)
            for deg in range(181):
                a = math.radians(deg)
                px = cx + int((radius + 1) * math.cos(math.pi - a))
                py = cy - int((radius + 1) * math.sin(math.pi - a))
                if rect.left <= px < rect.right and rect.top <= py < rect.bottom and py <= cy:
                    surface.set_at((px, py), rim_c)
            # Inner rim — 1px darker line at arc inner edge
            inner_rim_c = app._shade(bg, 20)
            inner_r = radius - arc_thick
            for deg in range(181):
                a = math.radians(deg)
                px = cx + int(inner_r * math.cos(math.pi - a))
                py = cy - int(inner_r * math.sin(math.pi - a))
                if rect.left <= px < rect.right and rect.top <= py < rect.bottom and py <= cy:
                    surface.set_at((px, py), inner_rim_c)
            # Inactive arc — Bayer-dithered subtle texture
            hi_inactive = app._shade(bg, 32)
            lo_inactive = app._shade(bg, 18)
            for r_off in range(arc_thick):
                r_cur = radius - r_off
                if r_cur < 1:
                    break
                for deg in range(181):
                    a = math.radians(deg)
                    px = cx + int(r_cur * math.cos(math.pi - a))
                    py = cy - int(r_cur * math.sin(math.pi - a))
                    if rect.left <= px < rect.right and rect.top <= py < rect.bottom and py <= cy:
                        threshold = _BAYER4[py % 4][px % 4]
                        c = hi_inactive if threshold < 0.5 else lo_inactive
                        surface.set_at((px, py), c)
            # Active arc — bright radial gradient
            if end_deg > 0:
                for r_off in range(arc_thick):
                    r_cur = radius - r_off
                    if r_cur < 1:
                        break
                    r_ratio = 1.0 - r_off / max(1, arc_thick - 1)
                    hi = int(176 + 48 * r_ratio)
                    lo = int(112 + 48 * r_ratio)
                    hi_c = (hi, hi, hi)
                    lo_c = (lo, lo, lo)
                    for deg in range(end_deg + 1):
                        a = math.radians(deg)
                        px = cx + int(r_cur * math.cos(math.pi - a))
                        py = cy - int(r_cur * math.sin(math.pi - a))
                        if (
                            rect.left <= px < rect.right
                            and rect.top <= py < rect.bottom
                            and py <= cy
                        ):
                            threshold = _BAYER4[py % 4][px % 4]
                            c = hi_c if r_ratio > threshold else lo_c
                            surface.set_at((px, py), c)
                # Active arc outer edge highlight — bright 1px
                for deg in range(end_deg + 1):
                    a = math.radians(deg)
                    px = cx + int((radius + 1) * math.cos(math.pi - a))
                    py = cy - int((radius + 1) * math.sin(math.pi - a))
                    if rect.left <= px < rect.right and rect.top <= py < rect.bottom and py <= cy:
                        surface.set_at((px, py), (176, 176, 176))
            # Scale marks — small dots at outer rim at 0%, 25%, 50%, 75%, 100%
            for mark_pct in (0.0, 0.25, 0.5, 0.75, 1.0):
                mark_a = math.pi * (1.0 - mark_pct)
                mr = radius + 2
                mx = cx + int(mr * math.cos(mark_a))
                my = min(cy, cy - int(mr * math.sin(mark_a)))
                tick_c = (176, 176, 176) if mark_pct == 0.5 else (80, 80, 80)
                if rect.left <= mx < rect.right and rect.top <= my < rect.bottom and my <= cy:
                    surface.set_at((mx, my), tick_c)
            # Baseline — subtle line connecting arc endpoints
            base_c = app._shade(bg, 24)
            left_x = cx - radius - 1
            right_x = cx + radius + 1
            for bx in range(max(rect.left, left_x), min(rect.right, right_x + 1)):
                if rect.top <= cy < rect.bottom:
                    surface.set_at((bx, cy), base_c)
            # Needle
            needle_r = radius - arc_thick - 2
            if needle_r < 3:
                needle_r = 3
            needle_a = math.pi * (1.0 - pct)
            nx = cx + int(needle_r * math.cos(needle_a))
            ny = min(cy, cy - int(needle_r * math.sin(needle_a)))
            pygame.draw.line(surface, (208, 208, 208), (cx, cy), (nx, ny), 1)
            # Needle tip — bright dot
            if rect.left <= nx < rect.right and rect.top <= ny < rect.bottom and ny <= cy:
                surface.set_at((nx, ny), (240, 240, 240))
            # Hub dot
            surface.set_at((cx, cy), (224, 224, 224))
            if cx - 1 >= rect.left:
                surface.set_at((cx - 1, cy), (144, 144, 144))
            if cx + 1 < rect.right:
                surface.set_at((cx + 1, cy), (144, 144, 144))
            if cy - 1 >= rect.top:
                surface.set_at((cx, cy - 1), (144, 144, 144))
            # Value text centered inside arc (skip for compact)
            if not compact:
                val = int(getattr(w, "value", 0) or 0)
                val_str = str(val)
                if use_device_font:
                    txt_s = font6x8.render_text(val_str, fg)
                else:
                    txt_s = app.pixel_font.render(val_str, True, fg)
                tw = txt_s.get_width()
                th = txt_s.get_height()
                vx = cx - tw // 2
                vy = cy - needle_r * 2 // 5 - th // 2
                if vy >= rect.top + padding and vy + th <= rect.bottom - padding:
                    pad_x, pad_y = 1, 0
                    panel_r = pygame.Rect(vx - pad_x, vy - pad_y, tw + pad_x * 2, th + pad_y * 2)
                    pygame.draw.rect(surface, bg, panel_r)
                    surface.blit(txt_s, (vx, vy))
            # Label — at top for normal, below arc for compact
            if label:
                if compact:
                    # Restore clip before drawing label below the arc
                    surface.set_clip(old_clip)
                if use_device_font:
                    lbl_s = font6x8.render_text(label, fg)
                else:
                    lbl_s = app.pixel_font.render(label, True, fg)
                lx = rect.centerx - lbl_s.get_width() // 2
                ly = cy + 1 if compact else rect.y + b_inset + padding
                if ly + lbl_s.get_height() <= rect.bottom - b_inset:
                    surface.blit(lbl_s, (lx, ly))
        finally:
            surface.set_clip(old_clip)
    else:
        inner = rect.inflate(-2, -2)
        fill_w = int(inner.width * pct)
        fill_rect = pygame.Rect(inner.x, inner.y, fill_w, inner.height)
        pygame.draw.rect(surface, app._shade(fg, -40), fill_rect)


def _render_chart(app, surface, rect, w, fg, bg, label, style, padding, use_device_font):
    """Render a chart widget."""
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
    title_h = (font6x8.CHAR_H + 2) if label else 0
    chart_area = pygame.Rect(
        inner.x + 1, inner.y + title_h, inner.width - 2, max(1, inner.height - title_h - 1)
    )
    old_clip = surface.get_clip()
    surface.set_clip(inner)
    try:
        # Horizontal dotted grid with small Y-axis ticks
        grid_c = app._shade(bg, 20)
        tick_c = app._shade(bg, 30)
        for gi in range(1, 4):
            gy = chart_area.top + gi * chart_area.height // 4
            for gx in range(chart_area.left + 3, chart_area.right, 3):
                surface.set_at((gx, gy), grid_c)
            # Y-axis tick marks (2px wide)
            pygame.draw.line(surface, tick_c, (chart_area.left, gy), (chart_area.left + 1, gy), 1)
        # Vertical dotted grid with X-axis ticks
        v_divs = max(2, min(n, 6))
        for vi in range(1, v_divs):
            gx = chart_area.left + vi * chart_area.width // v_divs
            for gy in range(chart_area.top, chart_area.bottom - 2, 3):
                surface.set_at((gx, gy), grid_c)
            # X-axis tick marks
            pygame.draw.line(
                surface, tick_c, (gx, chart_area.bottom - 2), (gx, chart_area.bottom - 1), 1
            )
        # Axis lines (brighter than grid)
        axis_c = app._shade(bg, 40)
        pygame.draw.line(
            surface,
            axis_c,
            (chart_area.left, chart_area.top),
            (chart_area.left, chart_area.bottom - 1),
            1,
        )
        pygame.draw.line(
            surface,
            axis_c,
            (chart_area.left, chart_area.bottom - 1),
            (chart_area.right - 1, chart_area.bottom - 1),
            1,
        )
        # Thin top/right border for chart box feel
        border_dim = app._shade(bg, 12)
        pygame.draw.line(
            surface,
            border_dim,
            (chart_area.left, chart_area.top),
            (chart_area.right - 1, chart_area.top),
            1,
        )
        pygame.draw.line(
            surface,
            border_dim,
            (chart_area.right - 1, chart_area.top),
            (chart_area.right - 1, chart_area.bottom - 1),
            1,
        )

        if chart_mode == "bar":
            bar_w = max(2, (chart_area.width // n) - 1)
            peak_i = points.index(p_max)
            for i, v in enumerate(points):
                x = chart_area.left + 1 + i * (chart_area.width // n)
                h = max(1, int((v - p_min) / denom * max(1, chart_area.height - 2)))
                bar = pygame.Rect(x, chart_area.bottom - 1 - h, bar_w, h)
                ratio = (v - p_min) / denom
                # Bayer-dithered bar fill: hi_lum at top, lo_lum at bottom
                hi_v = min(255, int(96 + 144 * ratio))
                lo_v = int(32 + 48 * ratio)
                for row in range(bar.height):
                    cy = bar.top + row
                    row_ratio = row / max(1, bar.height - 1)
                    target = 1.0 - row_ratio  # 1.0 at top, 0.0 at bottom
                    for col in range(bar_w):
                        cx = bar.left + col
                        threshold = _BAYER4[cy % 4][cx % 4]
                        lum = hi_v if target > threshold else lo_v
                        surface.set_at((cx, cy), (lum, lum, lum))
                # Bright cap line
                cap_c = (240, 240, 240) if i == peak_i else (208, 208, 208)
                pygame.draw.line(surface, cap_c, (bar.left, bar.top), (bar.right - 1, bar.top), 1)
                # Subtle side highlights (left edge brighter)
                if bar.height > 4:
                    for row in range(1, min(bar.height - 1, bar.height)):
                        cy = bar.top + row
                        r0, *_ = surface.get_at((bar.left, cy))
                        bump = min(255, r0 + 16)
                        surface.set_at((bar.left, cy), (bump, bump, bump))
            # Peak indicator: small dot above peak bar
            if peak_i < len(points):
                px = chart_area.left + 1 + peak_i * (chart_area.width // n) + bar_w // 2
                ph = max(1, int((p_max - p_min) / denom * max(1, chart_area.height - 2)))
                py_peak = chart_area.bottom - 1 - ph - 3
                if py_peak >= chart_area.top:
                    surface.set_at((px, py_peak), (240, 240, 240))
                    if px > chart_area.left:
                        surface.set_at((px - 1, py_peak), (160, 160, 160))
                    if px < chart_area.right - 1:
                        surface.set_at((px + 1, py_peak), (160, 160, 160))
        else:
            coords: List[Tuple[int, int]] = []
            for i, v in enumerate(points):
                x = chart_area.left + 2 + int(i * (chart_area.width - 4) / max(1, n - 1))
                y = chart_area.bottom - 2 - int((v - p_min) / denom * max(1, chart_area.height - 4))
                coords.append((x, y))
            if len(coords) >= 2:
                base_y = chart_area.bottom - 2
                # Solid fill polygon as base
                fill_pts = [*coords, (coords[-1][0], base_y), (coords[0][0], base_y)]
                fill_c = app._shade(bg, 45)
                pygame.draw.polygon(surface, fill_c, fill_pts)
                # Bayer-dithered gradient overlay: bright near line → dark at base
                hi_lum = app._shade(bg, 90)
                lo_lum = app._shade(bg, 20)
                for ci in range(len(coords) - 1):
                    x1, y1 = coords[ci]
                    x2, y2 = coords[ci + 1]
                    steps = max(1, abs(x2 - x1))
                    for s in range(steps + 1):
                        t = s / max(1, steps)
                        px = int(x1 + t * (x2 - x1))
                        line_y = int(y1 + t * (y2 - y1))
                        col_h = base_y - line_y
                        if col_h < 2:
                            continue
                        for dy in range(col_h):
                            cy = line_y + dy
                            if cy < chart_area.top or cy > base_y:
                                continue
                            ratio_v = dy / max(1, col_h - 1)
                            target = 1.0 - ratio_v  # 1.0 near line, 0.0 at base
                            threshold = _BAYER4[cy % 4][px % 4]
                            if target > threshold:
                                surface.set_at((px, cy), hi_lum)
                            else:
                                surface.set_at((px, cy), lo_lum)
                # Glow band: 2px bright strip just below the line
                glow_c = app._shade(bg, 70)
                for ci in range(len(coords) - 1):
                    x1, y1 = coords[ci]
                    x2, y2 = coords[ci + 1]
                    steps = max(1, abs(x2 - x1))
                    for s in range(steps + 1):
                        t = s / max(1, steps)
                        px = int(x1 + t * (x2 - x1))
                        ly = int(y1 + t * (y2 - y1))
                        for go in range(1, 3):
                            gy = ly + go
                            if chart_area.top <= gy <= base_y:
                                surface.set_at((px, gy), glow_c)
                # Main data line — uniform 2px thick (manual raster)
                line_c = (240, 240, 240)
                for ci in range(len(coords) - 1):
                    x1, y1 = coords[ci]
                    x2, y2 = coords[ci + 1]
                    steps = max(1, abs(x2 - x1))
                    for s in range(steps + 1):
                        t = s / max(1, steps)
                        px = int(x1 + t * (x2 - x1))
                        py = int(y1 + t * (y2 - y1))
                        if chart_area.left <= px < chart_area.right:
                            if chart_area.top <= py < chart_area.bottom:
                                surface.set_at((px, py), line_c)
                            if chart_area.top <= py - 1 < chart_area.bottom:
                                surface.set_at((px, py - 1), line_c)
            # Find peak index for special marker
            peak_i = points.index(p_max)
            # Data point dots with halos + peak highlight
            for i, (x, y) in enumerate(coords):
                if i == peak_i:
                    # Peak: diamond marker
                    pygame.draw.circle(surface, app._shade(bg, 25), (x, y), 4)
                    for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
                        nx, ny = x + dx, y + dy
                        if (
                            chart_area.left <= nx < chart_area.right
                            and chart_area.top <= ny < chart_area.bottom
                        ):
                            surface.set_at((nx, ny), (240, 240, 240))
                    for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1), (0, 0)]:
                        nx, ny = x + dx, y + dy
                        if (
                            chart_area.left <= nx < chart_area.right
                            and chart_area.top <= ny < chart_area.bottom
                        ):
                            surface.set_at((nx, ny), (240, 240, 240))
                else:
                    # Normal dots: halo + bright center
                    pygame.draw.circle(surface, app._shade(bg, 25), (x, y), 3)
                    pygame.draw.circle(surface, (224, 224, 224), (x, y), 1)
        # Title label
        if label:
            if use_device_font:
                lbl_s = font6x8.render_text(label, (224, 224, 224))
            else:
                lbl_s = app.pixel_font.render(label, True, (224, 224, 224))
            surface.blit(lbl_s, (inner.x + 2, inner.y + 1))
    finally:
        surface.set_clip(old_clip)


def _render_list(app, surface, rect, w, fg, bg, label, padding, use_device_font):
    """Render a list widget."""
    inner = rect.inflate(-padding * 2, -padding * 2)
    items = (label or "").split("\n") if label else []
    row_h = (
        font6x8.CHAR_H
        if use_device_font
        else (app.pixel_font.get_height() if app.pixel_font else 8)
    )
    vis_rows = max(1, inner.height // max(1, row_h))
    active = int(getattr(w, "value", 0) or 0)
    scroll = int(getattr(w, "min_value", 0) or 0)
    total = len(items)
    if scroll < 0:
        scroll = 0
    if total > vis_rows and scroll > total - vis_rows:
        scroll = total - vis_rows
    if scroll < 0:
        scroll = 0
    if active < 0:
        active = 0
    if active >= total:
        active = max(0, total - 1)
    old_clip = surface.get_clip()
    surface.set_clip(inner)
    try:
        for row_i in range(vis_rows):
            idx = scroll + row_i
            if idx >= total:
                break
            row_y = inner.y + row_i * row_h
            txt = items[idx]
            if idx == active:
                pygame.draw.rect(surface, fg, pygame.Rect(inner.x, row_y, inner.width, row_h))
                if use_device_font:
                    ts = font6x8.render_text(txt, bg)
                else:
                    ts = app.pixel_font.render(txt, True, bg)
            else:
                if use_device_font:
                    ts = font6x8.render_text(txt, fg)
                else:
                    ts = app.pixel_font.render(txt, True, fg)
            surface.blit(ts, (inner.x + 1, row_y))
        if total > vis_rows:
            sb_x = inner.right - 2
            sb_h = inner.height
            thumb_h = max(2, sb_h * vis_rows // total)
            denom = max(1, total - vis_rows)
            thumb_y = inner.y + scroll * (sb_h - thumb_h) // denom
            pygame.draw.line(
                surface,
                app._shade(bg, 30),
                (sb_x, inner.y),
                (sb_x, inner.y + sb_h - 1),
            )
            pygame.draw.line(
                surface,
                app._shade(fg, -20),
                (sb_x, thumb_y),
                (sb_x, thumb_y + thumb_h - 1),
                2,
            )
    finally:
        surface.set_clip(old_clip)


def _render_icon(app, surface, rect, w, fg, label, padding, use_device_font):
    """Render an icon widget."""
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


def _render_radiobutton(app, surface, rect, w, fg, label, padding, use_device_font):
    """Render a radiobutton widget."""
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


def _render_box(surface, rect, bg):
    """Render a box widget."""
    pygame.draw.rect(surface, bg, rect)


def _render_label(app, surface, rect, w, fg, label, padding):
    """Render a label widget (default fallback)."""
    if label:
        draw_text_in_rect(app, surface, label, rect, fg, padding, w)
