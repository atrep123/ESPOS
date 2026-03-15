"""Widget insertion logic for adding widgets to scenes."""

from __future__ import annotations

from typing import List, Set

from ui_designer import WidgetConfig

from .components import component_blueprints
from .constants import GRID, safe_save_state, snap


def _existing_roots(sc) -> Set[str]:
    roots: Set[str] = set()
    for w in getattr(sc, "widgets", []) or []:
        wid = str(getattr(w, "_widget_id", "") or "")
        if not wid:
            continue
        root = wid.split(".", 1)[0]
        if root:
            roots.add(root)
    return roots


def _unique_root(sc, base: str) -> str:
    base = str(base or "").strip()
    if not base:
        return ""
    roots = _existing_roots(sc)
    if base not in roots:
        return base
    n = 2
    while f"{base}_{n}" in roots:
        n += 1
    return f"{base}_{n}"


def add_component(app, name: str) -> None:
    """Insert a named component as a group of widgets."""
    comp_type = str(name or "")
    sc = app.state.current_scene()
    blueprints = component_blueprints(comp_type, sc)
    if not blueprints:
        app._set_status(f"Component not found: {comp_type}", ttl_sec=4.0)
        return
    root = _unique_root(sc, comp_type)

    safe_save_state(app.designer)

    base_z = 0
    try:
        base_z = max(int(getattr(w, "z_index", 0) or 0) for w in sc.widgets)
    except (ValueError, TypeError):
        base_z = 0

    min_x = min(int(bp.get("x", 0)) for bp in blueprints)
    min_y = min(int(bp.get("y", 0)) for bp in blueprints)
    max_x = max(int(bp.get("x", 0)) + int(bp.get("width", GRID)) for bp in blueprints)
    max_y = max(int(bp.get("y", 0)) + int(bp.get("height", GRID)) for bp in blueprints)
    comp_w = max(GRID, max_x - min_x)
    comp_h = max(GRID, max_y - min_y)

    origin_x = GRID
    origin_y = GRID
    if comp_type in {"modal"}:
        origin_x = 0
        origin_y = 0
    else:
        sr = getattr(app, "scene_rect", None)
        if sr is None or not hasattr(sr, "collidepoint"):
            sr = app.layout.canvas_rect
        if sr.collidepoint(app.pointer_pos):
            px = int(app.pointer_pos[0] - sr.x)
            py = int(app.pointer_pos[1] - sr.y)
            origin_x = px - (comp_w // 2)
            origin_y = py - (comp_h // 2)

    max_origin_x = max(0, int(sc.width) - comp_w)
    max_origin_y = max(0, int(sc.height) - comp_h)
    origin_x = max(0, min(max_origin_x, int(origin_x)))
    origin_y = max(0, min(max_origin_y, int(origin_y)))
    if app.snap_enabled:
        origin_x = snap(origin_x)
        origin_y = snap(origin_y)

    new_indices: List[int] = []
    for bp in blueprints:
        try:
            z = int(bp.get("z", 0))
        except (ValueError, TypeError):
            z = 0
        cfg = dict(bp)
        cfg.pop("z", None)
        role = str(cfg.pop("role", "") or "")
        widget_id = f"{root}.{role}" if role else ""
        try:
            w = WidgetConfig(
                type=str(cfg.get("type", "panel")),
                x=int(origin_x + int(cfg.get("x", 0))),
                y=int(origin_y + int(cfg.get("y", 0))),
                width=int(cfg.get("width", GRID)),
                height=int(cfg.get("height", GRID)),
                text=str(cfg.get("text", "")),
                style=str(cfg.get("style", "default")),
                color_fg=str(cfg.get("color_fg", "#f5f5f5")),
                color_bg=str(cfg.get("color_bg", "#101010")),
                border=bool(cfg.get("border", True)),
                border_style=str(cfg.get("border_style", "single")),
                align=str(cfg.get("align", "left")),
                valign=str(cfg.get("valign", "middle")),
                value=int(cfg.get("value", 0)),
                min_value=int(cfg.get("min_value", 0)),
                max_value=int(cfg.get("max_value", 100)),
                checked=bool(cfg.get("checked", False)),
                icon_char=str(cfg.get("icon_char", "")),
                data_points=list(cfg.get("data_points", [])),
                text_overflow=str(cfg.get("text_overflow", "ellipsis") or "ellipsis"),
                max_lines=cfg.get("max_lines"),
                runtime=str(cfg.get("runtime", "") or ""),
                locked=bool(cfg.get("locked", False)),
                visible=bool(cfg.get("visible", True)),
                enabled=bool(cfg.get("enabled", True)),
                z_index=int(base_z + z),
                _widget_id=widget_id,
            )
        except (ValueError, TypeError, KeyError):
            continue
        try:
            app._auto_complete_widget(w)
        except AttributeError:
            pass
        sc.widgets.append(w)
        new_indices.append(len(sc.widgets) - 1)

    if not new_indices:
        app._set_status(f"Component failed: {comp_type}", ttl_sec=4.0)
        return

    group_members = [i for i in new_indices if not bool(getattr(sc.widgets[i], "locked", False))]
    group_name = ""
    if len(group_members) >= 2:
        group_name = app._next_group_name(f"comp:{comp_type}:{root}:")
        try:
            if not app.designer.create_group(group_name, group_members):
                group_name = ""
        except AttributeError:
            group_name = ""

    app._set_selection(group_members or new_indices, anchor_idx=(group_members or new_indices)[0])
    label = str(comp_type)
    if root and root != comp_type:
        label = f"{comp_type} ({root})"
    if group_name:
        app._set_status(
            f"Inserted component: {label} ({len(new_indices)} widgets) grouped as {group_name}",
            ttl_sec=3.0,
        )
    else:
        app._set_status(f"Inserted component: {label} ({len(new_indices)} widgets)", ttl_sec=3.0)
    app._mark_dirty()
