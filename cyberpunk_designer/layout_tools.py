from __future__ import annotations

from typing import Iterable, List, Optional, Tuple

import pygame

from ui_designer import WidgetConfig

from .constants import GRID, GUIDE_TOL, snap


def _selected_widgets(app) -> List[Tuple[int, WidgetConfig]]:
    sc = app.state.current_scene()
    out: List[Tuple[int, WidgetConfig]] = []
    for idx in list(getattr(app.state, "selected", []) or []):
        try:
            i = int(idx)
        except Exception:
            continue
        if 0 <= i < len(sc.widgets):
            out.append((i, sc.widgets[i]))
    return out


def _any_locked(items: Iterable[Tuple[int, WidgetConfig]]) -> bool:
    return any(bool(getattr(w, "locked", False)) for _i, w in items)


def _scene_size(app) -> Tuple[int, int]:
    try:
        sc = app.state.current_scene()
        return int(getattr(sc, "width", 0) or 0), int(getattr(sc, "height", 0) or 0)
    except Exception:
        return 0, 0


def _clamp_xy_in_scene(app, x: int, y: int, w: WidgetConfig) -> Tuple[int, int]:
    sc_w, sc_h = _scene_size(app)
    ww = max(GRID, int(getattr(w, "width", GRID) or GRID))
    wh = max(GRID, int(getattr(w, "height", GRID) or GRID))
    max_x = max(0, int(sc_w) - ww)
    max_y = max(0, int(sc_h) - wh)
    x = max(0, min(max_x, int(x)))
    y = max(0, min(max_y, int(y)))
    if bool(getattr(app, "snap_enabled", True)):
        x = snap(int(x))
        y = snap(int(y))
        x = max(0, min(max_x, int(x)))
        y = max(0, min(max_y, int(y)))
    return x, y


