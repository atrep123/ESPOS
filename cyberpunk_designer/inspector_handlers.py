"""Inspector special-field handler functions."""

from __future__ import annotations

import pygame

from .constants import safe_save_state
from .inspector_values import _commit_epilogue, _parse_pair


def _handle_position(app) -> bool:
    raw = app.state.inspector_input_buffer
    pair = _parse_pair(raw.strip())
    if pair is None:
        app._set_status("Format: X,Y (e.g. 10,20)", ttl_sec=3.0)
        return False
    nx, ny = pair
    selection = app.state.selection_list()
    if not selection:
        app._inspector_cancel_edit()
        return True
    safe_save_state(app.designer)
    sc = app.state.current_scene()
    for idx in selection:
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].x = nx
            sc.widgets[idx].y = ny
    return _commit_epilogue(app, f"Position: {nx},{ny}")


def _handle_padding(app) -> bool:
    raw = app.state.inspector_input_buffer
    pair = _parse_pair(raw.strip())
    if pair is None:
        app._set_status("Format: Px,Py (e.g. 2,1)", ttl_sec=3.0)
        return False
    px, py = pair
    if px < 0 or py < 0:
        app._set_status("Padding must be \u2265 0.", ttl_sec=3.0)
        return False
    selection = app.state.selection_list()
    if not selection:
        app._inspector_cancel_edit()
        return True
    safe_save_state(app.designer)
    sc = app.state.current_scene()
    for idx in selection:
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].padding_x = px
            sc.widgets[idx].padding_y = py
    return _commit_epilogue(app, f"Padding: {px},{py}")


def _handle_margin(app) -> bool:
    raw = app.state.inspector_input_buffer
    pair = _parse_pair(raw.strip())
    if pair is None:
        app._set_status("Format: Mx,My (e.g. 2,1)", ttl_sec=3.0)
        return False
    mx, my = pair
    if mx < 0 or my < 0:
        app._set_status("Margin must be \u2265 0.", ttl_sec=3.0)
        return False
    selection = app.state.selection_list()
    if not selection:
        app._inspector_cancel_edit()
        return True
    safe_save_state(app.designer)
    sc = app.state.current_scene()
    for idx in selection:
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].margin_x = mx
            sc.widgets[idx].margin_y = my
    return _commit_epilogue(app, f"Margin: {mx},{my}")


def _handle_search(app) -> bool:
    raw = app.state.inspector_input_buffer
    from cyberpunk_designer.selection_ops import search_widgets

    _commit_epilogue(app, "")
    search_widgets(app, raw.strip())
    return True


def _handle_spacing(app) -> bool:
    raw = app.state.inspector_input_buffer
    buf = raw.strip()
    parts = [p.strip() for p in buf.replace(" ", ",").split(",") if p.strip()]
    if len(parts) != 4:
        app._set_status("Format: px,py,mx,my (e.g. 2,1,0,0)", ttl_sec=3.0)
        return False
    try:
        px = int(parts[0])
        py = int(parts[1])
        mx = int(parts[2])
        my = int(parts[3])
    except (ValueError, TypeError):
        app._set_status("Invalid spacing \u2014 use integers.", ttl_sec=3.0)
        return False
    if px < 0 or py < 0 or mx < 0 or my < 0:
        app._set_status("Spacing values must be \u2265 0.", ttl_sec=3.0)
        return False
    selection = app.state.selection_list()
    if not selection:
        app._inspector_cancel_edit()
        return True
    safe_save_state(app.designer)
    sc = app.state.current_scene()
    for idx in selection:
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].padding_x = px
            sc.widgets[idx].padding_y = py
            sc.widgets[idx].margin_x = mx
            sc.widgets[idx].margin_y = my
    return _commit_epilogue(app, f"Spacing: pad={px},{py} margin={mx},{my}")


def _handle_array_dup(app) -> bool:
    raw = app.state.inspector_input_buffer
    _commit_epilogue(app, "")
    buf = raw.strip()
    parts = [p.strip() for p in buf.replace(" ", ",").split(",") if p.strip()]
    if len(parts) != 3:
        app._set_status("Format: count,dx,dy (e.g. 3,16,0)", ttl_sec=3.0)
        return False
    try:
        count = int(parts[0])
        dx = int(parts[1])
        dy = int(parts[2])
    except (ValueError, TypeError):
        app._set_status("Invalid values \u2014 use integers.", ttl_sec=3.0)
        return False
    from cyberpunk_designer.selection_ops import array_duplicate

    array_duplicate(app, count, dx, dy)
    return True


def _handle_template_name(app) -> bool:
    raw = app.state.inspector_input_buffer
    name = raw.strip()
    app.state.inspector_selected_field = None
    app.state.inspector_input_buffer = ""
    try:
        pygame.key.stop_text_input()
    except (pygame.error, AttributeError):
        pass
    if not name:
        app._set_status("Template name cannot be empty.", ttl_sec=3.0)
        return False
    widgets = getattr(app, "_pending_template_widgets", None)
    if not widgets:
        app._set_status("No widgets to save.", ttl_sec=3.0)
        return False
    from ui_template_manager import Template, TemplateMetadata

    scene_data = {
        "name": name,
        "widgets": widgets,
    }

    class _SceneProxy:
        def __init__(self, data):
            self._raw_data = data

    tpl = Template(
        metadata=TemplateMetadata(
            name=name,
            category="Custom",
            description=f"{len(widgets)} widget(s)",
        ),
        scene=_SceneProxy(scene_data),
    )
    try:
        app.template_library.add_template(tpl)
        app.template_actions = app._build_template_actions()
        # Append new template action to palette
        label = f"Template: {name}"
        app.palette_actions.append((label, lambda t=tpl: app._apply_template(t)))
    except (AttributeError, ValueError) as exc:
        app._set_status(f"Template save failed: {exc}", ttl_sec=3.0)
        return False
    app._pending_template_widgets = None
    app._set_status(f"Saved template: {name}", ttl_sec=2.0)
    app._mark_dirty()
    return True


