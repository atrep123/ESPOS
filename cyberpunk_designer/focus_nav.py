from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

import pygame

_ITEM_RE = re.compile(r"^(?P<root>[^.]+)\.item(?P<slot>\d+)(?:$|\.)")


@dataclass
class _SimWidgetSnapshot:
    text: str
    value: int
    enabled: bool
    visible: bool


@dataclass
class _SimListModel:
    count: int = 0
    active: int = 0
    offset: int = 0
    seed_labels: List[str] = field(default_factory=list)
    seed_values: List[str] = field(default_factory=list)
    has_value_cols: bool = False


def sim_runtime_reset(app) -> None:
    app._sim_listmodels = {}
    app._sim_runtime_snapshot = {}


def sim_runtime_restore(app) -> None:
    sc = app.state.current_scene()
    snapshot = getattr(app, "_sim_runtime_snapshot", {}) or {}
    if not snapshot:
        app._sim_listmodels = {}
        app._sim_runtime_snapshot = {}
        return

    for w in getattr(sc, "widgets", []) or []:
        wid = getattr(w, "_widget_id", None)
        if not wid or wid not in snapshot:
            continue
        snap = snapshot[wid]
        try:
            w.text = snap.text
            w.value = snap.value
            w.enabled = snap.enabled
            w.visible = snap.visible
        except Exception:
            continue

    app._sim_listmodels = {}
    app._sim_runtime_snapshot = {}


def _sim_snapshot_widget(app, w) -> None:
    wid = getattr(w, "_widget_id", None)
    if not wid:
        return
    snapshot = getattr(app, "_sim_runtime_snapshot", None)
    if snapshot is None:
        snapshot = {}
        app._sim_runtime_snapshot = snapshot
    if wid in snapshot:
        return
    snapshot[wid] = _SimWidgetSnapshot(
        text=str(getattr(w, "text", "") or ""),
        value=int(getattr(w, "value", 0) or 0),
        enabled=bool(getattr(w, "enabled", True)),
        visible=bool(getattr(w, "visible", True)),
    )


def _find_by_widget_id(sc, widget_id: str) -> Optional[int]:
    for idx, w in enumerate(getattr(sc, "widgets", []) or []):
        if getattr(w, "_widget_id", None) == widget_id:
            return int(idx)
    return None


def _count_item_slots(sc, root: str, limit: int = 32) -> int:
    count = 0
    for i in range(limit):
        if _find_by_widget_id(sc, f"{root}.item{i}") is None:
            break
        count += 1
    return count


def _parse_scroll_text(text: str) -> Optional[tuple[int, int]]:
    if not text:
        return None
    if "/" not in text:
        return None
    left, right = text.split("/", 1)
    try:
        a = int(left.strip())
        b = int(right.strip())
    except Exception:
        return None
    if b <= 0:
        return None
    a = max(1, min(a, b))
    return a - 1, b


def _listmodel_clamp(m: _SimListModel, visible_slots: int) -> None:
    if m.count <= 0 or visible_slots <= 0:
        m.count = max(0, int(m.count))
        m.active = 0
        m.offset = 0
        return

    m.active = max(0, min(int(m.active), m.count - 1))
    max_off = max(0, m.count - visible_slots)
    m.offset = max(0, min(int(m.offset), max_off))

    if m.active < m.offset:
        m.offset = m.active
    elif m.active >= m.offset + visible_slots:
        m.offset = m.active - visible_slots + 1

    max_off = max(0, m.count - visible_slots)
    m.offset = max(0, min(int(m.offset), max_off))


def _listmodel_move_active(m: _SimListModel, delta: int, visible_slots: int) -> bool:
    if m.count <= 0 or delta == 0:
        return False
    before = (m.active, m.offset)
    m.active = max(0, min(m.active + int(delta), m.count - 1))
    _listmodel_clamp(m, visible_slots)
    return before != (m.active, m.offset)


def _listmodel_item_text(m: _SimListModel, index: int) -> tuple[str, str]:
    if index < 0 or index >= m.count:
        return "", ""
    label = ""
    value = ""
    if index < len(m.seed_labels):
        label = str(m.seed_labels[index] or "")
    if index < len(m.seed_values):
        value = str(m.seed_values[index] or "")
    if not label:
        label = f"Item {index + 1}"
    return label, value