def align_selection(app, mode: str) -> None:
    """Align selected widgets.

    Modes:
      - left, hcenter, right
      - top, vcenter, bottom
    """
    items = _selected_widgets(app)
    if not items:
        app._set_status("Align: no selection.", ttl_sec=2.0)
        return

    mode = str(mode or "").strip().lower()
    if mode not in {"left", "hcenter", "right", "top", "vcenter", "bottom"}:
        app._set_status(f"Align: unknown mode {mode!r}.", ttl_sec=3.0)
        return

    sc = app.state.current_scene()
    selection_indices = [i for i, _w in items]
    bounds = app._selection_bounds(selection_indices)
    if bounds is None:
        app._set_status("Align: selection bounds missing.", ttl_sec=2.0)
        return

    saved = False
    changed = 0
    skipped_locked = 0

    if len(items) == 1:
        idx, w = items[0]
        if bool(getattr(w, "locked", False)):
            app._set_status("Align: selection is locked.", ttl_sec=2.0)
            return
        sc_w = int(getattr(sc, "width", 0) or 0)
        sc_h = int(getattr(sc, "height", 0) or 0)
        ww = max(GRID, int(getattr(w, "width", GRID) or GRID))
        wh = max(GRID, int(getattr(w, "height", GRID) or GRID))
        if mode == "left":
            nx, ny = 0, int(getattr(w, "y", 0) or 0)
        elif mode == "hcenter":
            nx, ny = max(0, (sc_w - ww) // 2), int(getattr(w, "y", 0) or 0)
        elif mode == "right":
            nx, ny = max(0, sc_w - ww), int(getattr(w, "y", 0) or 0)
        elif mode == "top":
            nx, ny = int(getattr(w, "x", 0) or 0), 0
        elif mode == "vcenter":
            nx, ny = int(getattr(w, "x", 0) or 0), max(0, (sc_h - wh) // 2)
        else:  # bottom
            nx, ny = int(getattr(w, "x", 0) or 0), max(0, sc_h - wh)
        nx, ny = _clamp_xy_in_scene(app, nx, ny, w)
        if (int(getattr(w, "x", 0) or 0), int(getattr(w, "y", 0) or 0)) != (nx, ny):
            try:
                app.designer._save_state()
            except Exception:
                pass
            w.x = nx
            w.y = ny
            app._mark_dirty()
            app._set_status(f"Aligned {mode}.", ttl_sec=2.0)
        return

    for _idx, w in items:
        if bool(getattr(w, "locked", False)):
            skipped_locked += 1
            continue
        cur_x = int(getattr(w, "x", 0) or 0)
        cur_y = int(getattr(w, "y", 0) or 0)
        ww = max(GRID, int(getattr(w, "width", GRID) or GRID))
        wh = max(GRID, int(getattr(w, "height", GRID) or GRID))

        nx, ny = cur_x, cur_y
        if mode == "left":
            nx = int(bounds.x)
        elif mode == "hcenter":
            nx = int(bounds.centerx) - ww // 2
        elif mode == "right":
            nx = int(bounds.right) - ww
        elif mode == "top":
            ny = int(bounds.y)
        elif mode == "vcenter":
            ny = int(bounds.centery) - wh // 2
        elif mode == "bottom":
            ny = int(bounds.bottom) - wh

        nx, ny = _clamp_xy_in_scene(app, nx, ny, w)
        if (cur_x, cur_y) == (nx, ny):
            continue
        if not saved:
            try:
                app.designer._save_state()
            except Exception:
                pass
            saved = True
        w.x = nx
        w.y = ny
        changed += 1

    if changed:
        msg = f"Align {mode}: updated {changed} widget(s)."
        if skipped_locked:
            msg += f" Skipped locked: {skipped_locked}."
        app._set_status(msg, ttl_sec=2.5)
        app._mark_dirty()
    else:
        if skipped_locked:
            app._set_status(
                f"Align {mode}: nothing to change (locked: {skipped_locked}).", ttl_sec=2.5
            )
        else:
            app._set_status(f"Align {mode}: nothing to change.", ttl_sec=2.0)


def distribute_selection(app, axis: str) -> None:
    """Distribute selected widgets evenly.

    axis:
      - "h": horizontal spacing (x)
      - "v": vertical spacing (y)
    """
    items = _selected_widgets(app)
    if len(items) < 3:
        app._set_status("Distribute: select 3+ widgets.", ttl_sec=2.5)
        return
    if _any_locked(items):
        app._set_status("Distribute: selection contains locked widget(s).", ttl_sec=3.0)
        return

    axis = str(axis or "").strip().lower()
    if axis not in {"h", "v"}:
        app._set_status(f"Distribute: unknown axis {axis!r}.", ttl_sec=3.0)
        return

    if axis == "h":
        ordered = sorted(items, key=lambda t: (int(getattr(t[1], "x", 0) or 0), int(t[0])))
        first = ordered[0][1]
        last = ordered[-1][1]
        left = int(getattr(first, "x", 0) or 0)
        right = int(getattr(last, "x", 0) or 0) + max(
            GRID, int(getattr(last, "width", GRID) or GRID)
        )
        total = sum(max(GRID, int(getattr(w, "width", GRID) or GRID)) for _i, w in ordered)
        gap = float(right - left - total) / float(max(1, len(ordered) - 1))
        cursor = float(left)

        try:
            app.designer._save_state()
        except Exception:
            pass

        for pos, (_idx, w) in enumerate(ordered):
            ww = max(GRID, int(getattr(w, "width", GRID) or GRID))
            if pos == 0:
                nx = left
            elif pos == len(ordered) - 1:
                nx = right - ww
            else:
                prev_w = max(GRID, int(getattr(ordered[pos - 1][1], "width", GRID) or GRID))
                cursor += float(prev_w) + gap
                nx = round(cursor)
            ny = int(getattr(w, "y", 0) or 0)
            nx, ny = _clamp_xy_in_scene(app, nx, ny, w)
            w.x = nx
            w.y = ny
    else:
        ordered = sorted(items, key=lambda t: (int(getattr(t[1], "y", 0) or 0), int(t[0])))
        first = ordered[0][1]
        last = ordered[-1][1]
        top = int(getattr(first, "y", 0) or 0)
        bottom = int(getattr(last, "y", 0) or 0) + max(
            GRID, int(getattr(last, "height", GRID) or GRID)
        )
        total = sum(max(GRID, int(getattr(w, "height", GRID) or GRID)) for _i, w in ordered)
        gap = float(bottom - top - total) / float(max(1, len(ordered) - 1))
        cursor = float(top)

        try:
            app.designer._save_state()
        except Exception:
            pass

        for pos, (_idx, w) in enumerate(ordered):
            wh = max(GRID, int(getattr(w, "height", GRID) or GRID))
            if pos == 0:
                ny = top
            elif pos == len(ordered) - 1:
                ny = bottom - wh
            else:
                prev_h = max(GRID, int(getattr(ordered[pos - 1][1], "height", GRID) or GRID))
                cursor += float(prev_h) + gap
                ny = round(cursor)
            nx = int(getattr(w, "x", 0) or 0)
            nx, ny = _clamp_xy_in_scene(app, nx, ny, w)
            w.x = nx
            w.y = ny

    app._set_status(f"Distributed {'horizontally' if axis == 'h' else 'vertically'}.", ttl_sec=2.5)
    app._mark_dirty()


def match_size_selection(app, mode: str) -> None:
    """Match width/height of selection to the anchor (selected_idx)."""
    items = _selected_widgets(app)
    if len(items) < 2:
        app._set_status("Match size: select 2+ widgets.", ttl_sec=2.5)
        return
    mode = str(mode or "").strip().lower()
    if mode not in {"width", "height"}:
        app._set_status(f"Match size: unknown mode {mode!r}.", ttl_sec=3.0)
        return

    sc = app.state.current_scene()
    anchor = getattr(app.state, "selected_idx", None)
    if anchor is None:
        anchor = items[0][0]
    try:
        anchor_i = int(anchor)
    except Exception:
        anchor_i = items[0][0]
    if not (0 <= anchor_i < len(sc.widgets)):
        anchor_i = items[0][0]
    ref = sc.widgets[int(anchor_i)]
    ref_w = max(GRID, int(getattr(ref, "width", GRID) or GRID))
    ref_h = max(GRID, int(getattr(ref, "height", GRID) or GRID))

    saved = False
    changed = 0
    skipped_locked = 0

    for idx, w in items:
        if idx == anchor_i:
            continue
        if bool(getattr(w, "locked", False)):
            skipped_locked += 1
            continue
        cur_w = max(GRID, int(getattr(w, "width", GRID) or GRID))
        cur_h = max(GRID, int(getattr(w, "height", GRID) or GRID))
        new_w = cur_w
        new_h = cur_h
        if mode == "width":
            new_w = ref_w
        else:
            new_h = ref_h
        if bool(getattr(app, "snap_enabled", True)):
            new_w = max(GRID, snap(int(new_w)))
            new_h = max(GRID, snap(int(new_h)))

        max_w = max(GRID, int(sc.width) - int(getattr(w, "x", 0) or 0))
        max_h = max(GRID, int(sc.height) - int(getattr(w, "y", 0) or 0))
        new_w = max(GRID, min(int(max_w), int(new_w)))
        new_h = max(GRID, min(int(max_h), int(new_h)))

        if (cur_w, cur_h) == (new_w, new_h):
            continue
        if not saved:
            try:
                app.designer._save_state()
            except Exception:
                pass
            saved = True
        w.width = int(new_w)
        w.height = int(new_h)
        changed += 1

    if changed:
        msg = f"Match {mode}: updated {changed} widget(s)."
        if skipped_locked:
            msg += f" Skipped locked: {skipped_locked}."
        app._set_status(msg, ttl_sec=2.5)
        app._mark_dirty()
    else:
        if skipped_locked:
            app._set_status(
                f"Match {mode}: nothing to change (locked: {skipped_locked}).", ttl_sec=2.5
            )
        else:
            app._set_status(f"Match {mode}: nothing to change.", ttl_sec=2.0)


def center_selection_in_scene(app, axis: str = "both") -> None:
    """Center selection bounds inside the scene."""
    items = _selected_widgets(app)
    if not items:
        app._set_status("Center: no selection.", ttl_sec=2.0)
        return
    if _any_locked(items):
        app._set_status("Center: selection contains locked widget(s).", ttl_sec=3.0)
        return
    axis = str(axis or "both").strip().lower()
    if axis not in {"x", "y", "both"}:
        axis = "both"

    sc_w, sc_h = _scene_size(app)
    bounds = app._selection_bounds([i for i, _w in items])
    if bounds is None:
        return
    dx = 0
    dy = 0
    if axis in {"x", "both"}:
        dx = int((sc_w // 2) - int(bounds.centerx))
    if axis in {"y", "both"}:
        dy = int((sc_h // 2) - int(bounds.centery))
    app._move_selection(dx, dy)
    app._set_status("Centered selection.", ttl_sec=2.0)


def clear_active_guides(app) -> None:
    try:
        app.state.active_guides = []
    except Exception:
        pass


def snap_drag_to_guides(
    app, desired_x: int, desired_y: int, bounds: pygame.Rect
) -> Tuple[int, int]:
    """Snap a moving selection bounds to nearby guides.

    Returns adjusted (x,y) in scene coordinates and updates `state.active_guides`.
    """
    sc = app.state.current_scene()
    sc_w = int(getattr(sc, "width", 0) or 0)
    sc_h = int(getattr(sc, "height", 0) or 0)

    sel = {int(i) for i in (getattr(app.state, "selected", []) or []) if str(i).isdigit()}

    x_edges: List[int] = [0, sc_w]
    x_centers: List[int] = [sc_w // 2]
    y_edges: List[int] = [0, sc_h]
    y_centers: List[int] = [sc_h // 2]

    for i, w in enumerate(getattr(sc, "widgets", []) or []):
        if i in sel:
            continue
        if not bool(getattr(w, "visible", True)):
            continue
        try:
            wx = int(getattr(w, "x", 0) or 0)
            wy = int(getattr(w, "y", 0) or 0)
            ww = max(GRID, int(getattr(w, "width", GRID) or GRID))
            wh = max(GRID, int(getattr(w, "height", GRID) or GRID))
        except Exception:
            continue
        x_edges.extend([wx, wx + ww])
        x_centers.append(wx + ww // 2)
        y_edges.extend([wy, wy + wh])
        y_centers.append(wy + wh // 2)

    tol = int(GUIDE_TOL)
    best_dx: Optional[int] = None
    best_dy: Optional[int] = None
    best_abs_dx = tol + 1
    best_abs_dy = tol + 1
    guides: List[Tuple[str, int]] = []

    cand_left = int(desired_x)
    cand_right = int(desired_x) + int(bounds.width)
    cand_cx = int(desired_x) + int(bounds.width) // 2
    cand_top = int(desired_y)
    cand_bottom = int(desired_y) + int(bounds.height)
    cand_cy = int(desired_y) + int(bounds.height) // 2

    for gx in x_edges:
        for cx in (cand_left, cand_right):
            d = int(gx - cx)
            if abs(d) <= tol and abs(d) < best_abs_dx:
                best_abs_dx = abs(d)
                best_dx = d
                guides = [("v", int(gx))]
    for gx in x_centers:
        d = int(gx - cand_cx)
        if abs(d) <= tol and abs(d) < best_abs_dx:
            best_abs_dx = abs(d)
            best_dx = d
            guides = [("v", int(gx))]

    for gy in y_edges:
        for cy in (cand_top, cand_bottom):
            d = int(gy - cy)
            if abs(d) <= tol and abs(d) < best_abs_dy:
                best_abs_dy = abs(d)
                best_dy = d
                # keep any x guide already chosen
                guides = [g for g in guides if g[0] == "v"] + [("h", int(gy))]
    for gy in y_centers:
        d = int(gy - cand_cy)
        if abs(d) <= tol and abs(d) < best_abs_dy:
            best_abs_dy = abs(d)
            best_dy = d
            guides = [g for g in guides if g[0] == "v"] + [("h", int(gy))]

    if best_dx is None and best_dy is None:
        try:
            app.state.active_guides = []
        except Exception:
            pass
        return desired_x, desired_y

    nx = int(desired_x) + int(best_dx or 0)
    ny = int(desired_y) + int(best_dy or 0)

    try:
        app.state.active_guides = guides
    except Exception:
        pass
    return nx, ny