def _handle_value_range(app) -> bool:
    raw = app.state.inspector_input_buffer
    pair = _parse_pair(raw.strip())
    if pair is None:
        app._set_status("Format: min,max (e.g. 0,100)", ttl_sec=3.0)
        return False
    lo, hi = pair
    if lo > hi:
        app._set_status("min must be \u2264 max.", ttl_sec=3.0)
        return False
    selection = app.state.selection_list()
    if not selection:
        app._inspector_cancel_edit()
        return True
    safe_save_state(app.designer)
    sc = app.state.current_scene()
    for idx in selection:
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].min_value = lo
            sc.widgets[idx].max_value = hi
            v = int(getattr(sc.widgets[idx], "value", 0) or 0)
            sc.widgets[idx].value = max(lo, min(hi, v))
    return _commit_epilogue(app, f"Value range: {lo}..{hi}")


def _handle_size(app) -> bool:
    raw = app.state.inspector_input_buffer
    buf = raw.strip()
    parts = None
    for sep in ("x", "X", ",", " "):
        if sep in buf:
            parts = buf.split(sep, 1)
            break
    if parts is None or len(parts) != 2:
        app._set_status("Format: WxH or W,H (e.g. 64x16)", ttl_sec=3.0)
        return False
    try:
        nw = int(parts[0].strip())
        nh = int(parts[1].strip())
    except (ValueError, TypeError):
        app._set_status("Invalid size — use integers.", ttl_sec=3.0)
        return False
    if nw < 1 or nh < 1:
        app._set_status("Size must be positive.", ttl_sec=3.0)
        return False
    selection = app.state.selection_list()
    if not selection:
        app._inspector_cancel_edit()
        return True
    safe_save_state(app.designer)
    sc = app.state.current_scene()
    for idx in selection:
        if 0 <= idx < len(sc.widgets):
            sc.widgets[idx].width = nw
            sc.widgets[idx].height = nh
    return _commit_epilogue(app, f"Size: {nw}x{nh}")


def _handle_goto_widget(app) -> bool:
    raw = app.state.inspector_input_buffer
    buf = raw.strip()
    try:
        idx = int(buf)
    except (ValueError, TypeError):
        app._set_status(f"Invalid index: {buf!r}", ttl_sec=3.0)
        return False
    sc = app.state.current_scene()
    if not (0 <= idx < len(sc.widgets)):
        app._set_status(f"Widget #{idx} not found (0..{len(sc.widgets) - 1}).", ttl_sec=3.0)
        return False
    app._set_selection([idx], anchor_idx=idx)
    return _commit_epilogue(app, f"Selected widget #{idx}: {sc.widgets[idx].type}")


def _handle_scene_name(app) -> bool:
    raw = app.state.inspector_input_buffer
    new_name = raw.strip()
    if not new_name:
        app._set_status("Scene name cannot be empty.", ttl_sec=3.0)
        return False
    if not all(ch.isalnum() or ch in "_- " for ch in new_name):
        app._set_status("Invalid scene name.", ttl_sec=3.0)
        return False
    old_name = str(app.designer.current_scene or "")
    if new_name == old_name:
        app.state.inspector_selected_field = None
        app.state.inspector_input_buffer = ""
        try:
            pygame.key.stop_text_input()
        except (pygame.error, AttributeError):
            pass
        return True
    if new_name in app.designer.scenes:
        app._set_status(f"Scene '{new_name}' already exists.", ttl_sec=3.0)
        return False
    # Rename: move scene data to new key
    scene_data = app.designer.scenes.pop(old_name, None)
    if scene_data is not None:
        app.designer.scenes[new_name] = scene_data
    # Transfer dirty state to new name
    dirty_scenes = getattr(app, "_dirty_scenes", set())
    if old_name in dirty_scenes:
        dirty_scenes.discard(old_name)
        dirty_scenes.add(new_name)
    app.designer.current_scene = new_name
    app.state.inspector_selected_field = None
    app.state.inspector_input_buffer = ""
    try:
        pygame.key.stop_text_input()
    except (pygame.error, AttributeError):
        pass
    app._set_status(f"Renamed: {old_name} → {new_name}", ttl_sec=2.0)
    app._mark_dirty()
    return True


_SPECIAL_HANDLERS = {
    "_position": _handle_position,
    "_padding": _handle_padding,
    "_margin": _handle_margin,
    "_search": _handle_search,
    "_spacing": _handle_spacing,
    "_array_dup": _handle_array_dup,
    "_template_name": _handle_template_name,
    "_value_range": _handle_value_range,
    "_size": _handle_size,
    "_goto_widget": _handle_goto_widget,
    "_scene_name": _handle_scene_name,
}
