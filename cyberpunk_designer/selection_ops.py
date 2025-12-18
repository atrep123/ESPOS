from __future__ import annotations

from dataclasses import asdict
from typing import List, Optional

import pygame

from ui_designer import WidgetConfig

from .constants import GRID, snap


def set_selection(app, indices: List[int], anchor_idx: Optional[int] = None) -> None:
    sc = app.state.current_scene()
    valid = [int(i) for i in indices if 0 <= int(i) < len(sc.widgets)]
    if not valid:
        app.state.selected = []
        app.state.selected_idx = None
        app.designer.selected_widget = None
        return
    unique = sorted(set(valid))
    app.state.selected = unique
    app.state.selected_idx = anchor_idx if anchor_idx in unique else unique[0]
    app.designer.selected_widget = app.state.selected_idx


def selection_bounds(app, indices: List[int]) -> Optional[pygame.Rect]:
    sc = app.state.current_scene()
    rects: List[pygame.Rect] = []
    for idx in indices:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        ww = max(GRID, int(getattr(w, "width", GRID) or GRID))
        wh = max(GRID, int(getattr(w, "height", GRID) or GRID))
        wx = int(getattr(w, "x", 0) or 0)
        wy = int(getattr(w, "y", 0) or 0)
        rects.append(pygame.Rect(wx, wy, ww, wh))
    if not rects:
        return None
    min_x = min(r.x for r in rects)
    min_y = min(r.y for r in rects)
    max_x = max(r.right for r in rects)
    max_y = max(r.bottom for r in rects)
    return pygame.Rect(min_x, min_y, max(1, max_x - min_x), max(1, max_y - min_y))


def apply_click_selection(app, hit: int, mods: int) -> None:
    """Apply selection semantics for a clicked widget index."""
    if mods & pygame.KMOD_CTRL:
        if hit in app.state.selected:
            remaining = [i for i in app.state.selected if i != hit]
            set_selection(app, remaining, anchor_idx=remaining[-1] if remaining else None)
        else:
            set_selection(app, [*app.state.selected, hit], anchor_idx=hit)
        return

    if not (mods & pygame.KMOD_ALT):
        gname = app._primary_group_for_index(hit)
        if gname:
            members = app._group_members(gname)
            if members:
                set_selection(app, members, anchor_idx=hit)
                return

    set_selection(app, [hit], anchor_idx=hit)


def move_selection(app, dx: int, dy: int) -> None:
    if not app.state.selected:
        return
    sc = app.state.current_scene()
    if any(
        bool(getattr(sc.widgets[i], "locked", False))
        for i in app.state.selected
        if 0 <= i < len(sc.widgets)
    ):
        app._set_status("Selection contains locked widget(s).", ttl_sec=2.0)
        return
    bounds = selection_bounds(app, app.state.selected)
    if bounds is None:
        return
    new_x = int(bounds.x) + int(dx)
    new_y = int(bounds.y) + int(dy)
    if app.snap_enabled:
        new_x = snap(new_x)
        new_y = snap(new_y)
    max_x = max(0, int(sc.width) - int(bounds.width))
    max_y = max(0, int(sc.height) - int(bounds.height))
    new_x = max(0, min(max_x, new_x))
    new_y = max(0, min(max_y, new_y))
    if app.snap_enabled:
        new_x = snap(new_x)
        new_y = snap(new_y)
        new_x = max(0, min(max_x, new_x))
        new_y = max(0, min(max_y, new_y))
    ddx = int(new_x - int(bounds.x))
    ddy = int(new_y - int(bounds.y))
    if ddx == 0 and ddy == 0:
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        w.x = int(getattr(w, "x", 0) or 0) + ddx
        w.y = int(getattr(w, "y", 0) or 0) + ddy
    app._mark_dirty()


def resize_selection_to(app, new_w: int, new_h: int) -> bool:
    """Resize the current selection bounding box, scaling children proportionally."""
    if not app.state.selected:
        return False
    sc = app.state.current_scene()
    if any(
        bool(getattr(sc.widgets[i], "locked", False))
        for i in app.state.selected
        if 0 <= i < len(sc.widgets)
    ):
        app._set_status("Selection contains locked widget(s).", ttl_sec=2.0)
        return False

    bounds = selection_bounds(app, app.state.selected)
    if bounds is None:
        return False

    new_w = int(new_w)
    new_h = int(new_h)
    if app.snap_enabled:
        new_w = max(GRID, snap(new_w))
        new_h = max(GRID, snap(new_h))
    else:
        new_w = max(GRID, new_w)
        new_h = max(GRID, new_h)

    max_w = max(GRID, int(sc.width) - int(bounds.x))
    max_h = max(GRID, int(sc.height) - int(bounds.y))
    new_w = max(GRID, min(max_w, new_w))
    new_h = max(GRID, min(max_h, new_h))

    if int(bounds.width) <= 0 or int(bounds.height) <= 0:
        return False

    try:
        sx = float(new_w) / float(int(bounds.width))
        sy = float(new_h) / float(int(bounds.height))
    except Exception:
        sx, sy = 1.0, 1.0

    try:
        app.designer._save_state()
    except Exception:
        pass

    for idx in app.state.selected:
        if not (0 <= idx < len(sc.widgets)):
            continue
        w = sc.widgets[idx]
        ox = int(getattr(w, "x", 0) or 0)
        oy = int(getattr(w, "y", 0) or 0)
        ow = max(GRID, int(getattr(w, "width", GRID) or GRID))
        oh = max(GRID, int(getattr(w, "height", GRID) or GRID))

        rel_x = float(ox - int(bounds.x))
        rel_y = float(oy - int(bounds.y))
        nx = float(int(bounds.x)) + rel_x * sx
        ny = float(int(bounds.y)) + rel_y * sy
        nw = float(ow) * sx
        nh = float(oh) * sy

        ix = int(round(nx))
        iy = int(round(ny))
        iw = max(GRID, int(round(nw)))
        ih = max(GRID, int(round(nh)))
        if app.snap_enabled:
            ix = snap(ix)
            iy = snap(iy)
            iw = max(GRID, snap(iw))
            ih = max(GRID, snap(ih))

        max_ix = max(0, int(sc.width) - iw)
        max_iy = max(0, int(sc.height) - ih)
        ix = max(0, min(max_ix, ix))
        iy = max(0, min(max_iy, iy))

        w.x = ix
        w.y = iy
        w.width = iw
        w.height = ih

    app._mark_dirty()
    return True


