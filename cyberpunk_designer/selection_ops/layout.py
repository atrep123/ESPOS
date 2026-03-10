from __future__ import annotations

import math

import pygame

from ..constants import GRID, snap
from .core import selection_bounds


def arrange_in_row(app) -> None:
    """Arrange selected widgets in a horizontal row with GRID spacing."""
    if len(app.state.selected) < 2:
        app._set_status("Arrange row: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    try:
        app.designer._save_state()
    except Exception:
        pass
    indices = sorted(app.state.selected)
    widgets = [(i, sc.widgets[i]) for i in indices if 0 <= i < len(sc.widgets)]
    if not widgets:
        return
    # Start from the first widget's position
    start_x = int(getattr(widgets[0][1], "x", 0) or 0)
    start_y = int(getattr(widgets[0][1], "y", 0) or 0)
    cursor_x = start_x
    for _idx, w in widgets:
        w.x = max(0, min(int(sc.width) - max(GRID, int(w.width or GRID)), cursor_x))
        w.y = start_y
        cursor_x += max(GRID, int(w.width or GRID)) + GRID
    app._set_status(f"Arranged {len(widgets)} widgets in row.", ttl_sec=1.5)
    app._mark_dirty()


def arrange_in_column(app) -> None:
    """Arrange selected widgets in a vertical column with GRID spacing."""
    if len(app.state.selected) < 2:
        app._set_status("Arrange column: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    try:
        app.designer._save_state()
    except Exception:
        pass
    indices = sorted(app.state.selected)
    widgets = [(i, sc.widgets[i]) for i in indices if 0 <= i < len(sc.widgets)]
    if not widgets:
        return
    start_x = int(getattr(widgets[0][1], "x", 0) or 0)
    start_y = int(getattr(widgets[0][1], "y", 0) or 0)
    cursor_y = start_y
    for _idx, w in widgets:
        w.x = start_x
        w.y = max(0, min(int(sc.height) - max(GRID, int(w.height or GRID)), cursor_y))
        cursor_y += max(GRID, int(w.height or GRID)) + GRID
    app._set_status(f"Arranged {len(widgets)} widgets in column.", ttl_sec=1.5)
    app._mark_dirty()


def compact_widgets(app) -> None:
    """Move all widgets so the bounding box starts at (0,0) and remove gaps."""
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("No widgets to compact.", ttl_sec=2.0)
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    min_x = min(int(w.x) for w in sc.widgets)
    min_y = min(int(w.y) for w in sc.widgets)
    if min_x == 0 and min_y == 0:
        app._set_status("Already compact (origin at 0,0).", ttl_sec=2.0)
        return
    for w in sc.widgets:
        w.x = int(w.x) - min_x
        w.y = int(w.y) - min_y
    app._set_status(f"Compacted: shifted by ({-min_x},{-min_y}).", ttl_sec=2.0)
    app._mark_dirty()


def stack_vertical(app) -> None:
    """Stack selected widgets vertically with GRID gap, starting from topmost."""
    if len(app.state.selected) < 2:
        app._set_status("Stack V: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    valid = [i for i in app.state.selected if 0 <= i < len(sc.widgets)]
    if len(valid) < 2:
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    # Sort by current y position
    valid.sort(key=lambda i: (int(sc.widgets[i].y), int(sc.widgets[i].x)))
    first = sc.widgets[valid[0]]
    cur_y = int(first.y)
    base_x = int(first.x)
    for i in valid:
        w = sc.widgets[i]
        w.x = base_x
        w.y = cur_y
        cur_y += int(w.height) + GRID
    app._set_status(f"Stacked {len(valid)} widgets vertically.", ttl_sec=2.0)
    app._mark_dirty()


def stack_horizontal(app) -> None:
    """Stack selected widgets horizontally with GRID gap, starting from leftmost."""
    if len(app.state.selected) < 2:
        app._set_status("Stack H: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    valid = [i for i in app.state.selected if 0 <= i < len(sc.widgets)]
    if len(valid) < 2:
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    # Sort by current x position
    valid.sort(key=lambda i: (int(sc.widgets[i].x), int(sc.widgets[i].y)))
    first = sc.widgets[valid[0]]
    cur_x = int(first.x)
    base_y = int(first.y)
    for i in valid:
        w = sc.widgets[i]
        w.y = base_y
        w.x = cur_x
        cur_x += int(w.width) + GRID
    app._set_status(f"Stacked {len(valid)} widgets horizontally.", ttl_sec=2.0)
    app._mark_dirty()


def equalize_widths(app) -> None:
    """Set all selected widgets to the same width as the widest one."""
    if len(app.state.selected) < 2:
        app._set_status("Equalize W: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    valid = [i for i in app.state.selected if 0 <= i < len(sc.widgets)]
    if len(valid) < 2:
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    max_w = max(int(sc.widgets[i].width) for i in valid)
    changed = 0
    for i in valid:
        w = sc.widgets[i]
        if int(w.width) != max_w:
            w.width = max_w
            changed += 1
    app._set_status(f"Equalized {changed} widgets to width={max_w}.", ttl_sec=2.0)
    app._mark_dirty()


def equalize_heights(app) -> None:
    """Set all selected widgets to the same height as the tallest one."""
    if len(app.state.selected) < 2:
        app._set_status("Equalize H: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    valid = [i for i in app.state.selected if 0 <= i < len(sc.widgets)]
    if len(valid) < 2:
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    max_h = max(int(sc.widgets[i].height) for i in valid)
    changed = 0
    for i in valid:
        w = sc.widgets[i]
        if int(w.height) != max_h:
            w.height = max_h
            changed += 1
    app._set_status(f"Equalized {changed} widgets to height={max_h}.", ttl_sec=2.0)
    app._mark_dirty()


def equalize_gaps(app, axis: str = "auto") -> None:
    """Set uniform GRID-sized gaps between selected widgets.

    Unlike distribute (which preserves endpoints), this re-spaces
    widgets from the first widget's position with GRID gaps.
    axis: 'h', 'v', or 'auto' (detect dominant axis).
    """
    if len(app.state.selected) < 2:
        app._set_status("Equal gaps: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    valid = [i for i in app.state.selected if 0 <= i < len(sc.widgets)]
    if len(valid) < 2:
        return
    # Auto-detect axis
    if axis == "auto":
        xs = [int(sc.widgets[i].x) for i in valid]
        ys = [int(sc.widgets[i].y) for i in valid]
        spread_x = max(xs) - min(xs)
        spread_y = max(ys) - min(ys)
        axis = "h" if spread_x >= spread_y else "v"
    try:
        app.designer._save_state()
    except Exception:
        pass
    if axis == "h":
        ordered = sorted(valid, key=lambda i: int(sc.widgets[i].x))
        cursor = int(sc.widgets[ordered[0]].x)
        for i in ordered:
            w = sc.widgets[i]
            w.x = cursor
            cursor += int(w.width or GRID) + GRID
    else:
        ordered = sorted(valid, key=lambda i: int(sc.widgets[i].y))
        cursor = int(sc.widgets[ordered[0]].y)
        for i in ordered:
            w = sc.widgets[i]
            w.y = cursor
            cursor += int(w.height or GRID) + GRID
    label = "horizontally" if axis == "h" else "vertically"
    app._set_status(f"Equalized gaps {label} ({len(valid)} widgets).", ttl_sec=2.0)
    app._mark_dirty()


def grid_arrange(app) -> None:
    """Arrange selected widgets in an auto-calculated grid layout."""
    if len(app.state.selected) < 2:
        app._set_status("Grid: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    valid = [i for i in app.state.selected if 0 <= i < len(sc.widgets)]
    if len(valid) < 2:
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    n = len(valid)
    cols = max(1, math.ceil(math.sqrt(n)))
    # Use first widget position as origin; uniform cell = max sizes + GRID gap
    max_w = max(int(sc.widgets[i].width or GRID) for i in valid)
    max_h = max(int(sc.widgets[i].height or GRID) for i in valid)
    cell_w = max_w + GRID
    cell_h = max_h + GRID
    origin_x = min(int(sc.widgets[i].x) for i in valid)
    origin_y = min(int(sc.widgets[i].y) for i in valid)
    for idx_pos, i in enumerate(valid):
        col = idx_pos % cols
        row = idx_pos // cols
        sc.widgets[i].x = origin_x + col * cell_w
        sc.widgets[i].y = origin_y + row * cell_h
    rows = (n + cols - 1) // cols
    app._set_status(f"Grid {cols}x{rows} ({n} widgets).", ttl_sec=2.0)
    app._mark_dirty()


def auto_flow_layout(app) -> None:
    """Arrange selected widgets in a wrapping left-to-right flow.

    Widgets are placed in reading order (left-to-right, wrapping to next row
    when the scene width would be exceeded), with GRID-sized gaps.
    """
    if len(app.state.selected) < 2:
        app._set_status("Flow layout: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    scene_w = int(getattr(sc, "width", 256) or 256)
    widgets = []
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            widgets.append((idx, sc.widgets[idx]))
    if len(widgets) < 2:
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    gap = GRID
    cx, cy = 0, 0
    row_h = 0
    for _idx, w in widgets:
        ww = int(getattr(w, "width", GRID) or GRID)
        wh = int(getattr(w, "height", GRID) or GRID)
        if cx > 0 and cx + ww > scene_w:
            cx = 0
            cy += row_h + gap
            row_h = 0
        w.x = snap(cx)
        w.y = snap(cy)
        cx += ww + gap
        if wh > row_h:
            row_h = wh
    app._set_status(f"Flow layout → {len(widgets)} widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def space_evenly_h(app) -> None:
    """Space selected widgets evenly horizontally (equal center-to-center)."""
    if len(app.state.selected) < 3:
        app._set_status("Space H: select 3+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    items = []
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            w = sc.widgets[idx]
            cx = w.x + int(getattr(w, "width", 0) or 0) // 2
            items.append((cx, idx, w))
    if len(items) < 3:
        return
    items.sort(key=lambda t: t[0])
    try:
        app.designer._save_state()
    except Exception:
        pass
    first_cx = items[0][0]
    last_cx = items[-1][0]
    step = (last_cx - first_cx) / (len(items) - 1)
    for i, (_cx, _idx, w) in enumerate(items):
        ww = int(getattr(w, "width", 0) or 0)
        new_cx = first_cx + round(step * i)
        w.x = snap(new_cx - ww // 2)
    app._set_status(f"Spaced {len(items)} horizontally.", ttl_sec=2.0)
    app._mark_dirty()


def space_evenly_v(app) -> None:
    """Space selected widgets evenly vertically (equal center-to-center)."""
    if len(app.state.selected) < 3:
        app._set_status("Space V: select 3+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    items = []
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            w = sc.widgets[idx]
            cy = w.y + int(getattr(w, "height", 0) or 0) // 2
            items.append((cy, idx, w))
    if len(items) < 3:
        return
    items.sort(key=lambda t: t[0])
    try:
        app.designer._save_state()
    except Exception:
        pass
    first_cy = items[0][0]
    last_cy = items[-1][0]
    step = (last_cy - first_cy) / (len(items) - 1)
    for i, (_cy, _idx, w) in enumerate(items):
        wh = int(getattr(w, "height", 0) or 0)
        new_cy = first_cy + round(step * i)
        w.y = snap(new_cy - wh // 2)
    app._set_status(f"Spaced {len(items)} vertically.", ttl_sec=2.0)
    app._mark_dirty()


def shrink_to_content(app) -> None:
    """Shrink a panel widget to tightly fit its enclosed children."""
    if not app.state.selected:
        app._set_status("Shrink: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    app._save_undo_state()
    count = 0
    pad = GRID // 2
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        if str(getattr(w, "type", "")) != "panel":
            continue
        # Find children that are geometrically inside this panel
        px, py = int(w.x), int(w.y)
        pw, ph = int(w.width), int(w.height)
        panel_rect = pygame.Rect(px, py, pw, ph)
        children_rects = []
        for ci, cw in enumerate(sc.widgets):
            if ci == idx:
                continue
            cx, cy = int(cw.x), int(cw.y)
            cw2, ch2 = int(getattr(cw, "width", 0) or 0), int(getattr(cw, "height", 0) or 0)
            child_rect = pygame.Rect(cx, cy, max(1, cw2), max(1, ch2))
            if panel_rect.contains(child_rect):
                children_rects.append(child_rect)
        if not children_rects:
            continue
        min_x = min(r.x for r in children_rects)
        min_y = min(r.y for r in children_rects)
        max_x = max(r.right for r in children_rects)
        max_y = max(r.bottom for r in children_rects)
        w.x = min_x - pad
        w.y = min_y - pad
        w.width = (max_x - min_x) + pad * 2
        w.height = (max_y - min_y) + pad * 2
        count += 1
    if count:
        app._set_status(f"Shrunk {count} panel(s) to content.", ttl_sec=2.0)
    else:
        app._set_status("Shrink: no panels with children found.", ttl_sec=2.0)
    app._mark_dirty()


def distribute_columns(app, col_count: int = 2) -> None:
    """Arrange selected widgets into N equal-width columns, preserving order."""
    if len(app.state.selected) < 2:
        app._set_status("Distribute cols: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    bounds = selection_bounds(app, app.state.selected)
    if bounds is None:
        return
    app._save_undo_state()
    indices = sorted(app.state.selected)
    col_w = bounds.width // col_count
    row_h = 0
    # Measure tallest widget for row height
    for idx in indices:
        if 0 <= idx < len(sc.widgets):
            h = int(getattr(sc.widgets[idx], "height", GRID) or GRID)
            if h > row_h:
                row_h = h
    row_h = max(row_h, GRID)
    gap = GRID
    for i, idx in enumerate(indices):
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        col = i % col_count
        row = i // col_count
        w.x = bounds.x + col * (col_w + gap)
        w.y = bounds.y + row * (row_h + gap)
        w.width = col_w
    app._set_status(f"Distributed {len(indices)} widgets into {col_count} columns.", ttl_sec=2.0)
    app._mark_dirty()


def distribute_rows(app, row_count: int = 2) -> None:
    """Arrange selected widgets into N equal-height rows, preserving order."""
    if len(app.state.selected) < 2:
        app._set_status("Distribute rows: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    bounds = selection_bounds(app, app.state.selected)
    if bounds is None:
        return
    app._save_undo_state()
    indices = sorted(app.state.selected)
    row_h = bounds.height // row_count
    col_w = 0
    for idx in indices:
        if 0 <= idx < len(sc.widgets):
            w = int(getattr(sc.widgets[idx], "width", GRID) or GRID)
            if w > col_w:
                col_w = w
    col_w = max(col_w, GRID)
    gap = GRID
    cols_per_row = max(1, len(indices) // row_count + (1 if len(indices) % row_count else 0))
    for i, idx in enumerate(indices):
        if not (0 <= idx < len(sc.widgets)):
            continue
        wgt = sc.widgets[idx]
        row = i // cols_per_row
        col = i % cols_per_row
        wgt.x = bounds.x + col * (col_w + gap)
        wgt.y = bounds.y + row * (row_h + gap)
        wgt.height = row_h
    app._set_status(f"Distributed {len(indices)} widgets into {row_count} rows.", ttl_sec=2.0)
    app._mark_dirty()


def pack_left(app) -> None:
    """Pack selected widgets left-to-right with touching edges, preserving Y."""
    if len(app.state.selected) < 2:
        app._set_status("Pack left: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    app._save_undo_state()
    indices = sorted(app.state.selected, key=lambda i: sc.widgets[i].x)
    x = int(sc.widgets[indices[0]].x)
    for idx in indices:
        w = sc.widgets[idx]
        w.x = x
        x += int(getattr(w, "width", GRID) or GRID)
    app._set_status(f"Packed {len(indices)} widgets left.", ttl_sec=2.0)
    app._mark_dirty()


def pack_top(app) -> None:
    """Pack selected widgets top-to-bottom with touching edges, preserving X."""
    if len(app.state.selected) < 2:
        app._set_status("Pack top: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    app._save_undo_state()
    indices = sorted(app.state.selected, key=lambda i: sc.widgets[i].y)
    y = int(sc.widgets[indices[0]].y)
    for idx in indices:
        w = sc.widgets[idx]
        w.y = y
        y += int(getattr(w, "height", GRID) or GRID)
    app._set_status(f"Packed {len(indices)} widgets top.", ttl_sec=2.0)
    app._mark_dirty()


def cascade_arrange(app) -> None:
    """Arrange selected widgets in a diagonal staircase pattern (+8,+8 each)."""
    if len(app.state.selected) < 2:
        app._set_status("Cascade: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    app._save_undo_state()
    indices = sorted(app.state.selected)
    base_x = int(sc.widgets[indices[0]].x)
    base_y = int(sc.widgets[indices[0]].y)
    step = GRID
    for n, idx in enumerate(indices):
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].x = base_x + n * step
            sc.widgets[idx].y = base_y + n * step
    app._set_status(f"Cascaded {len(indices)} widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def distribute_columns_3(app) -> None:
    """Arrange selected widgets into 3 equal-width columns."""
    distribute_columns(app, col_count=3)
