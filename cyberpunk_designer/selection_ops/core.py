"""Core selection management and common helpers."""

from __future__ import annotations

import logging
from typing import List, Optional

import pygame

from ..constants import GRID, safe_save_state

logger = logging.getLogger(__name__)


def save_undo(app, *, log: bool = False) -> None:
    """Save an undo checkpoint.  Call immediately before mutating state."""
    try:
        safe_save_state(app.designer)
    except AttributeError as exc:
        if log:
            logger.warning("Failed to save undo state: %s", exc)


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

    # Shift+click: range select from anchor to hit
    if mods & pygame.KMOD_SHIFT:
        anchor = app.state.selected_idx
        if anchor is not None:
            lo, hi = min(anchor, hit), max(anchor, hit)
            set_selection(app, list(range(lo, hi + 1)), anchor_idx=anchor)
        else:
            set_selection(app, [hit], anchor_idx=hit)
        return

    if not (mods & pygame.KMOD_ALT):
        gname = app._primary_group_for_index(hit)
        if gname:
            members = app._group_members(gname)
            if members:
                set_selection(app, members, anchor_idx=hit)
                return

    set_selection(app, [hit], anchor_idx=hit)


def delete_selected(app) -> None:
    """Delete selected widgets."""
    if not app.state.selected:
        return
    save_undo(app, log=True)
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
        except (AttributeError, IndexError) as exc:
            logger.warning("Reindex after delete failed at %d: %s", idx, exc)
    app.state.selected = []
    app.state.selected_idx = None
    if skipped:
        app._set_status(f"Delete: skipped {skipped} locked widget(s).", ttl_sec=3.0)
    app._mark_dirty()
