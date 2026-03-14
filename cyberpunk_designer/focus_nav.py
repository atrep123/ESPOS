"""D-pad / encoder focus navigation simulation."""

from __future__ import annotations

from typing import List, Optional

import pygame

from . import focus_nav_sim as sim

_SimListModel = sim._SimListModel
_SimWidgetSnapshot = sim._SimWidgetSnapshot
_apply_sim_listmodel = sim._apply_sim_listmodel
_count_item_slots = sim._count_item_slots
_ensure_sim_listmodel = sim._ensure_sim_listmodel
_find_by_widget_id = sim._find_by_widget_id
_listmodel_clamp = sim._listmodel_clamp
_listmodel_item_text = sim._listmodel_item_text
_listmodel_move_active = sim._listmodel_move_active
_parse_scroll_text = sim._parse_scroll_text
_sim_snapshot_widget = sim._sim_snapshot_widget
sim_runtime_reset = sim.sim_runtime_reset
sim_runtime_restore = sim.sim_runtime_restore


def _sim_try_scroll_list(app, direction: str) -> bool:
    return sim.sim_try_scroll_list(app, direction, set_focus)


def is_widget_focusable(w) -> bool:
    if not bool(getattr(w, "visible", True)):
        return False
    if not bool(getattr(w, "enabled", True)):
        return False
    wtype = str(getattr(w, "type", "") or "").lower()
    return wtype in {
        "button", "checkbox", "radiobutton", "slider", "textbox",
        "list", "toggle", "gauge", "progressbar",
    }


def focusable_indices(sc) -> List[int]:
    out: List[int] = []
    for idx, w in enumerate(getattr(sc, "widgets", []) or []):
        if is_widget_focusable(w):
            out.append(int(idx))
    out.sort(
        key=lambda i: (
            int(getattr(sc.widgets[i], "y", 0) or 0),
            int(getattr(sc.widgets[i], "x", 0) or 0),
            i,
        )
    )
    return out


def set_focus(app, idx: Optional[int], *, sync_selection: bool = True) -> None:
    sc = app.state.current_scene()
    if idx is None or not (0 <= int(idx) < len(sc.widgets)):
        app.focus_idx = None
        app.focus_edit_value = False
        return
    i = int(idx)
    if not is_widget_focusable(sc.widgets[i]):
        return
    app.focus_idx = i
    app.focus_edit_value = False
    if sync_selection:
        app._set_selection([i], anchor_idx=i)


def ensure_focus(app) -> None:
    sc = app.state.current_scene()
    if app.focus_idx is not None and 0 <= int(app.focus_idx) < len(sc.widgets):
        if is_widget_focusable(sc.widgets[int(app.focus_idx)]):
            return
    if app.state.selected_idx is not None and 0 <= int(app.state.selected_idx) < len(sc.widgets):
        if is_widget_focusable(sc.widgets[int(app.state.selected_idx)]):
            set_focus(app, int(app.state.selected_idx), sync_selection=False)
            return
    focusables = focusable_indices(sc)
    if focusables:
        set_focus(app, focusables[0], sync_selection=False)
    else:
        app.focus_idx = None
        app.focus_edit_value = False


def focus_cycle(app, delta: int) -> None:
    focusables = focusable_indices(app.state.current_scene())
    if not focusables:
        set_focus(app, None)
        return
    ensure_focus(app)
    cur = app.focus_idx
    if cur is None or cur not in focusables:
        set_focus(app, focusables[0])
        return
    pos = focusables.index(cur)
    nxt = focusables[(pos + (1 if delta >= 0 else -1)) % len(focusables)]
    set_focus(app, nxt)