def _ensure_sim_listmodel(app, sc, root: str) -> Optional[_SimListModel]:
    models = getattr(app, "_sim_listmodels", None)
    if models is None:
        models = {}
        app._sim_listmodels = models
    if root in models:
        return models[root]

    visible = _count_item_slots(sc, root)
    if visible <= 0:
        return None

    scroll_idx = _find_by_widget_id(sc, f"{root}.scroll")
    active = 0
    count = visible
    if scroll_idx is not None:
        parsed = _parse_scroll_text(str(getattr(sc.widgets[scroll_idx], "text", "") or ""))
        if parsed is not None:
            active, count = parsed

    count = max(0, int(count))
    active = max(0, min(int(active), max(0, count - 1))) if count > 0 else 0

    has_value_cols = _find_by_widget_id(sc, f"{root}.item0.label") is not None

    seed_labels: List[str] = []
    seed_values: List[str] = []
    for i in range(min(visible, count)):
        if has_value_cols:
            label_idx = _find_by_widget_id(sc, f"{root}.item{i}.label")
            value_idx = _find_by_widget_id(sc, f"{root}.item{i}.value")
            seed_labels.append(str(getattr(sc.widgets[label_idx], "text", "") or "") if label_idx is not None else "")
            seed_values.append(str(getattr(sc.widgets[value_idx], "text", "") or "") if value_idx is not None else "")
        else:
            btn_idx = _find_by_widget_id(sc, f"{root}.item{i}")
            seed_labels.append(str(getattr(sc.widgets[btn_idx], "text", "") or "") if btn_idx is not None else "")
            seed_values.append("")

    m = _SimListModel(
        count=count,
        active=active,
        offset=0,
        seed_labels=seed_labels,
        seed_values=seed_values,
        has_value_cols=has_value_cols,
    )
    _listmodel_clamp(m, visible)
    models[root] = m
    return m


def _apply_sim_listmodel(app, sc, root: str, m: _SimListModel, visible: int) -> None:
    scroll_idx = _find_by_widget_id(sc, f"{root}.scroll")
    if scroll_idx is not None:
        sw = sc.widgets[scroll_idx]
        _sim_snapshot_widget(app, sw)
        sw.text = f"{m.active + 1}/{m.count}" if m.count > 0 else "0/0"

    for slot in range(visible):
        abs_idx = m.offset + slot
        btn_idx = _find_by_widget_id(sc, f"{root}.item{slot}")
        if btn_idx is None:
            continue
        btn = sc.widgets[btn_idx]
        _sim_snapshot_widget(app, btn)
        if 0 <= abs_idx < m.count:
            btn.enabled = True
            btn.visible = True
            btn.value = abs_idx
        else:
            btn.enabled = False
            btn.visible = True
            btn.value = 0

        label, value = _listmodel_item_text(m, abs_idx)
        if m.has_value_cols:
            label_idx = _find_by_widget_id(sc, f"{root}.item{slot}.label")
            if label_idx is not None:
                lw = sc.widgets[label_idx]
                _sim_snapshot_widget(app, lw)
                lw.text = label

            value_idx = _find_by_widget_id(sc, f"{root}.item{slot}.value")
            if value_idx is not None:
                vw = sc.widgets[value_idx]
                _sim_snapshot_widget(app, vw)
                vw.text = value
        else:
            btn.text = label


def _sim_try_scroll_list(app, direction: str) -> bool:
    if direction not in {"up", "down"}:
        return False
    sc = app.state.current_scene()
    idx = app.focus_idx
    if idx is None or not (0 <= int(idx) < len(sc.widgets)):
        return False

    wid = getattr(sc.widgets[int(idx)], "_widget_id", None)
    if not wid:
        return False
    m = _ITEM_RE.match(str(wid))
    if not m:
        return False

    root = m.group("root")
    slot = int(m.group("slot"))
    visible = _count_item_slots(sc, root)
    if visible <= 0:
        return False

    model = _ensure_sim_listmodel(app, sc, root)
    if model is None or model.count <= visible:
        return False

    model.active = max(0, min(model.offset + slot, model.count - 1))
    delta = -1 if direction == "up" else 1
    if not _listmodel_move_active(model, delta, visible):
        return False

    _apply_sim_listmodel(app, sc, root, model, visible)

    active_slot = max(0, min(model.active - model.offset, visible - 1))
    target_idx = _find_by_widget_id(sc, f"{root}.item{active_slot}")
    if target_idx is not None:
        set_focus(app, target_idx)
    return True


def is_widget_focusable(w) -> bool:
    if not bool(getattr(w, "visible", True)):
        return False
    if not bool(getattr(w, "enabled", True)):
        return False
    wtype = str(getattr(w, "type", "") or "").lower()
    return wtype in {"button", "checkbox", "radiobutton", "slider", "textbox"}


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
    except Exception:
        v, vmin, vmax = 0, 0, 100
    v = max(vmin, min(vmax, v + int(delta)))
    try:
        w.value = int(v)
    except Exception:
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
        except Exception:
            pass
        app._set_status(f"checkbox: {'on' if bool(getattr(w, 'checked', False)) else 'off'}", ttl_sec=1.2)
        app._mark_dirty()
        return

    if wtype == "slider":
        app.focus_edit_value = not app.focus_edit_value
        app._set_status(
            "slider: edit (Up/Down adjust, Enter done)" if app.focus_edit_value else "slider: focus",
            ttl_sec=2.0,
        )
        app._mark_dirty()
        return

    label = str(getattr(w, "text", "") or wtype)
    app._set_status(f"pressed: {label}", ttl_sec=1.2)
    app._mark_dirty()
