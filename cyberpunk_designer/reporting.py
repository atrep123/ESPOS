"""Design report generation and analysis."""

from __future__ import annotations

import time
from pathlib import Path

import pygame

from .constants import PALETTE


def screenshot_canvas(app) -> None:
    """Save a screenshot of the canvas area."""
    try:
        sc = app.state.current_scene()
        report_dir = Path("reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        out_path = report_dir / f"{ts}_canvas.png"

        canvas = pygame.Surface((int(sc.width), int(sc.height)))
        canvas.fill(PALETTE.get("canvas_bg", PALETTE["bg"]))

        items = list(enumerate(sc.widgets))
        items.sort(key=lambda t: int(getattr(t[1], "z_index", 0) or 0))
        pad = max(2, app.pixel_padding // 2)
        for _idx, w in items:
            if not getattr(w, "visible", True):
                continue
            ww = max(1, int(getattr(w, "width", 1) or 1))
            wh = max(1, int(getattr(w, "height", 1) or 1))
            rect = pygame.Rect(int(w.x), int(w.y), ww, wh)
            app._draw_widget_preview(
                surface=canvas,
                w=w,
                rect=rect,
                base_bg=PALETTE.get("canvas_bg", PALETTE["bg"]),
                padding=pad,
                is_selected=False,
            )

        pygame.image.save(canvas, str(out_path))
        app._set_status(f"Saved screenshot: {out_path}", ttl_sec=5.0)
    except (OSError, pygame.error) as exc:
        app._set_status(f"Screenshot failed: {exc}", ttl_sec=5.0)
