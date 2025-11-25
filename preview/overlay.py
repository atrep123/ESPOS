"""Overlay drawing utilities for Designer preview.

Separated from window.py to reduce monolith size and allow focused
performance tuning.

All functions are pure w.r.t. inputs; they only mutate the passed canvas.
"""
from __future__ import annotations

from typing import Callable, Optional, Sequence

__all__ = ["draw_perf_overlay", "draw_diagnostics_overlay"]


def draw_perf_overlay(
    canvas,
    ms: float,
    budget: float,
    warn: float,
    scale_spacing: Callable[[int], int],
    scale_font_size: Callable[[int], int],
    color_hex: Callable[[str], str],
    tag: str = "perf_overlay",
) -> None:
    """Draw compact performance HUD.

    Existing shapes for tag are cleared before drawing.
    """
    try:
        canvas.delete(tag)
    except Exception:
        pass
    try:
        w = scale_spacing(160)
        h = scale_spacing(48)
        pad = scale_spacing(8)
        x0 = scale_spacing(12)
        y0 = scale_spacing(12)
        x1 = x0 + w
        y1 = y0 + h
        canvas.create_rectangle(
            x0,
            y0,
            x1,
            y1,
            fill=color_hex("shadow"),
            outline=color_hex("legacy_gray8"),
            stipple="gray25",
            tags=(tag,),
        )
        # Bar
        bar_width = w - 2 * pad
        bar_height = scale_spacing(12)
        bx0 = x0 + pad
        by0 = y0 + pad
        bx1 = bx0 + bar_width
        by1 = by0 + bar_height
        canvas.create_rectangle(bx0, by0, bx1, by1, outline=color_hex("legacy_gray8"), tags=(tag,))
        if bar_width > 0:
            frac = min(1.5, ms / max(1e-6, budget))
            fill_w = max(1, int(bar_width * frac / 1.5))
            if ms > warn:
                fill_color = color_hex("legacy_dracula_red")
            elif ms > budget:
                fill_color = color_hex("legacy_orange")
            else:
                fill_color = color_hex("legacy_green")
            canvas.create_rectangle(
                bx0,
                by0,
                bx0 + fill_w,
                by1,
                fill=fill_color,
                outline="",
                tags=(tag,),
            )
        txt = f"{ms:.1f} ms (budget {budget:.1f} / warn {warn:.1f})"
        canvas.create_text(
            x0 + pad,
            by1 + pad,
            anchor="nw",
            text=txt,
            fill=color_hex("text_primary"),
            font=("TkDefaultFont", scale_font_size(9)),
            tags=(tag,),
        )
    except Exception:
        pass


def draw_diagnostics_overlay(
    canvas,
    widgets: Sequence,
    zoom: float,
    selected_index: Optional[int],
    fps_history: Sequence[float],
    display_height: int,
    scale_font_size: Callable[[int], int],
    color_hex: Callable[[str], str],
    tag: str = "diag_overlay",
) -> None:
    """Draw bounding boxes for widgets and FPS sparkline.

    Clears previous tagged shapes first.
    """
    try:
        canvas.delete(tag)
    except Exception:
        pass
    # Bounding boxes
    try:
        for idx, w in enumerate(widgets):
            x1 = int(w.x * zoom)
            y1 = int(w.y * zoom)
            x2 = int((w.x + w.width) * zoom)
            y2 = int((w.y + w.height) * zoom)
            canvas.create_rectangle(
                x1,
                y1,
                x2,
                y2,
                outline=color_hex("legacy_dracula_cyan"),
                width=1,
                tags=(tag,),
            )
            if idx == selected_index:
                canvas.create_rectangle(
                    x1,
                    y1,
                    x2,
                    y2,
                    outline=color_hex("legacy_green"),
                    width=2,
                    tags=(tag,),
                )
    except Exception:
        pass
    # FPS sparkline
    try:
        if fps_history:
            spark_w = 100
            spark_h = 28
            pad = 4
            x0 = 10
            y0 = int(display_height * zoom) - spark_h - 10
            canvas.create_rectangle(
                x0,
                y0,
                x0 + spark_w,
                y0 + spark_h,
                fill=color_hex("shadow"),
                outline=color_hex("legacy_gray8"),
                tags=(tag,),
            )
            max_fps = max(fps_history)
            min_fps = min(fps_history)
            span = max(1.0, max_fps - min_fps)
            pts = []
            hist = fps_history[-spark_w:]
            for i, v in enumerate(hist):
                norm = (v - min_fps) / span
                px = x0 + pad + i
                py = (y0 + spark_h - pad) - int(norm * (spark_h - 2 * pad))
                pts.append((px, py))
            for a, b in zip(pts, pts[1:]):
                canvas.create_line(a[0], a[1], b[0], b[1], fill=color_hex("legacy_dracula_pink"), tags=(tag,))
            try:
                inst = fps_history[-1]
                canvas.create_text(
                    x0 + spark_w // 2,
                    y0 - 2,
                    text=f"FPS {inst:.1f}",
                    fill=color_hex("text_primary"),
                    font=("TkDefaultFont", scale_font_size(9)),
                    tags=(tag,),
                )
            except Exception:
                pass
    except Exception:
        pass
