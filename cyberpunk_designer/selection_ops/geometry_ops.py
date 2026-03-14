"""Widget geometry: margins, padding, fill, sizing, snap."""

from __future__ import annotations

import copy
import random
from dataclasses import asdict

from ui_designer import WidgetConfig

from ..constants import GRID, snap
from .core import save_undo


def clear_margins(app) -> None:
    """Set margin_x and margin_y to 0 on all selected widgets."""
    if not app.state.selected:
        app._set_status("Clear margins: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    save_undo(app)
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


def clear_padding(app) -> None:
    """Set padding_x and padding_y to 0 on all selected widgets."""
    if not app.state.selected:
        app._set_status("Clear padding: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    save_undo(app)
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


def fit_scene_to_content(app) -> None:
    """Resize the current scene to tightly fit all widgets (with GRID padding)."""
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("No widgets to fit.", ttl_sec=2.0)
        return
    save_undo(app)
    max_r = max(int(w.x) + int(w.width) for w in sc.widgets)
    max_b = max(int(w.y) + int(w.height) for w in sc.widgets)
    new_w = snap(max_r + GRID)
    new_h = snap(max_b + GRID)
    old_w, old_h = int(sc.width), int(sc.height)
    sc.width = max(GRID, new_w)
    sc.height = max(GRID, new_h)
    app._set_status(f"Scene resized: {old_w}x{old_h} -> {sc.width}x{sc.height}", ttl_sec=2.0)
    app._mark_dirty()


def snap_sizes_to_grid(app) -> None:
    """Snap width and height of all selected widgets to the nearest grid multiple."""
    if not app.state.selected:
        app._set_status("Snap sizes: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    save_undo(app)
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
