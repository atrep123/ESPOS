"""Diagnostics helpers for UI Designer.

Separation from window.py reduces monolithic size and isolates
layout analysis logic for easier testing and future optimization.

Functions here must avoid any tkinter dependencies; operate purely
on model objects (scene, widgets).
"""
from __future__ import annotations

from typing import Dict, List, Tuple

# Type hints are kept loose to avoid tight coupling; widgets are expected
# to expose x, y, width, height attributes and scene.widgets is a list.

__all__ = ["layout_warnings"]


def layout_warnings(scene, display_width: int, display_height: int) -> List[str]:
    """Return list of layout warning strings for the given scene.

    Includes:
    - Non-positive sizes
    - Negative origins
    - Overflow past display bounds
    - Overlaps (O(n^2) for <=120 widgets, spatial grid for larger counts)
    - Edge proximity guidance (<2px from any edge)
    """
    if scene is None:
        return ["No active scene"]
    widgets = getattr(scene, "widgets", []) or []
    warnings: List[str] = []
    count = len(widgets)

    # Bounds checks (O(n))
    for idx, w in enumerate(widgets):
        try:
            x2 = w.x + w.width
            y2 = w.y + w.height
            if w.width <= 0 or w.height <= 0:
                warnings.append(f"Widget #{idx} has non-positive size ({w.width}x{w.height})")
            if w.x < 0 or w.y < 0:
                warnings.append(f"Widget #{idx} positioned with negative origin ({w.x},{w.y})")
            if x2 > display_width or y2 > display_height:
                warnings.append(
                    f"Widget #{idx} overflows display ({x2}>{display_width} or {y2}>{display_height})"
                )
        except Exception:
            warnings.append(f"Widget #{idx} missing required geometry attributes")

    # Overlap detection
    if count <= 120:
        for i in range(count):
            a = widgets[i]
            ax2 = a.x + a.width
            ay2 = a.y + a.height
            for j in range(i + 1, count):
                b = widgets[j]
                bx2 = b.x + b.width
                by2 = b.y + b.height
                overlap_w = min(ax2, bx2) - max(a.x, b.x)
                overlap_h = min(ay2, by2) - max(a.y, b.y)
                if overlap_w > 0 and overlap_h > 0:
                    area = overlap_w * overlap_h
                    if area > 0:
                        warnings.append(
                            f"Widgets #{i} and #{j} overlap ({overlap_w}x{overlap_h} = {area} px)"
                        )
    else:
        cell_size = max(8, int(min(display_width, display_height) / 20))
        cols = max(1, (display_width // cell_size) + 1)
        rows = max(1, (display_height // cell_size) + 1)
        grid: Dict[Tuple[int, int], List[int]] = {}
        for idx, w in enumerate(widgets):
            c0 = max(0, w.x // cell_size)
            c1 = max(0, (w.x + w.width) // cell_size)
            r0 = max(0, w.y // cell_size)
            r1 = max(0, (w.y + w.height) // cell_size)
            for cy in range(r0, r1 + 1):
                if cy >= rows:
                    break
                for cx in range(c0, c1 + 1):
                    if cx >= cols:
                        break
                    grid.setdefault((cx, cy), []).append(idx)
        seen_pairs = set()
        for cell_indices in grid.values():
            if len(cell_indices) < 2:
                continue
            for i_pos in range(len(cell_indices)):
                i = cell_indices[i_pos]
                a = widgets[i]
                ax2 = a.x + a.width
                ay2 = a.y + a.height
                for j_pos in range(i_pos + 1, len(cell_indices)):
                    j = cell_indices[j_pos]
                    if i == j:
                        continue
                    pair = (min(i, j), max(i, j))
                    if pair in seen_pairs:
                        continue
                    seen_pairs.add(pair)
                    b = widgets[j]
                    bx2 = b.x + b.width
                    by2 = b.y + b.height
                    overlap_w = min(ax2, bx2) - max(a.x, b.x)
                    overlap_h = min(ay2, by2) - max(a.y, b.y)
                    if overlap_w > 0 and overlap_h > 0:
                        area = overlap_w * overlap_h
                        if area > 0:
                            warnings.append(
                                f"Widgets #{pair[0]} and #{pair[1]} overlap ({overlap_w}x{overlap_h} = {area} px)"
                            )

    # Edge padding guidance
    pad_min = 2
    for idx, w in enumerate(widgets):
        try:
            if w.x < pad_min:
                warnings.append(f"Widget #{idx} very close to left edge (<{pad_min}px)")
            if w.y < pad_min:
                warnings.append(f"Widget #{idx} very close to top edge (<{pad_min}px)")
            if w.x + w.width > display_width - pad_min:
                warnings.append(f"Widget #{idx} very close to right edge (<{pad_min}px)")
            if w.y + w.height > display_height - pad_min:
                warnings.append(f"Widget #{idx} very close to bottom edge (<{pad_min}px)")
        except Exception:
            continue

    return warnings or ["No layout issues detected"]
