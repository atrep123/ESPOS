"""Visual-backend Logic Editor — attach events/rules to widgets & scenes.

A real, modal overlay (mirrors ``icon_palette.py`` structurally so the two
windows are consistent): browse and edit the selected widget's event
handlers (``on_press`` / ``on_change`` / ``on_focus``) and the current
scene's behavior ``rules`` (trigger -> action(s)).

Every mutation goes through the undo-safe ``safe_save_state`` path the
inspector uses, and the action/rule templates it inserts are deliberately
the *real, codegen-valid* shapes (``tools/ui_codegen.py`` compiles them to
working C and ``tools/validate_design.py`` accepts them) — so what you build
here round-trips save -> codegen -> firmware and actually runs. This is a
bounded but genuine editor, not a decorative shell.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import pygame

from .constants import GRID, PALETTE, safe_save_state, snap

# NOTE: ``draw_text_clipped`` is imported lazily inside ``draw_logic_editor``
# to break the logic_editor <-> drawing.frame import cycle (same pattern the
# icon palette uses).

_EVENT_KINDS = ("on_press", "on_change", "on_focus")
_TRIGGER_TYPES = ("boot", "timer", "gpio_in", "ble_recv", "lora_recv")
_ACTION_TYPES = (
    "toast",
    "set_scene",
    "set_widget",
    "set_var",
    "gpio_write",
    "start_timer",
    "stop_timer",
    "ble_send",
    "lora_send",
)


def _default_action(atype: str, app) -> Dict[str, Any]:
    """A real, codegen-valid default for *atype*.

    Values are chosen so the result validates and compiles immediately; the
    user refines specifics in the inspector / by re-cycling. References point
    at real scene/widget names where one is needed.
    """
    scene_names: List[str] = []
    try:
        scene_names = list(app.designer.scenes.keys())
    except (AttributeError, TypeError):
        pass
    a_scene = scene_names[0] if scene_names else "main"
    a_wid = ""
    try:
        sc = app.state.current_scene()
        for w in sc.widgets:
            wid = getattr(w, "_widget_id", None) or getattr(w, "id", None)
            if wid:
                a_wid = str(wid)
                break
    except (AttributeError, TypeError):
        pass

    if atype == "toast":
        return {"type": "toast", "text": "hello"}
    if atype == "set_scene":
        return {"type": "set_scene", "scene": a_scene}
    if atype == "set_widget":
        return {"type": "set_widget", "widget": a_wid or "widget_id",
                "prop": "value", "value": 0}
    if atype == "set_var":
        return {"type": "set_var", "var": "counter", "expr": "counter + 1"}
    if atype == "gpio_write":
        return {"type": "gpio_write", "pin": 2, "level": 1}
    if atype == "start_timer":
        return {"type": "start_timer", "timer_id": 0, "ms": 1000}
    if atype == "stop_timer":
        return {"type": "stop_timer", "timer_id": 0}
    if atype == "ble_send":
        return {"type": "ble_send", "bytes": "ping"}
    if atype == "lora_send":
        return {"type": "lora_send", "bytes": "ping"}
    return {"type": "toast", "text": "hello"}


def _default_rule(app) -> Dict[str, Any]:
    return {
        "name": "rule",
        "trigger": {"type": "boot"},
        "actions": [_default_action("toast", app)],
    }


def _state(app) -> dict:
    st = getattr(app, "_logic_editor", None)
    if not isinstance(st, dict):
        st = {"visible": False, "section": 0, "cursor": 0, "hitboxes": []}
        app._logic_editor = st
    return st


def _selected_widget(app):
    """Return the single selected WidgetConfig (or None)."""
    try:
        sc = app.state.current_scene()
        sel = list(getattr(app.state, "selected", []) or [])
        if len(sel) == 1 and 0 <= sel[0] < len(sc.widgets):
            return sc.widgets[sel[0]]
    except (AttributeError, TypeError, IndexError):
        pass
    return None


def _widget_id(w) -> str:
    return str(getattr(w, "_widget_id", None) or getattr(w, "id", None) or "")


def _ensure_events(w) -> Dict[str, List[Dict[str, Any]]]:
    ev = getattr(w, "events", None)
    if not isinstance(ev, dict):
        ev = {}
        w.events = ev
    return ev


def _scene_rules(app) -> List[Dict[str, Any]]:
    try:
        sc = app.state.current_scene()
    except (AttributeError, TypeError):
        return []
    r = getattr(sc, "rules", None)
    if not isinstance(r, list):
        r = []
        sc.rules = r
    return r


# Flat row model: list of (section, key, label) describing every editable
# line so the cursor / keyboard ops operate on real model objects.
def _rows(app) -> List[Tuple[str, Any, str]]:
    rows: List[Tuple[str, Any, str]] = []
    w = _selected_widget(app)
    if w is not None:
        wid = _widget_id(w) or "(no id — set one to wire events)"
        rows.append(("hdr", None, f"Widget events  [{wid}]"))
        ev = getattr(w, "events", {}) or {}
        for ek in _EVENT_KINDS:
            acts = ev.get(ek) if isinstance(ev, dict) else None
            if isinstance(acts, list) and acts:
                summary = " > ".join(str(a.get("type", "?")) for a in acts)
                rows.append(("event", ek, f"  {ek}: {summary}"))
    else:
        rows.append(("hdr", None, "Widget events  (select one widget)"))
    rows.append(("hdr", None, "Scene rules"))
    for i, r in enumerate(_scene_rules(app)):
        trig = (r.get("trigger") or {}).get("type", "?")
        acts = r.get("actions") or []
        summary = " > ".join(str(a.get("type", "?")) for a in acts)
        nm = r.get("name") or f"rule{i}"
        rows.append(("rule", i, f"  [{trig}] {nm}: {summary}"))
    return rows


def _selectable(rows: List[Tuple[str, Any, str]]) -> List[int]:
    return [i for i, r in enumerate(rows) if r[0] in ("event", "rule")]


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def open_logic_editor(app) -> None:
    st = _state(app)
    st["visible"] = True
    st["cursor"] = 0
    app._set_status(
        "Logic: A=add  E=cycle action  H=add handler  T=cycle trigger  "
        "R=add rule  Del=remove  Esc=close",
        ttl_sec=5.0,
    )
    app._mark_dirty()


def close_logic_editor(app) -> None:
    st = _state(app)
    if st.get("visible"):
        st["visible"] = False
        app._mark_dirty()


def is_open(app) -> bool:
    return bool(_state(app).get("visible"))


def toggle_logic_editor(app) -> None:
    if is_open(app):
        close_logic_editor(app)
    else:
        open_logic_editor(app)


def _focused(app):
    """Return (kind, obj) for the row under the cursor, or (None, None)."""
    rows = _rows(app)
    sel = _selectable(rows)
    if not sel:
        return None, None
    st = _state(app)
    cur = max(0, min(len(sel) - 1, int(st.get("cursor", 0))))
    st["cursor"] = cur
    kind, key, _label = rows[sel[cur]]
    return kind, key


def _add_handler(app) -> None:
    """Add the next unused event handler to the selected widget."""
    w = _selected_widget(app)
    if w is None:
        app._set_status("Select exactly one widget first.", ttl_sec=2.5)
        return
    if not _widget_id(w):
        app._set_status("Widget needs an id (set one in the inspector).", ttl_sec=3.0)
        return
    safe_save_state(app.designer)
    ev = _ensure_events(w)
    for ek in _EVENT_KINDS:
        if ek not in ev or not ev.get(ek):
            ev[ek] = [_default_action("toast", app)]
            app._set_status(f"Added {ek} handler.", ttl_sec=2.0)
            app._mark_dirty()
            return
    app._set_status("All three handlers already exist.", ttl_sec=2.5)


def _add_action(app) -> None:
    """Append a real action to the focused handler / rule."""
    kind, key = _focused(app)
    if kind is None:
        app._set_status("Nothing focused — add a handler (H) or rule (R).", ttl_sec=2.5)
        return
    safe_save_state(app.designer)
    if kind == "event":
        w = _selected_widget(app)
        if w is None:
            return
        ev = _ensure_events(w)
        ev.setdefault(key, []).append(_default_action("toast", app))
    else:  # rule
        rules = _scene_rules(app)
        if 0 <= key < len(rules):
            rules[key].setdefault("actions", []).append(_default_action("toast", app))
    app._set_status("Action appended (cycle type with E).", ttl_sec=2.0)
    app._mark_dirty()


def _cycle_action(app) -> None:
    """Cycle the LAST action's type on the focused handler/rule through the
    real vocabulary, re-defaulting its fields so it stays codegen-valid."""
    kind, key = _focused(app)
    if kind is None:
        return
    if kind == "event":
        w = _selected_widget(app)
        if w is None:
            return
        acts = (getattr(w, "events", {}) or {}).get(key) or []
    else:
        rules = _scene_rules(app)
        if not (0 <= key < len(rules)):
            return
        acts = rules[key].get("actions") or []
    if not acts:
        return
    cur_t = str(acts[-1].get("type", "toast"))
    nxt = _ACTION_TYPES[(_ACTION_TYPES.index(cur_t) + 1) % len(_ACTION_TYPES)] \
        if cur_t in _ACTION_TYPES else _ACTION_TYPES[0]
    safe_save_state(app.designer)
    acts[-1].clear()
    acts[-1].update(_default_action(nxt, app))
    app._set_status(f"Action -> {nxt}", ttl_sec=2.0)
    app._mark_dirty()


def _cycle_trigger(app) -> None:
    kind, key = _focused(app)
    if kind != "rule":
        app._set_status("Select a scene rule to cycle its trigger.", ttl_sec=2.5)
        return
    rules = _scene_rules(app)
    if not (0 <= key < len(rules)):
        return
    trig = rules[key].setdefault("trigger", {"type": "boot"})
    cur = str(trig.get("type", "boot"))
    nxt = _TRIGGER_TYPES[(_TRIGGER_TYPES.index(cur) + 1) % len(_TRIGGER_TYPES)] \
        if cur in _TRIGGER_TYPES else _TRIGGER_TYPES[0]
    safe_save_state(app.designer)
    new_trig: Dict[str, Any] = {"type": nxt}
    if nxt == "timer":
        new_trig["timer_id"] = 0
    elif nxt == "gpio_in":
        new_trig["pin"] = 0
        new_trig["edge"] = "any"
    rules[key]["trigger"] = new_trig
    app._set_status(f"Trigger -> {nxt}", ttl_sec=2.0)
    app._mark_dirty()


def _add_rule(app) -> None:
    safe_save_state(app.designer)
    _scene_rules(app).append(_default_rule(app))
    st = _state(app)
    rows = _rows(app)
    sel = _selectable(rows)
    st["cursor"] = max(0, len(sel) - 1)
    app._set_status("Scene rule added (boot -> toast).", ttl_sec=2.0)
    app._mark_dirty()


def _delete_focused(app) -> None:
    kind, key = _focused(app)
    if kind is None:
        return
    safe_save_state(app.designer)
    if kind == "event":
        w = _selected_widget(app)
        if w is None:
            return
        ev = _ensure_events(w)
        ev.pop(key, None)
        app._set_status(f"Removed {key} handler.", ttl_sec=2.0)
    else:
        rules = _scene_rules(app)
        if 0 <= key < len(rules):
            rules.pop(key)
            app._set_status("Removed scene rule.", ttl_sec=2.0)
    st = _state(app)
    st["cursor"] = max(0, int(st.get("cursor", 0)) - 1)
    app._mark_dirty()


def _move(app, delta: int) -> None:
    st = _state(app)
    rows = _rows(app)
    sel = _selectable(rows)
    if not sel:
        return
    st["cursor"] = max(0, min(len(sel) - 1, int(st.get("cursor", 0)) + delta))
    app._mark_dirty()


def handle_key(app, event: pygame.event.Event) -> bool:
    st = _state(app)
    if not st.get("visible"):
        return False
    key = event.key
    if key == pygame.K_ESCAPE:
        close_logic_editor(app)
        return True
    if key in (pygame.K_UP, pygame.K_LEFT):
        _move(app, -1)
        return True
    if key in (pygame.K_DOWN, pygame.K_RIGHT):
        _move(app, 1)
        return True
    if key == pygame.K_a:
        _add_action(app)
        return True
    if key == pygame.K_e:
        _cycle_action(app)
        return True
    if key == pygame.K_h:
        _add_handler(app)
        return True
    if key == pygame.K_t:
        _cycle_trigger(app)
        return True
    if key == pygame.K_r:
        _add_rule(app)
        return True
    if key in (pygame.K_DELETE, pygame.K_BACKSPACE):
        _delete_focused(app)
        return True
    # Modal: swallow everything else so global shortcuts don't fire.
    return True


def handle_click(app, pos: Tuple[int, int]) -> bool:
    st = _state(app)
    if not st.get("visible"):
        return False
    for rect, sel_idx in st.get("hitboxes", []):
        if rect.collidepoint(pos[0], pos[1]):
            st["cursor"] = sel_idx
            app._mark_dirty()
            return True
    close_logic_editor(app)
    return True


def handle_wheel(app, dy: int) -> bool:
    st = _state(app)
    if not st.get("visible"):
        return False
    _move(app, -dy)
    return True


# --------------------------------------------------------------------------- #
# Rendering — modeled on icon_palette.draw_icon_palette
# --------------------------------------------------------------------------- #
def draw_logic_editor(app) -> None:
    st = _state(app)
    if not st.get("visible"):
        return
    from .drawing.text import draw_text_clipped

    surface = getattr(app, "logical_surface", None)
    layout = getattr(app, "layout", None)
    if surface is None or layout is None:
        return
    w = int(getattr(layout, "width", 0) or 0)
    h = int(getattr(layout, "height", 0) or 0)
    if w <= 0 or h <= 0:
        return

    dim = pygame.Surface((w, h), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 170))
    surface.blit(dim, (0, 0))

    pad = max(2, int(getattr(app, "pixel_padding", 0) or 0))
    row_h = max(1, int(getattr(app, "pixel_row_height", 0) or 0))

    margin = GRID * 2
    panel_w = max(GRID * 24, min(w - margin * 2, GRID * 70))
    panel_h = max(GRID * 16, min(h - margin * 2, GRID * 46))
    panel_w = max(GRID * 16, snap(panel_w))
    panel_h = max(GRID * 12, snap(panel_h))
    x = snap((w - panel_w) // 2)
    y = snap((h - panel_h) // 2)
    panel_rect = pygame.Rect(x, y, panel_w, panel_h)
    pygame.draw.rect(surface, PALETTE["panel"], panel_rect)
    pygame.draw.rect(surface, PALETTE["panel_border"], panel_rect, 1)

    title_rect = pygame.Rect(x + pad, y + pad, panel_w - 2 * pad, row_h)
    draw_text_clipped(
        app, surface=surface, text="Logic Editor (events / rules)",
        rect=title_rect, fg=PALETTE["accent_yellow"], padding=0,
        align="left", valign="middle", max_lines=1, use_device_font=False,
    )
    draw_text_clipped(
        app, surface=surface, text="A add  E cycle  H +handler  T trig  R +rule  Del",
        rect=title_rect, fg=PALETTE["muted"], padding=0,
        align="right", valign="middle", max_lines=1, use_device_font=False,
    )

    rows = _rows(app)
    sel = _selectable(rows)
    cur = max(0, min(len(sel) - 1, int(st.get("cursor", 0)))) if sel else 0
    st["cursor"] = cur
    cur_row_idx = sel[cur] if sel else -1

    list_top = y + pad + row_h + pad
    list_rect = pygame.Rect(
        x + pad, list_top, panel_w - 2 * pad, (y + panel_h - pad - row_h) - list_top
    )
    hitboxes: List[Tuple[pygame.Rect, int]] = []
    if list_rect.height > 0:
        max_rows = max(1, list_rect.height // row_h)
        # Scroll so the cursor row stays visible.
        start = 0
        if cur_row_idx >= max_rows:
            start = cur_row_idx - max_rows + 1
        for vi, ri in enumerate(range(start, min(len(rows), start + max_rows))):
            kind, _key, label = rows[ri]
            rr = pygame.Rect(list_rect.x, list_top + vi * row_h, list_rect.width, row_h)
            if kind == "hdr":
                fg = PALETTE["accent_cyan"]
            elif ri == cur_row_idx:
                pygame.draw.rect(surface, PALETTE["selection"], rr, 1)
                fg = PALETTE["text"]
            else:
                fg = PALETTE["muted"]
            draw_text_clipped(
                app, surface=surface, text=label, rect=pygame.Rect(
                    rr.x + pad, rr.y, rr.width - 2 * pad, row_h
                ), fg=fg, padding=0, align="left", valign="middle",
                max_lines=1, use_device_font=False,
            )
            if kind in ("event", "rule"):
                hitboxes.append((rr, sel.index(ri)))
    st["hitboxes"] = hitboxes

    n_ev = sum(1 for r in rows if r[0] == "event")
    n_rule = sum(1 for r in rows if r[0] == "rule")
    foot_rect = pygame.Rect(x + pad, y + panel_h - row_h, panel_w - 2 * pad, row_h)
    draw_text_clipped(
        app, surface=surface,
        text=f"{n_ev} handler(s), {n_rule} rule(s)  -  compiles to firmware C",
        rect=foot_rect, fg=PALETTE["muted"], padding=0,
        align="left", valign="middle", max_lines=1, use_device_font=False,
    )
