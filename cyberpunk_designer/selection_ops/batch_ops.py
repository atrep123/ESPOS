"""Batch widget operations: reorder, reset, duplicate, sort."""

from __future__ import annotations

from dataclasses import asdict
from typing import List

from ui_designer import WidgetConfig

from ..constants import GRID
from .core import save_undo


def reorder_selection(app, direction: int) -> None:
    """Move selected widgets up (-1) or down (+1) in the widget list.

    This affects tab/focus order and z-order rendering.
    """
    if not app.state.selected:
        app._set_status("Reorder: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    n = len(sc.widgets)
    if n < 2:
        return
    indices = sorted(app.state.selected)
    # Check boundaries
    if direction < 0 and indices[0] <= 0:
        return
    if direction > 0 and indices[-1] >= n - 1:
        return
    save_undo(app)
    # Swap one-by-one in the correct order to avoid conflicts
    new_indices = []
    if direction < 0:
        for idx in indices:
            sc.widgets[idx - 1], sc.widgets[idx] = sc.widgets[idx], sc.widgets[idx - 1]
            new_indices.append(idx - 1)
    else:
        for idx in reversed(indices):
            sc.widgets[idx + 1], sc.widgets[idx] = sc.widgets[idx], sc.widgets[idx + 1]
            new_indices.append(idx + 1)
        new_indices.reverse()
    app.state.selected = new_indices
    app.state.selected_idx = new_indices[0] if new_indices else None
    app.designer.selected_widget = app.state.selected_idx
    label = "up" if direction < 0 else "down"
    app._set_status(f"Reorder: moved {label}.", ttl_sec=1.5)
    app._mark_dirty()


def reset_to_defaults(app) -> None:
    """Reset selected widgets to type defaults, keeping position/size/type/text."""
    if not app.state.selected:
        app._set_status("Reset: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    items = [(i, sc.widgets[i]) for i in app.state.selected if 0 <= i < len(sc.widgets)]
    if not items:
        return
    if any(getattr(w, "locked", False) for _, w in items):
        app._set_status("Some widgets are locked.", ttl_sec=2.0)
        return
    save_undo(app)
    keep_fields = {"type", "x", "y", "width", "height", "text", "runtime", "locked"}
    count = 0
    for _idx, w in items:
        ref = WidgetConfig(type=w.type, x=w.x, y=w.y, width=w.width, height=w.height)
        for attr in (
            "style",
            "color_fg",
            "color_bg",
            "border",
            "border_style",
            "align",
            "valign",
            "text_overflow",
            "max_lines",
            "value",
            "min_value",
            "max_value",
            "checked",
            "enabled",
            "visible",
            "icon_char",
            "data_points",
            "z_index",
            "padding_x",
            "padding_y",
            "margin_x",
            "margin_y",
        ):
            if attr not in keep_fields:
                setattr(w, attr, getattr(ref, attr))
        count += 1
    app._set_status(f"Reset {count} widget(s) to defaults.", ttl_sec=2.0)
    app._mark_dirty()


def array_duplicate(app, count: int, dx: int, dy: int) -> None:
    """Duplicate selection N times, each offset by (dx, dy) from the previous."""
    if not app.state.selected:
        app._set_status("Array dup: nothing selected.", ttl_sec=2.0)
        return
    if count < 1 or count > 50:
        app._set_status("Count must be 1..50.", ttl_sec=3.0)
        return
    sc = app.state.current_scene()
    save_undo(app)
    base_widgets = []
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            base_widgets.append(sc.widgets[idx])
    if not base_widgets:
        return
    new_indices: List[int] = []
    for step in range(1, count + 1):
        for bw in base_widgets:
            try:
                nw = WidgetConfig(**asdict(bw))
            except (TypeError, ValueError):
                continue
            nw.x = max(0, min(int(sc.width) - max(1, int(nw.width)), int(nw.x) + dx * step))
            nw.y = max(0, min(int(sc.height) - max(1, int(nw.height)), int(nw.y) + dy * step))
            sc.widgets.append(nw)
            new_indices.append(len(sc.widgets) - 1)
    if new_indices:
        app._set_selection(new_indices, anchor_idx=new_indices[0])
    total = len(new_indices)
    app._set_status(f"Array duplicated: {total} widget(s) ({count}x).", ttl_sec=2.0)
    app._mark_dirty()


def remove_degenerate_widgets(app) -> None:
    """Remove widgets with zero or negative width/height."""
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("No widgets in scene.", ttl_sec=2.0)
        return
    degenerate = [i for i, w in enumerate(sc.widgets) if int(w.width) <= 0 or int(w.height) <= 0]
    if not degenerate:
        app._set_status("No degenerate widgets found.", ttl_sec=2.0)
        return
    save_undo(app)
    count = len(degenerate)
    for i in reversed(degenerate):
        sc.widgets.pop(i)
    app.state.selected = []
    app.state.selected_idx = None
    app.designer.selected_widget = None
    app._set_status(f"Removed {count} degenerate widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def sort_widgets_by_position(app) -> None:
    """Sort widgets by position: top-to-bottom, then left-to-right."""
    sc = app.state.current_scene()
    if len(sc.widgets) < 2:
        app._set_status("Nothing to sort.", ttl_sec=2.0)
        return
    save_undo(app)
    sc.widgets.sort(key=lambda w: (int(w.y), int(w.x)))
    app.state.selected = []
    app.state.selected_idx = None
    app.designer.selected_widget = None
    app._set_status(f"Sorted {len(sc.widgets)} widgets by position.", ttl_sec=2.0)
    app._mark_dirty()


def flatten_z_indices(app) -> None:
    """Reassign z_index 0,1,2,... based on current visual sort order."""
    sc = app.state.current_scene()
    if len(sc.widgets) < 2:
        app._set_status("Nothing to flatten.", ttl_sec=2.0)
        return
    save_undo(app)
    ordered = sorted(
        enumerate(sc.widgets),
        key=lambda t: (int(getattr(t[1], "z_index", 0) or 0), t[0]),
    )
    changed = 0
    for new_z, (_, w) in enumerate(ordered):
        old_z = int(getattr(w, "z_index", 0) or 0)
        if old_z != new_z:
            w.z_index = new_z
            changed += 1
    app._set_status(
        f"Flattened z-indices: {changed}/{len(sc.widgets)} updated (0..{len(sc.widgets) - 1}).",
        ttl_sec=2.0,
    )
    app._mark_dirty()


def reverse_widget_order(app) -> None:
    """Reverse the order of selected widgets in the widget list."""
    if len(app.state.selected) < 2:
        app._set_status("Reverse: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    valid = sorted([i for i in app.state.selected if 0 <= i < len(sc.widgets)])
    if len(valid) < 2:
        return
    save_undo(app)
    # Collect widgets at the indices, reverse, put back
    widgets_copy = [sc.widgets[i] for i in valid]
    widgets_copy.reverse()
    for pos, i in enumerate(valid):
        sc.widgets[i] = widgets_copy[pos]
    app._set_status(f"Reversed order of {len(valid)} widgets.", ttl_sec=2.0)
    app._mark_dirty()


def normalize_sizes(app) -> None:
    """Set all selected widgets to average width and height."""
    if len(app.state.selected) < 2:
        app._set_status("Normalize: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    valid = [i for i in app.state.selected if 0 <= i < len(sc.widgets)]
    if len(valid) < 2:
        return
    save_undo(app)
    avg_w = sum(int(sc.widgets[i].width or GRID) for i in valid) // len(valid)
    avg_h = sum(int(sc.widgets[i].height or GRID) for i in valid) // len(valid)
    avg_w = max(GRID, avg_w)
    avg_h = max(GRID, avg_h)
    changed = 0
    for i in valid:
        w = sc.widgets[i]
        if int(w.width or 0) != avg_w or int(w.height or 0) != avg_h:
            w.width = avg_w
            w.height = avg_h
            changed += 1
    app._set_status(f"Normalized {changed} to {avg_w}x{avg_h}.", ttl_sec=2.0)
    app._mark_dirty()


def remove_duplicates(app) -> None:
    """Remove widgets with identical position, size, and type (keep first)."""
    sc = app.state.current_scene()
    if len(sc.widgets) < 2:
        app._set_status("No duplicates possible.", ttl_sec=2.0)
        return
    save_undo(app)
    seen = set()
    keep = []
    removed = 0
    for w in sc.widgets:
        key = (
            str(getattr(w, "type", "")),
            int(w.x),
            int(w.y),
            int(w.width or 0),
            int(w.height or 0),
        )
        if key in seen:
            removed += 1
        else:
            seen.add(key)
            keep.append(w)
    sc.widgets[:] = keep
    app.state.selected = []
    app._set_status(f"Removed {removed} duplicate(s).", ttl_sec=2.0)
    app._mark_dirty()


def flatten_z_index(app) -> None:
    """Reset z_index to 0 for all widgets in the scene."""
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("No widgets.", ttl_sec=2.0)
        return
    app._save_undo_state()
    count = 0
    for w in sc.widgets:
        if int(getattr(w, "z_index", 0) or 0) != 0:
            w.z_index = 0
            count += 1
    if count:
        app._set_status(f"Flattened z-index on {count} widget(s).", ttl_sec=2.0)
    else:
        app._set_status("All z-index already 0.", ttl_sec=2.0)
    app._mark_dirty()


def z_by_position(app) -> None:
    """Set z_index on all widgets by top-to-bottom, left-to-right order."""
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("No widgets.", ttl_sec=2.0)
        return
    app._save_undo_state()
    order = sorted(
        range(len(sc.widgets)),
        key=lambda i: (sc.widgets[i].y, sc.widgets[i].x),
    )
    for z, idx in enumerate(order):
        sc.widgets[idx].z_index = z
    app._set_status(f"Set z-index by position on {len(sc.widgets)} widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def sort_widgets_by_z(app) -> None:
    """Reorder the widget list by z_index so rendering order matches z-order."""
    sc = app.state.current_scene()
    if len(sc.widgets) < 2:
        app._set_status("Need 2+ widgets to sort.", ttl_sec=2.0)
        return
    app._save_undo_state()
    sc.widgets.sort(key=lambda w: int(getattr(w, "z_index", 0) or 0))
    app.state.selected = []
    app._set_status(f"Sorted {len(sc.widgets)} widget(s) by z-index.", ttl_sec=2.0)
    app._mark_dirty()
