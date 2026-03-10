from __future__ import annotations

from ..constants import GRID, snap


def snap_selection_to_grid(app) -> None:
    """Snap all selected widget positions to the nearest grid point."""
    if not app.state.selected:
        app._set_status("Snap to grid: nothing selected.", ttl_sec=2.0)
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
        nx = snap(int(w.x))
        ny = snap(int(w.y))
        if nx != int(w.x) or ny != int(w.y):
            w.x = nx
            w.y = ny
            snapped += 1
    app._set_status(f"Snapped {snapped}/{len(app.state.selected)} widget(s) to grid.", ttl_sec=2.0)
    app._mark_dirty()


def center_in_scene(app) -> None:
    """Center selected widgets as a group in the scene."""
    if not app.state.selected:
        app._set_status("Center: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    valid = [i for i in app.state.selected if 0 <= i < len(sc.widgets)]
    if not valid:
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    sw = int(getattr(sc, "width", 256) or 256)
    sh = int(getattr(sc, "height", 128) or 128)
    min_x = min(int(sc.widgets[i].x) for i in valid)
    min_y = min(int(sc.widgets[i].y) for i in valid)
    max_x = max(int(sc.widgets[i].x) + int(sc.widgets[i].width or 0) for i in valid)
    max_y = max(int(sc.widgets[i].y) + int(sc.widgets[i].height or 0) for i in valid)
    gw = max_x - min_x
    gh = max_y - min_y
    dx = (sw - gw) // 2 - min_x
    dy = (sh - gh) // 2 - min_y
    for i in valid:
        w = sc.widgets[i]
        w.x = int(w.x) + dx
        w.y = int(w.y) + dy
    app._set_status(f"Centered {len(valid)} widget(s) in scene.", ttl_sec=2.0)
    app._mark_dirty()


def align_to_scene_top(app) -> None:
    """Move selected widgets so their top edge touches y=0."""
    if not app.state.selected:
        app._set_status("Align top: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    app._save_undo_state()
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].y = 0
    app._set_status(f"Aligned {len(app.state.selected)} widget(s) to top.", ttl_sec=2.0)
    app._mark_dirty()


def align_to_scene_bottom(app) -> None:
    """Move selected widgets so their bottom edge touches scene bottom."""
    if not app.state.selected:
        app._set_status("Align bottom: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    sh = int(sc.height)
    app._save_undo_state()
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            w = sc.widgets[idx]
            w.y = sh - int(getattr(w, "height", GRID) or GRID)
    app._set_status(f"Aligned {len(app.state.selected)} widget(s) to bottom.", ttl_sec=2.0)
    app._mark_dirty()


def align_to_scene_left(app) -> None:
    """Move selected widgets so their left edge touches x=0."""
    if not app.state.selected:
        app._set_status("Align left: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    app._save_undo_state()
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].x = 0
    app._set_status(f"Aligned {len(app.state.selected)} widget(s) to left.", ttl_sec=2.0)
    app._mark_dirty()


def align_to_scene_right(app) -> None:
    """Move selected widgets so their right edge touches scene right."""
    if not app.state.selected:
        app._set_status("Align right: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    sw = int(sc.width)
    app._save_undo_state()
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            w = sc.widgets[idx]
            w.x = sw - int(getattr(w, "width", GRID) or GRID)
    app._set_status(f"Aligned {len(app.state.selected)} widget(s) to right.", ttl_sec=2.0)
    app._mark_dirty()


def center_horizontal(app) -> None:
    """Center selected widgets horizontally in the scene."""
    if not app.state.selected:
        app._set_status("Center H: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    sw = int(sc.width)
    app._save_undo_state()
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            w = sc.widgets[idx]
            ww = int(getattr(w, "width", GRID) or GRID)
            w.x = (sw - ww) // 2
    app._set_status(f"Centered {len(app.state.selected)} widget(s) horizontally.", ttl_sec=2.0)
    app._mark_dirty()


def center_vertical(app) -> None:
    """Center selected widgets vertically in the scene."""
    if not app.state.selected:
        app._set_status("Center V: nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    sh = int(sc.height)
    app._save_undo_state()
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            w = sc.widgets[idx]
            wh = int(getattr(w, "height", GRID) or GRID)
            w.y = (sh - wh) // 2
    app._set_status(f"Centered {len(app.state.selected)} widget(s) vertically.", ttl_sec=2.0)
    app._mark_dirty()


def center_in_parent(app) -> None:
    """Center each selected widget inside its smallest enclosing panel."""
    if not app.state.selected:
        app._set_status("Nothing selected.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    app._save_undo_state()
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
            px, py = int(p.x), int(p.y)
            pww = int(getattr(p, "width", 0) or 0)
            pwh = int(getattr(p, "height", 0) or 0)
            child.x = snap(px + (pww - cw) // 2)
            child.y = snap(py + (pwh - ch) // 2)
            count += 1
    if count:
        app._set_status(f"Centered {count} widget(s) in parent panel.", ttl_sec=2.0)
    else:
        app._set_status("No enclosing panels found.", ttl_sec=2.0)
    app._mark_dirty()


def align_h_centers(app) -> None:
    """Align horizontal centers of selected widgets to the first widget's center."""
    if len(app.state.selected) < 2:
        app._set_status("Align centers: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    first_idx = app.state.selected[0]
    if not (0 <= first_idx < len(sc.widgets)):
        return
    ref = sc.widgets[first_idx]
    ref_cx = int(ref.x) + int(getattr(ref, "width", 0) or 0) // 2
    app._save_undo_state()
    count = 0
    for idx in app.state.selected[1:]:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        ww = int(getattr(w, "width", 0) or 0)
        w.x = snap(ref_cx - ww // 2)
        count += 1
    app._set_status(f"Aligned {count + 1} widget center(s) horizontally.", ttl_sec=2.0)
    app._mark_dirty()


def align_v_centers(app) -> None:
    """Align vertical centers of selected widgets to the first widget's center."""
    if len(app.state.selected) < 2:
        app._set_status("Align centers: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    first_idx = app.state.selected[0]
    if not (0 <= first_idx < len(sc.widgets)):
        return
    ref = sc.widgets[first_idx]
    ref_cy = int(ref.y) + int(getattr(ref, "height", 0) or 0) // 2
    app._save_undo_state()
    count = 0
    for idx in app.state.selected[1:]:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        wh = int(getattr(w, "height", 0) or 0)
        w.y = snap(ref_cy - wh // 2)
        count += 1
    app._set_status(f"Aligned {count + 1} widget center(s) vertically.", ttl_sec=2.0)
    app._mark_dirty()


def align_left_edges(app) -> None:
    """Align left edges of selected widgets to the first widget's x."""
    if len(app.state.selected) < 2:
        app._set_status("Align left: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    first_idx = app.state.selected[0]
    if not (0 <= first_idx < len(sc.widgets)):
        return
    ref_x = int(sc.widgets[first_idx].x)
    app._save_undo_state()
    count = 0
    for idx in app.state.selected[1:]:
        if not (0 <= idx < len(sc.widgets)):
            continue
        sc.widgets[idx].x = ref_x
        count += 1
    app._set_status(f"Aligned {count + 1} widget(s) left.", ttl_sec=2.0)
    app._mark_dirty()


def align_top_edges(app) -> None:
    """Align top edges of selected widgets to the first widget's y."""
    if len(app.state.selected) < 2:
        app._set_status("Align top: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    first_idx = app.state.selected[0]
    if not (0 <= first_idx < len(sc.widgets)):
        return
    ref_y = int(sc.widgets[first_idx].y)
    app._save_undo_state()
    count = 0
    for idx in app.state.selected[1:]:
        if not (0 <= idx < len(sc.widgets)):
            continue
        sc.widgets[idx].y = ref_y
        count += 1
    app._set_status(f"Aligned {count + 1} widget(s) top.", ttl_sec=2.0)
    app._mark_dirty()


def align_right_edges(app) -> None:
    """Align right edges of selected widgets to the first widget's right edge."""
    if len(app.state.selected) < 2:
        app._set_status("Align right: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    first_idx = app.state.selected[0]
    if not (0 <= first_idx < len(sc.widgets)):
        return
    ref = sc.widgets[first_idx]
    ref_right = int(ref.x) + int(getattr(ref, "width", 0) or 0)
    app._save_undo_state()
    count = 0
    for idx in app.state.selected[1:]:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        ww = int(getattr(w, "width", 0) or 0)
        w.x = ref_right - ww
        count += 1
    app._set_status(f"Aligned {count + 1} widget(s) right.", ttl_sec=2.0)
    app._mark_dirty()


def align_bottom_edges(app) -> None:
    """Align bottom edges of selected widgets to the first widget's bottom edge."""
    if len(app.state.selected) < 2:
        app._set_status("Align bottom: select 2+ widgets.", ttl_sec=2.0)
        return
    sc = app.state.current_scene()
    first_idx = app.state.selected[0]
    if not (0 <= first_idx < len(sc.widgets)):
        return
    ref = sc.widgets[first_idx]
    ref_bottom = int(ref.y) + int(getattr(ref, "height", 0) or 0)
    app._save_undo_state()
    count = 0
    for idx in app.state.selected[1:]:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        wh = int(getattr(w, "height", 0) or 0)
        w.y = ref_bottom - wh
        count += 1
    app._set_status(f"Aligned {count + 1} widget(s) bottom.", ttl_sec=2.0)
    app._mark_dirty()
