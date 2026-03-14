"""Simulation-specific list model helpers for focus navigation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional

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
        except AttributeError:
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
    except (ValueError, TypeError):
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
            seed_labels.append(
                str(getattr(sc.widgets[label_idx], "text", "") or "")
                if label_idx is not None
                else ""
            )
            seed_values.append(
                str(getattr(sc.widgets[value_idx], "text", "") or "")
                if value_idx is not None
                else ""
            )
        else:
            btn_idx = _find_by_widget_id(sc, f"{root}.item{i}")
            seed_labels.append(
                str(getattr(sc.widgets[btn_idx], "text", "") or "") if btn_idx is not None else ""
            )
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


def sim_try_scroll_list(app, direction: str, set_focus_fn: Callable) -> bool:
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
        set_focus_fn(app, target_idx)
    return True