def delete_selected(app) -> None:
    """Delete selected widgets."""
    if not app.state.selected:
        return
    try:
        app.designer._save_state()
    except Exception:
        pass
    sc = app.state.current_scene()
    skipped = 0
    for idx in sorted(app.state.selected, reverse=True):
        if not (0 <= idx < len(sc.widgets)):
            continue
        if bool(getattr(sc.widgets[idx], "locked", False)):
            skipped += 1
            continue
        del sc.widgets[idx]
        try:
            app.designer._reindex_after_delete(idx)
        except Exception:
            pass
    app.state.selected = []
    app.state.selected_idx = None
    if skipped:
        app._set_status(f"Delete: skipped {skipped} locked widget(s).", ttl_sec=3.0)
    app._mark_dirty()


def copy_selection(app) -> None:
    sc = app.state.current_scene()
    if not app.state.selected:
        app._set_status("Copy: nothing selected.", ttl_sec=2.0)
        return
    copied: List[WidgetConfig] = []
    for idx in app.state.selected:
        if 0 <= idx < len(sc.widgets):
            try:
                copied.append(WidgetConfig(**asdict(sc.widgets[idx])))
            except Exception:
                continue
    app.clipboard = copied
    app._set_status(f"Copied {len(copied)} widget(s).", ttl_sec=2.0)


def paste_clipboard(app) -> None:
    if not app.clipboard:
        app._set_status("Paste: clipboard empty.", ttl_sec=2.0)
        return

    sc = app.state.current_scene()
    try:
        app.designer._save_state()
    except Exception:
        pass

    min_x = min(int(w.x) for w in app.clipboard)
    min_y = min(int(w.y) for w in app.clipboard)

    dx = GRID * 2
    dy = GRID * 2
    sr = getattr(app, "scene_rect", None)
    if sr is None or not hasattr(sr, "collidepoint"):
        sr = app.layout.canvas_rect
    if sr.collidepoint(app.pointer_pos):
        try:
            dx = int(app.pointer_pos[0] - sr.x) - min_x
            dy = int(app.pointer_pos[1] - sr.y) - min_y
        except Exception:
            dx, dy = GRID * 2, GRID * 2

    new_indices: List[int] = []
    for w in app.clipboard:
        try:
            nw = WidgetConfig(**asdict(w))
        except Exception:
            continue
        nw.x = int(nw.x + dx)
        nw.y = int(nw.y + dy)
        if app.snap_enabled:
            nw.x = snap(int(nw.x))
            nw.y = snap(int(nw.y))
        max_x = max(0, int(sc.width) - int(nw.width))
        max_y = max(0, int(sc.height) - int(nw.height))
        nw.x = max(0, min(max_x, int(nw.x)))
        nw.y = max(0, min(max_y, int(nw.y)))
        sc.widgets.append(nw)
        new_indices.append(len(sc.widgets) - 1)

    app.state.selected = new_indices
    app.state.selected_idx = new_indices[0] if new_indices else None
    app.designer.selected_widget = app.state.selected_idx
    app._set_status(f"Pasted {len(new_indices)} widget(s).", ttl_sec=2.0)


def cut_selection(app) -> None:
    if not app.state.selected:
        app._set_status("Cut: nothing selected.", ttl_sec=2.0)
        return
    copy_selection(app)
    delete_selected(app)
    app._set_status("Cut.", ttl_sec=2.0)


def duplicate_selection(app) -> None:
    if not app.state.selected:
        app._set_status("Duplicate: nothing selected.", ttl_sec=2.0)
        return
    copy_selection(app)
    paste_clipboard(app)
    app._set_status("Duplicated.", ttl_sec=2.0)


def select_all(app) -> None:
    sc = app.state.current_scene()
    if not sc.widgets:
        app._set_status("Select all: empty scene.", ttl_sec=2.0)
        return
    app.state.selected = list(range(len(sc.widgets)))
    app.state.selected_idx = app.state.selected[0] if app.state.selected else None
    app.designer.selected_widget = app.state.selected_idx
    app._set_status(f"Selected {len(app.state.selected)} widget(s).", ttl_sec=2.0)