def focus_move_direction(app, direction: str) -> None:
    """Move focus based on widget geometry (D-pad style)."""
    ensure_focus(app)
    if getattr(app, "sim_input_mode", False) and _sim_try_scroll_list(app, direction):
        return
    sc = app.state.current_scene()
    cur = app.focus_idx
    if cur is None:
        return
    focusables = focusable_indices(sc)
    if len(focusables) <= 1:
        return

    cw = sc.widgets[cur]
    cr = pygame.Rect(int(cw.x), int(cw.y), int(cw.width), int(cw.height))
    cx, cy = cr.center

    beam_idx: Optional[int] = None
    beam_score: Optional[int] = None
    loose_idx: Optional[int] = None
    loose_score: Optional[int] = None
    for idx in focusables:
        if idx == cur:
            continue
        w = sc.widgets[idx]
        r = pygame.Rect(int(w.x), int(w.y), int(w.width), int(w.height))
        tx, ty = r.center
        dx = int(tx - cx)
        dy = int(ty - cy)
        if direction == "up" and dy >= 0:
            continue
        if direction == "down" and dy <= 0:
            continue
        if direction == "left" and dx >= 0:
            continue
        if direction == "right" and dx <= 0:
            continue

        vertical = direction in {"up", "down"}

        primary = abs(dy) if vertical else abs(dx)
        secondary = abs(dx) if vertical else abs(dy)
        dist2 = (dx * dx) + (dy * dy)

        if vertical:
            overlap = min(cr.right, r.right) - max(cr.left, r.left)
            if overlap > 0:
                score = int(primary * 10_000 + secondary * 100 + dist2)
                if beam_score is None or score < beam_score:
                    beam_score = score
                    beam_idx = idx
            else:
                if r.right <= cr.left:
                    gap = cr.left - r.right
                elif r.left >= cr.right:
                    gap = r.left - cr.right
                else:  # pragma: no cover — requires zero-width widget
                    gap = 0
                score = int(1_000_000 + gap * 10_000 + primary * 10_000 + secondary * 100 + dist2)
                if loose_score is None or score < loose_score:
                    loose_score = score
                    loose_idx = idx
        else:
            overlap = min(cr.bottom, r.bottom) - max(cr.top, r.top)
            if overlap > 0:
                score = int(primary * 10_000 + secondary * 100 + dist2)
                if beam_score is None or score < beam_score:
                    beam_score = score
                    beam_idx = idx
            else:
                if r.bottom <= cr.top:
                    gap = cr.top - r.bottom
                elif r.top >= cr.bottom:
                    gap = r.top - cr.bottom
                else:  # pragma: no cover — requires zero-height widget
                    gap = 0
                score = int(1_000_000 + gap * 10_000 + primary * 10_000 + secondary * 100 + dist2)
                if loose_score is None or score < loose_score:
                    loose_score = score
                    loose_idx = idx

    best_idx = beam_idx if beam_idx is not None else loose_idx
    if best_idx is None:
        focus_cycle(app, 1 if direction in {"down", "right"} else -1)
        return
    set_focus(app, best_idx)


def adjust_focused_value(app, delta: int) -> None:
    ensure_focus(app)
    sc = app.state.current_scene()
    idx = app.focus_idx
    if idx is None or not (0 <= idx < len(sc.widgets)):
        return
    w = sc.widgets[idx]
    wtype = str(getattr(w, "type", "") or "").lower()
    if wtype not in {"slider"}:
        return
    try:
        v = int(getattr(w, "value", 0) or 0)
        vmin = int(getattr(w, "min_value", 0) or 0)
        vmax = int(getattr(w, "max_value", 100) or 100)
    except (ValueError, TypeError):
        v, vmin, vmax = 0, 0, 100
    v = max(vmin, min(vmax, v + int(delta)))
    try:
        w.value = int(v)
    except (ValueError, AttributeError):
        return
    app._set_status(f"slider value: {v}", ttl_sec=1.2)
    app._mark_dirty()


def activate_focused(app) -> None:
    """Simulate device 'OK/press' on the focused widget."""
    ensure_focus(app)
    sc = app.state.current_scene()
    idx = app.focus_idx
    if idx is None or not (0 <= idx < len(sc.widgets)):
        return
    w = sc.widgets[idx]
    wtype = str(getattr(w, "type", "") or "").lower()

    if wtype == "checkbox":
        try:
            w.checked = not bool(getattr(w, "checked", False))
        except AttributeError:
            pass
        app._set_status(
            f"checkbox: {'on' if bool(getattr(w, 'checked', False)) else 'off'}", ttl_sec=1.2
        )
        app._mark_dirty()
        return

    if wtype == "slider":
        app.focus_edit_value = not app.focus_edit_value
        app._set_status(
            "slider: edit (Up/Down adjust, Enter done)"
            if app.focus_edit_value
            else "slider: focus",
            ttl_sec=2.0,
        )
        app._mark_dirty()
        return

    label = str(getattr(w, "text", "") or wtype)
    app._set_status(f"pressed: {label}", ttl_sec=1.2)
    app._mark_dirty()
