from __future__ import annotations

import copy
import random
import re
from collections import Counter
from dataclasses import asdict
from typing import List

from ui_designer import WidgetConfig

from ..constants import GRID, snap


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
    try:
        app.designer._save_state()
    except Exception:
        pass
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
    try:
        app.designer._save_state()
    except Exception:
        pass
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


def widget_info(app) -> None:
    """Show a summary of the first selected widget's properties in status bar."""
    if not app.state.selected:
        app._set_status("Info: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    idx = app.state.selected[0]
    if not (0 <= idx < len(sc.widgets)):
        return
    w = sc.widgets[idx]
    ty = str(getattr(w, "type", "?") or "?")
    txt = str(getattr(w, "text", "") or "")
    if len(txt) > 12:
        txt = txt[:12] + "\u2026"
    pos = f"{int(w.x)},{int(w.y)}"
    size = f"{int(w.width)}x{int(w.height)}"
    style = str(getattr(w, "style", "default") or "default")
    fg = str(getattr(w, "color_fg", "") or "")
    bg = str(getattr(w, "color_bg", "") or "")
    z = int(getattr(w, "z_index", 0) or 0)
    flags = []
    if getattr(w, "locked", False):
        flags.append("L")
    if not getattr(w, "visible", True):
        flags.append("H")
    if not getattr(w, "enabled", True):
        flags.append("D")
    if getattr(w, "border", True):
        flags.append("B")
    flag_str = "".join(flags) if flags else "-"
    info = f"#{idx} {ty} '{txt}' @{pos} {size} z{z} {style} fg:{fg} bg:{bg} [{flag_str}]"
    app._set_status(info, ttl_sec=6.0)
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
    try:
        app.designer._save_state()
    except Exception:
        pass
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
            except Exception:
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


def auto_rename(app) -> None:
    """Auto-rename selected widgets as type_1, type_2, etc."""
    if not app.state.selected:
        app._set_status("Auto-rename: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    try:
        app.designer._save_state()
    except Exception:
        pass
    counter: Counter[str] = Counter()
    renamed = 0
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        ty = str(getattr(w, "type", "widget") or "widget").lower()
        counter[ty] += 1
        w.id = f"{ty}_{counter[ty]}"
        renamed += 1
    app._set_status(f"Renamed {renamed} widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def scene_stats(app) -> None:
    """Show scene statistics in the status bar."""
    sc = app.state.current_scene()
    total = len(sc.widgets)
    if total == 0:
        app._set_status(f"Scene '{sc.name}' {sc.width}x{sc.height}: empty.", ttl_sec=4.0)
        return
    types: Counter[str] = Counter()
    hidden = locked = disabled = 0
    for w in sc.widgets:
        types[str(getattr(w, "type", "?") or "?").lower()] += 1
        if not getattr(w, "visible", True):
            hidden += 1
        if getattr(w, "locked", False):
            locked += 1
        if not getattr(w, "enabled", True):
            disabled += 1
    type_str = " ".join(f"{k}:{v}" for k, v in types.most_common())
    flags = []
    if hidden:
        flags.append(f"{hidden}H")
    if locked:
        flags.append(f"{locked}L")
    if disabled:
        flags.append(f"{disabled}D")
    flag_str = f" [{','.join(flags)}]" if flags else ""
    app._set_status(
        f"Scene '{sc.name}' {sc.width}x{sc.height}: {total}w {type_str}{flag_str}",
        ttl_sec=6.0,
    )


def clear_margins(app) -> None:
    """Set margin_x and margin_y to 0 on all selected widgets."""
    if not app.state.selected:
        app._set_status("Clear margins: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    try:
        app.designer._save_state()
    except Exception:
        pass
    cleared = 0
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        old_mx = int(getattr(w, "margin_x", 0) or 0)
        old_my = int(getattr(w, "margin_y", 0) or 0)
        if old_mx != 0 or old_my != 0:
            w.margin_x = 0
            w.margin_y = 0
            cleared += 1
    app._set_status(
        f"Cleared margins on {cleared}/{len(app.state.selected)} widget(s).", ttl_sec=2.0
    )
    app._mark_dirty()


def hide_unselected(app) -> None:
    """Hide all widgets that are NOT in the current selection (isolation mode)."""
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("No widgets in scene.", ttl_sec=2.0)
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    selected_set = set(app.state.selected)
    hidden = 0
    for i, w in enumerate(sc.widgets):
        if i not in selected_set:
            if getattr(w, "visible", True):
                w.visible = False
                hidden += 1
    app._set_status(f"Isolated: hid {hidden} unselected widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def fit_scene_to_content(app) -> None:
    """Resize the current scene to tightly fit all widgets (with GRID padding)."""
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("No widgets to fit.", ttl_sec=2.0)
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    max_r = max(int(w.x) + int(w.width) for w in sc.widgets)
    max_b = max(int(w.y) + int(w.height) for w in sc.widgets)
    new_w = snap(max_r + GRID)
    new_h = snap(max_b + GRID)
    old_w, old_h = int(sc.width), int(sc.height)
    sc.width = max(GRID, new_w)
    sc.height = max(GRID, new_h)
    app._set_status(f"Scene resized: {old_w}x{old_h} -> {sc.width}x{sc.height}", ttl_sec=2.0)
    app._mark_dirty()


def show_all_widgets(app) -> None:
    """Unhide every hidden widget in the current scene."""
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("No widgets in scene.", ttl_sec=2.0)
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    shown = 0
    for w in sc.widgets:
        if not getattr(w, "visible", True):
            w.visible = True
            shown += 1
    if shown:
        app._set_status(f"Showed {shown} hidden widget(s).", ttl_sec=2.0)
    else:
        app._set_status("No hidden widgets to show.", ttl_sec=2.0)
    app._mark_dirty()


def unlock_all_widgets(app) -> None:
    """Unlock every locked widget in the current scene."""
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("No widgets in scene.", ttl_sec=2.0)
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    unlocked = 0
    for w in sc.widgets:
        if getattr(w, "locked", False):
            w.locked = False
            unlocked += 1
    if unlocked:
        app._set_status(f"Unlocked {unlocked} widget(s).", ttl_sec=2.0)
    else:
        app._set_status("No locked widgets to unlock.", ttl_sec=2.0)
    app._mark_dirty()


def toggle_all_borders(app) -> None:
    """Toggle border on all widgets in scene (all on -> all off, or all on)."""
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("No widgets in scene.", ttl_sec=2.0)
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    all_bordered = all(getattr(w, "border", True) for w in sc.widgets)
    new_val = not all_bordered
    for w in sc.widgets:
        w.border = new_val
    label = "ON" if new_val else "OFF"
    app._set_status(f"All borders {label} ({len(sc.widgets)} widgets).", ttl_sec=2.0)
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
    try:
        app.designer._save_state()
    except Exception:
        pass
    count = len(degenerate)
    for i in reversed(degenerate):
        sc.widgets.pop(i)
    app.state.selected = []
    app.state.selected_idx = None
    app.designer.selected_widget = None
    app._set_status(f"Removed {count} degenerate widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def enable_all_widgets(app) -> None:
    """Enable every disabled widget in the current scene."""
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("No widgets in scene.", ttl_sec=2.0)
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    enabled = 0
    for w in sc.widgets:
        if not getattr(w, "enabled", True):
            w.enabled = True
            enabled += 1
    if enabled:
        app._set_status(f"Enabled {enabled} widget(s).", ttl_sec=2.0)
    else:
        app._set_status("No disabled widgets to enable.", ttl_sec=2.0)
    app._mark_dirty()


def sort_widgets_by_position(app) -> None:
    """Sort widgets by position: top-to-bottom, then left-to-right."""
    sc = app.state.current_scene()
    if len(sc.widgets) < 2:
        app._set_status("Nothing to sort.", ttl_sec=2.0)
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    sc.widgets.sort(key=lambda w: (int(w.y), int(w.x)))
    app.state.selected = []
    app.state.selected_idx = None
    app.designer.selected_widget = None
    app._set_status(f"Sorted {len(sc.widgets)} widgets by position.", ttl_sec=2.0)
    app._mark_dirty()


def snap_sizes_to_grid(app) -> None:
    """Snap width and height of all selected widgets to the nearest grid multiple."""
    if not app.state.selected:
        app._set_status("Snap sizes: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    try:
        app.designer._save_state()
    except Exception:
        pass
    snapped = 0
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        nw = max(GRID, snap(int(w.width)))
        nh = max(GRID, snap(int(w.height)))
        nx = snap(int(w.x))
        ny = snap(int(w.y))
        if nw != int(w.width) or nh != int(w.height) or nx != int(w.x) or ny != int(w.y):
            w.width = nw
            w.height = nh
            w.x = nx
            w.y = ny
            snapped += 1
    app._set_status(
        f"Grid-snapped {snapped}/{len(app.state.selected)} widget(s) (pos+size).",
        ttl_sec=2.0,
    )
    app._mark_dirty()


def list_templates(app) -> None:
    """Show available template names in the status bar."""
    lib = getattr(app, "template_library", None)
    if lib is None or not hasattr(lib, "templates"):
        app._set_status("No template library.", ttl_sec=2.0)
        return
    names = list(lib.templates.keys()) if lib.templates else []
    if not names:
        app._set_status("No saved templates.", ttl_sec=2.0)
        return
    summary = ", ".join(names[:10])
    extra = f" (+{len(names) - 10} more)" if len(names) > 10 else ""
    app._set_status(f"Templates: {summary}{extra}", ttl_sec=6.0)


def clear_padding(app) -> None:
    """Set padding_x and padding_y to 0 on all selected widgets."""
    if not app.state.selected:
        app._set_status("Clear padding: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    try:
        app.designer._save_state()
    except Exception:
        pass
    cleared = 0
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        old_px = int(getattr(w, "padding_x", 0) or 0)
        old_py = int(getattr(w, "padding_y", 0) or 0)
        if old_px != 0 or old_py != 0:
            w.padding_x = 0
            w.padding_y = 0
            cleared += 1
    app._set_status(
        f"Cleared padding on {cleared}/{len(app.state.selected)} widget(s).", ttl_sec=2.0
    )
    app._mark_dirty()


def flatten_z_indices(app) -> None:
    """Reassign z_index 0,1,2,... based on current visual sort order."""
    sc = app.state.current_scene()
    if len(sc.widgets) < 2:
        app._set_status("Nothing to flatten.", ttl_sec=2.0)
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
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
    try:
        app.designer._save_state()
    except Exception:
        pass
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
    try:
        app.designer._save_state()
    except Exception:
        pass
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


def auto_name_scene(app) -> None:
    """Auto-name ALL widgets in the current scene as type_N."""
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("Scene empty.", ttl_sec=2.0)
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    counter: Counter[str] = Counter()
    for w in sc.widgets:
        ty = str(getattr(w, "type", "widget") or "widget").lower()
        counter[ty] += 1
        w.id = f"{ty}_{counter[ty]}"
    app._set_status(f"Named {len(sc.widgets)} widgets in scene.", ttl_sec=2.0)
    app._mark_dirty()


def remove_duplicates(app) -> None:
    """Remove widgets with identical position, size, and type (keep first)."""
    sc = app.state.current_scene()
    if len(sc.widgets) < 2:
        app._set_status("No duplicates possible.", ttl_sec=2.0)
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
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


def increment_text(app) -> None:
    """Append sequential numbers to selected widget texts (1, 2, 3...)."""
    if not app.state.selected:
        app._set_status("Inc text: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    valid = [i for i in app.state.selected if 0 <= i < len(sc.widgets)]
    if not valid:
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    for seq, i in enumerate(valid, 1):
        w = sc.widgets[i]
        base = str(getattr(w, "text", "") or "")
        # Strip existing trailing number
        base = re.sub(r"\s*\d+$", "", base)
        w.text = f"{base} {seq}" if base else str(seq)
    app._set_status(f"Numbered {len(valid)} widget text(s).", ttl_sec=2.0)
    app._mark_dirty()


def measure_selection(app) -> None:
    """Show distances/gaps between selected widgets in the status bar."""
    if not app.state.selected:
        app._set_status("Measure: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    widgets = []
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            widgets.append(sc.widgets[idx])
    if not widgets:
        return
    if len(widgets) == 1:
        w = widgets[0]
        app._set_status(
            f"{getattr(w, 'id', '?')}: pos=({w.x},{w.y}) size={w.width}×{w.height}",
            ttl_sec=4.0,
        )
        return
    # Bounding box of selection
    xs = [w.x for w in widgets]
    ys = [w.y for w in widgets]
    x2s = [w.x + int(getattr(w, "width", 0) or 0) for w in widgets]
    y2s = [w.y + int(getattr(w, "height", 0) or 0) for w in widgets]
    bx, by = min(xs), min(ys)
    bx2, by2 = max(x2s), max(y2s)
    bw, bh = bx2 - bx, by2 - by
    if len(widgets) == 2:
        a, b = widgets
        aw = int(getattr(a, "width", 0) or 0)
        ah = int(getattr(a, "height", 0) or 0)
        bw2 = int(getattr(b, "width", 0) or 0)
        bh2 = int(getattr(b, "height", 0) or 0)
        gap_h = max(b.x - (a.x + aw), a.x - (b.x + bw2))
        gap_v = max(b.y - (a.y + ah), a.y - (b.y + bh2))
        app._set_status(
            f"2 sel: bbox {bw}×{bh} | gap h={gap_h} v={gap_v}",
            ttl_sec=4.0,
        )
    else:
        app._set_status(
            f"{len(widgets)} sel: bbox {bw}×{bh} @ ({bx},{by})",
            ttl_sec=4.0,
        )


def replace_text_in_scene(app) -> None:
    """Find and replace text across all widgets in the current scene.

    Uses the inspector input buffer mechanism: first call prompts for
    'find|replace' pattern, then applies it.
    """
    sc = app.state.current_scene()
    # Use a simple prompt via status bar
    buf = getattr(app, "_replace_buf", None)
    if buf is None:
        # First call: set a flag so user types find|replace
        app._replace_buf = ""
        app._set_status("Replace: type find|replace then press Ctrl+F5 again", ttl_sec=5.0)
        return
    # Parse the buffer
    parts = buf.split("|", 1)
    app._replace_buf = None  # reset
    if len(parts) != 2 or not parts[0]:
        app._set_status("Replace cancelled (use find|replace format).", ttl_sec=2.0)
        return
    find_str, repl_str = parts
    try:
        app.designer._save_state()
    except Exception:
        pass
    changed = 0
    for w in sc.widgets:
        txt = str(getattr(w, "text", "") or "")
        if find_str in txt:
            w.text = txt.replace(find_str, repl_str)
            changed += 1
    app._set_status(f"Replaced '{find_str}'→'{repl_str}' in {changed} widget(s).", ttl_sec=3.0)
    app._mark_dirty()


def zoom_to_selection(app) -> None:
    """Zoom and pan so the current selection fills the canvas."""
    if not app.state.selected:
        app._set_status("Zoom to sel: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    widgets = [sc.widgets[i] for i in app.state.selected if 0 <= i < len(sc.widgets)]
    if not widgets:
        return
    xs = [w.x for w in widgets]
    ys = [w.y for w in widgets]
    x2s = [w.x + int(getattr(w, "width", 8) or 8) for w in widgets]
    y2s = [w.y + int(getattr(w, "height", 8) or 8) for w in widgets]
    bx, by = min(xs), min(ys)
    bx2, by2 = max(x2s), max(y2s)
    bw = max(8, bx2 - bx)
    bh = max(8, by2 - by)
    margin = 16
    canvas = getattr(app, "layout", None)
    if canvas is None:
        return
    cr = canvas.canvas_rect
    cw = max(1, cr.width)
    ch = max(1, cr.height)
    sx = cw / (bw + margin * 2)
    sy = ch / (bh + margin * 2)
    new_scale = max(1, min(8, int(min(sx, sy))))
    app._set_scale(new_scale)
    cx = bx + bw // 2
    cy = by + bh // 2
    app.pan_offset_x = cr.width // 2 - cx * new_scale
    app.pan_offset_y = cr.height // 2 - cy * new_scale
    app._set_status(f"Zoom to sel: {len(widgets)} widget(s), scale={new_scale}.", ttl_sec=2.0)
    app._mark_dirty()


def scene_overview(app) -> None:
    """Show summary of all scenes in the status bar."""
    scenes = app.designer.scenes
    parts = []
    total = 0
    for name, sc in scenes.items():
        n = len(sc.widgets)
        total += n
        parts.append(f"{name}({n})")
    summary = " | ".join(parts)
    app._set_status(f"{len(scenes)} scene(s), {total} widgets: {summary}", ttl_sec=5.0)


def widget_type_summary(app) -> None:
    """Show count of each widget type in the current scene."""
    sc = app.state.current_scene()
    counts = Counter(w.type for w in sc.widgets)
    if not counts:
        app._set_status("Scene is empty.", ttl_sec=2.0)
        return
    parts = [f"{t}:{n}" for t, n in counts.most_common()]
    app._set_status(f"{len(sc.widgets)} widgets — {', '.join(parts)}", ttl_sec=5.0)


def toggle_focus_order_overlay(app) -> None:
    """Toggle display of focus navigation order numbers on widgets."""
    current = bool(getattr(app, "show_focus_order", False))
    app.show_focus_order = not current
    state = "ON" if app.show_focus_order else "OFF"
    app._set_status(f"Focus order overlay: {state}", ttl_sec=2.0)
    app._mark_dirty()


def fill_scene(app) -> None:
    """Resize selected widget(s) to fill the entire scene."""
    if not app.state.selected:
        app._set_status("Fill scene: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    app._save_undo_state()
    count = 0
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            w = sc.widgets[idx]
            w.x = 0
            w.y = 0
            w.width = int(sc.width)
            w.height = int(sc.height)
            count += 1
    app._set_status(f"Filled {count} widget(s) to scene size.", ttl_sec=2.0)
    app._mark_dirty()


def auto_label_widgets(app) -> None:
    """Auto-set text of selected widgets to Type #N based on their order."""
    if not app.state.selected:
        app._set_status("Auto-label: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    app._save_undo_state()
    count = 0
    for i, idx in enumerate(sorted(app.state.selected)):
        if 0 <= idx < len(sc.widgets):
            w = sc.widgets[idx]
            wtype = str(getattr(w, "type", "widget") or "widget").capitalize()
            w.text = f"{wtype} {i + 1}"
            count += 1
    app._set_status(f"Auto-labeled {count} widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def inset_widgets(app, amount: int = 0) -> None:
    """Shrink each selected widget inward by `amount` pixels on all sides."""
    if amount == 0:
        amount = GRID
    if not app.state.selected:
        app._set_status("Inset: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    app._save_undo_state()
    count = 0
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        ww = int(getattr(w, "width", 0) or 0)
        wh = int(getattr(w, "height", 0) or 0)
        if ww <= amount * 2 or wh <= amount * 2:
            continue  # too small to inset further
        w.x = int(w.x) + amount
        w.y = int(w.y) + amount
        w.width = ww - amount * 2
        w.height = wh - amount * 2
        count += 1
    app._set_status(f"Inset {count} widget(s) by {amount}px.", ttl_sec=2.0)
    app._mark_dirty()


def outset_widgets(app, amount: int = 0) -> None:
    """Expand each selected widget outward by `amount` pixels on all sides."""
    if amount == 0:
        amount = GRID
    if not app.state.selected:
        app._set_status("Outset: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    app._save_undo_state()
    count = 0
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        w.x = max(0, int(w.x) - amount)
        w.y = max(0, int(w.y) - amount)
        w.width = int(getattr(w, "width", 0) or 0) + amount * 2
        w.height = int(getattr(w, "height", 0) or 0) + amount * 2
        count += 1
    app._set_status(f"Outset {count} widget(s) by {amount}px.", ttl_sec=2.0)
    app._mark_dirty()


def delete_hidden_widgets(app) -> None:
    """Delete all invisible (visible=False) widgets from the current scene."""
    sc = app.state.current_scene()
    hidden = [i for i, w in enumerate(sc.widgets) if not getattr(w, "visible", True)]
    if not hidden:
        app._set_status("No hidden widgets to delete.", ttl_sec=2.0)
        return
    app._save_undo_state()
    for idx in reversed(hidden):
        sc.widgets.pop(idx)
    app.state.selected = []
    app.state.selected_idx = None
    app._set_status(f"Deleted {len(hidden)} hidden widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def delete_offscreen_widgets(app) -> None:
    """Delete widgets that are completely outside the scene bounds."""
    sc = app.state.current_scene()
    sw, sh = int(sc.width), int(sc.height)
    offscreen = []
    for i, w in enumerate(sc.widgets):
        wx = int(getattr(w, "x", 0) or 0)
        wy = int(getattr(w, "y", 0) or 0)
        ww = int(getattr(w, "width", 0) or 0)
        wh = int(getattr(w, "height", 0) or 0)
        # Completely outside
        if wx + ww <= 0 or wy + wh <= 0 or wx >= sw or wy >= sh:
            offscreen.append(i)
    if not offscreen:
        app._set_status("No offscreen widgets to delete.", ttl_sec=2.0)
        return
    app._save_undo_state()
    for idx in reversed(offscreen):
        sc.widgets.pop(idx)
    app.state.selected = []
    app.state.selected_idx = None
    app._set_status(f"Deleted {len(offscreen)} offscreen widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def tile_fill_scene(app) -> None:
    """Tile selected widget(s) to fill the entire scene (grid of copies)."""
    if not app.state.selected:
        app._set_status("Tile fill: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    if len(app.state.selected) != 1:
        app._set_status("Tile fill: select exactly 1 widget.", ttl_sec=2.0)
        return
    src_idx = app.state.selected[0]
    if not (0 <= src_idx < len(sc.widgets)):
        return
    src = sc.widgets[src_idx]
    sw, sh = int(sc.width), int(sc.height)
    ww = max(GRID, int(getattr(src, "width", GRID) or GRID))
    wh = max(GRID, int(getattr(src, "height", GRID) or GRID))
    cols = max(1, sw // ww)
    rows = max(1, sh // wh)
    app._save_undo_state()
    base = len(sc.widgets)
    count = 0
    for r in range(rows):
        for c in range(cols):
            if r == 0 and c == 0:
                # Reposition the original
                src.x = 0
                src.y = 0
                continue
            d = asdict(src)
            d["x"] = c * ww
            d["y"] = r * wh
            sc.widgets.append(WidgetConfig(**d))
            count += 1
    total = count + 1
    app.state.selected = list(range(src_idx, src_idx + 1)) + list(range(base, base + count))
    app.state.selected_idx = src_idx
    app._set_status(f"Tiled {total} copies ({cols}×{rows}).", ttl_sec=2.0)
    app._mark_dirty()


def match_first_width(app) -> None:
    """Set all selected widgets to the same width as the first selected."""
    if len(app.state.selected) < 2:
        app._set_status("Match width: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    first_idx = app.state.selected[0]
    if not (0 <= first_idx < len(sc.widgets)):
        return
    target_w = int(getattr(sc.widgets[first_idx], "width", GRID) or GRID)
    app._save_undo_state()
    count = 0
    for idx in app.state.selected[1:]:
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].width = target_w
            count += 1
    app._set_status(f"Set {count} widget(s) width to {target_w}.", ttl_sec=2.0)
    app._mark_dirty()


def match_first_height(app) -> None:
    """Set all selected widgets to the same height as the first selected."""
    if len(app.state.selected) < 2:
        app._set_status("Match height: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    first_idx = app.state.selected[0]
    if not (0 <= first_idx < len(sc.widgets)):
        return
    target_h = int(getattr(sc.widgets[first_idx], "height", GRID) or GRID)
    app._save_undo_state()
    count = 0
    for idx in app.state.selected[1:]:
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].height = target_h
            count += 1
    app._set_status(f"Set {count} widget(s) height to {target_h}.", ttl_sec=2.0)
    app._mark_dirty()


def scatter_random(app) -> None:
    """Scatter selected widgets to random positions within the scene."""
    if not app.state.selected:
        app._set_status("Scatter: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    sw, sh = int(sc.width), int(sc.height)
    app._save_undo_state()
    count = 0
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        ww = max(GRID, int(getattr(w, "width", GRID) or GRID))
        wh = max(GRID, int(getattr(w, "height", GRID) or GRID))
        max_x = max(0, sw - ww)
        max_y = max(0, sh - wh)
        w.x = snap(random.randint(0, max_x))  # noqa: S311
        w.y = snap(random.randint(0, max_y))  # noqa: S311
        count += 1
    app._set_status(f"Scattered {count} widget(s) randomly.", ttl_sec=2.0)
    app._mark_dirty()


def toggle_all_checked(app) -> None:
    """Toggle the checked state of all selected checkbox/radiobutton widgets."""
    if not app.state.selected:
        app._set_status("Toggle checked: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    app._save_undo_state()
    count = 0
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        wtype = str(getattr(w, "type", "") or "").lower()
        if wtype in ("checkbox", "radiobutton"):
            w.checked = not getattr(w, "checked", False)
            count += 1
    if count:
        app._set_status(f"Toggled checked on {count} widget(s).", ttl_sec=2.0)
    else:
        app._set_status("No checkbox/radiobutton in selection.", ttl_sec=2.0)
    app._mark_dirty()


def reset_all_values(app) -> None:
    """Reset value to min_value on all selected value-based widgets."""
    if not app.state.selected:
        app._set_status("Reset values: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    app._save_undo_state()
    count = 0
    value_types = {"gauge", "slider", "progressbar"}
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        wtype = str(getattr(w, "type", "") or "").lower()
        if wtype in value_types:
            w.value = int(getattr(w, "min_value", 0) or 0)
            count += 1
    if count:
        app._set_status(f"Reset values on {count} widget(s).", ttl_sec=2.0)
    else:
        app._set_status("No value widgets in selection.", ttl_sec=2.0)
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


def number_widget_ids(app) -> None:
    """Auto-assign _widget_id as 'type_N' for all widgets in the scene."""
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("No widgets.", ttl_sec=2.0)
        return
    app._save_undo_state()
    counters: dict[str, int] = {}
    for w in sc.widgets:
        wtype = str(getattr(w, "type", "widget") or "widget").lower()
        n = counters.get(wtype, 0)
        counters[wtype] = n + 1
        w._widget_id = f"{wtype}_{n}"
    app._set_status(f"Numbered {len(sc.widgets)} widget ID(s).", ttl_sec=2.0)
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


def clone_to_grid(app) -> None:
    """Clone selected single widget into a 3-col grid filling the scene."""
    sc = app.state.current_scene()
    if len(app.state.selected) != 1:
        app._set_status("Select exactly 1 widget.", ttl_sec=2.0)
        return
    idx = app.state.selected[0]
    if not (0 <= idx < len(sc.widgets)):
        return
    src = sc.widgets[idx]
    w = int(getattr(src, "width", 32) or 32)
    h = int(getattr(src, "height", 16) or 16)
    gap = 8
    cols = max(1, (sc.width + gap) // (w + gap))
    rows = max(1, (sc.height + gap) // (h + gap))
    app._save_undo_state()
    new_indices = [idx]
    for r in range(rows):
        for c in range(cols):
            if r == 0 and c == 0:
                src.x = 0
                src.y = 0
                continue
            clone = copy.deepcopy(src)
            clone.x = c * (w + gap)
            clone.y = r * (h + gap)
            sc.widgets.append(clone)
            new_indices.append(len(sc.widgets) - 1)
    app.state.selected = new_indices
    total = len(new_indices)
    app._set_status(f"Grid: {cols}×{rows} = {total} widget(s).", ttl_sec=2.0)
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


def clamp_to_scene(app) -> None:
    """Clip selected widgets so they fit entirely within the scene bounds."""
    if not app.state.selected:
        app._set_status("Nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    sw, sh = sc.width, sc.height
    app._save_undo_state()
    count = 0
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        ww = int(getattr(w, "width", 8) or 8)
        wh = int(getattr(w, "height", 8) or 8)
        changed = False
        if w.x < 0:
            w.x = 0
            changed = True
        if w.y < 0:
            w.y = 0
            changed = True
        if w.x + ww > sw:
            w.x = max(0, sw - ww)
            changed = True
        if w.y + wh > sh:
            w.y = max(0, sh - wh)
            changed = True
        if changed:
            count += 1
    app._set_status(f"Clamped {count} widget(s) to scene.", ttl_sec=2.0)
    app._mark_dirty()


def snap_all_to_grid(app) -> None:
    """Round x/y/w/h of selected widgets to the nearest GRID multiple."""
    if not app.state.selected:
        app._set_status("Nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    app._save_undo_state()
    count = 0
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        w.x = snap(int(w.x))
        w.y = snap(int(w.y))
        w.width = max(GRID, snap(int(getattr(w, "width", GRID) or GRID)))
        w.height = max(GRID, snap(int(getattr(w, "height", GRID) or GRID)))
        count += 1
    app._set_status(f"Snapped {count} widget(s) to grid ({GRID}px).", ttl_sec=2.0)
    app._mark_dirty()


def size_to_text(app) -> None:
    """Auto-size selected widgets' width to fit their text (6px per char + padding)."""
    if not app.state.selected:
        app._set_status("Nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    app._save_undo_state()
    char_w = 6
    count = 0
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        text = str(getattr(w, "text", "") or "")
        if not text:
            continue
        pad_x = int(getattr(w, "padding_x", 1) or 1)
        new_w = max(GRID, snap(len(text) * char_w + pad_x * 2))
        w.width = new_w
        count += 1
    if count:
        app._set_status(f"Sized {count} widget(s) to text.", ttl_sec=2.0)
    else:
        app._set_status("No widgets with text.", ttl_sec=2.0)
    app._mark_dirty()


def fill_parent(app) -> None:
    """Expand each selected widget to fill its smallest enclosing panel (8px padding)."""
    if not app.state.selected:
        app._set_status("Nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    app._save_undo_state()
    pad = GRID
    count = 0
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        child = sc.widgets[idx]
        cx, cy = int(child.x), int(child.y)
        cw = int(getattr(child, "width", 8) or 8)
        ch = int(getattr(child, "height", 8) or 8)
        best_i = None
        best_area = float("inf")
        for i, pw in enumerate(sc.widgets):
            if i == idx:
                continue
            if str(getattr(pw, "type", "") or "").lower() != "panel":
                continue
            px, py = int(pw.x), int(pw.y)
            pww = int(getattr(pw, "width", 0) or 0)
            pwh = int(getattr(pw, "height", 0) or 0)
            if px <= cx and py <= cy and px + pww >= cx + cw and py + pwh >= cy + ch:
                area = pww * pwh
                if area < best_area:
                    best_area = area
                    best_i = i
        if best_i is not None:
            p = sc.widgets[best_i]
            child.x = int(p.x) + pad
            child.y = int(p.y) + pad
            child.width = max(GRID, int(getattr(p, "width", 0) or 0) - pad * 2)
            child.height = max(GRID, int(getattr(p, "height", 0) or 0) - pad * 2)
            count += 1
    if count:
        app._set_status(f"Filled {count} widget(s) to parent.", ttl_sec=2.0)
    else:
        app._set_status("No enclosing panels found.", ttl_sec=2.0)
    app._mark_dirty()


def clear_all_text(app) -> None:
    """Set text to empty string on all selected widgets."""
    if not app.state.selected:
        app._set_status("Nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    app._save_undo_state()
    count = 0
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        if str(getattr(w, "text", "") or ""):
            w.text = ""
            count += 1
    app._set_status(f"Cleared text on {count} widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def number_text(app) -> None:
    """Set text to '1', '2', '3'… on selected widgets by position order."""
    if not app.state.selected:
        app._set_status("Nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    app._save_undo_state()
    indices = sorted(
        app.state.selected,
        key=lambda i: (sc.widgets[i].y, sc.widgets[i].x) if 0 <= i < len(sc.widgets) else (0, 0),
    )
    for n, idx in enumerate(indices, 1):
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].text = str(n)
    app._set_status(f"Numbered {len(indices)} widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def spread_values(app) -> None:
    """Distribute value linearly from min to max across selected widgets."""
    if len(app.state.selected) < 2:
        app._set_status("Spread values: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    value_types = {"gauge", "slider", "progressbar"}
    indices = [
        i
        for i in app.state.selected
        if 0 <= i < len(sc.widgets)
        and str(getattr(sc.widgets[i], "type", "") or "").lower() in value_types
    ]
    if len(indices) < 2:
        app._set_status("Need 2+ gauge/slider/progressbar.", ttl_sec=2.0)
        return
    app._save_undo_state()
    indices.sort(key=lambda i: (sc.widgets[i].y, sc.widgets[i].x))
    first = sc.widgets[indices[0]]
    lo = int(getattr(first, "min_value", 0) or 0)
    hi = int(getattr(first, "max_value", 100) or 100)
    count = len(indices)
    for n, idx in enumerate(indices):
        val = lo + (hi - lo) * n // (count - 1)
        sc.widgets[idx].value = val
    app._set_status(f"Spread {lo}–{hi} across {count} widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def reset_padding(app) -> None:
    """Zero out padding and margin on selected widgets."""
    if not app.state.selected:
        app._set_status("Nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    app._save_undo_state()
    count = 0
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        changed = False
        for attr in ("padding_x", "padding_y", "margin_x", "margin_y"):
            if int(getattr(w, attr, 0) or 0) != 0:
                setattr(w, attr, 0)
                changed = True
        if changed:
            count += 1
    app._set_status(f"Reset padding/margin on {count} widget(s).", ttl_sec=2.0)
    app._mark_dirty()


def reset_colors(app) -> None:
    """Reset color_fg to white and color_bg to black on selected widgets."""
    if not app.state.selected:
        app._set_status("Nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    app._save_undo_state()
    count = 0
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        changed = False
        if str(getattr(w, "color_fg", "") or "") != "white":
            w.color_fg = "white"
            changed = True
        if str(getattr(w, "color_bg", "") or "") != "black":
            w.color_bg = "black"
            changed = True
        if changed:
            count += 1
    app._set_status(f"Reset colors on {count} widget(s).", ttl_sec=2.0)
    app._mark_dirty()
