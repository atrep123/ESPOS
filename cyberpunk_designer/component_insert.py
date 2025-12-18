from __future__ import annotations

from typing import List

from ui_designer import WidgetConfig

from .components import component_blueprints
from .constants import GRID, snap


def add_component(app, name: str) -> None:
    """Insert a named component as a group of widgets."""
    comp_name = str(name or "")
    sc = app.state.current_scene()
    blueprints = component_blueprints(comp_name, sc)
    if not blueprints:
        app._set_status(f"Component not found: {comp_name}", ttl_sec=4.0)
        return

    try:
        app.designer._save_state()
    except Exception:
        pass

    base_z = 0
    try:
        base_z = max(int(getattr(w, "z_index", 0) or 0) for w in sc.widgets)
    except Exception:
        base_z = 0

    min_x = min(int(bp.get("x", 0)) for bp in blueprints)
    min_y = min(int(bp.get("y", 0)) for bp in blueprints)
    max_x = max(int(bp.get("x", 0)) + int(bp.get("width", GRID)) for bp in blueprints)
    max_y = max(int(bp.get("y", 0)) + int(bp.get("height", GRID)) for bp in blueprints)
    comp_w = max(GRID, max_x - min_x)
    comp_h = max(GRID, max_y - min_y)

    origin_x = GRID
    origin_y = GRID
    if comp_name in {"modal"}:
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
        except Exception:
            z = 0
        cfg = dict(bp)
        cfg.pop("z", None)
        role = str(cfg.pop("role", "") or "")
        widget_id = f"{comp_name}.{role}" if role else ""
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
                max_lines=cfg.get("max_lines", None),
                runtime=str(cfg.get("runtime", "") or ""),
                locked=bool(cfg.get("locked", False)),
                visible=bool(cfg.get("visible", True)),
                enabled=bool(cfg.get("enabled", True)),
                z_index=int(base_z + z),
                _widget_id=widget_id,
            )
        except Exception:
            continue
        try:
            app._auto_complete_widget(w)
        except Exception:
            pass
        sc.widgets.append(w)
        new_indices.append(len(sc.widgets) - 1)

    if not new_indices:
        app._set_status(f"Component failed: {comp_name}", ttl_sec=4.0)
        return

    group_members = [i for i in new_indices if not bool(getattr(sc.widgets[i], "locked", False))]
    group_name = ""
    if len(group_members) >= 2:
        group_name = app._next_group_name(f"comp:{comp_name}:")
        try:
            if not app.designer.create_group(group_name, group_members):
                group_name = ""
        except Exception:
            group_name = ""

    app._set_selection(group_members or new_indices, anchor_idx=(group_members or new_indices)[0])
    if group_name:
        app._set_status(
            f"Inserted component: {comp_name} ({len(new_indices)} widgets) grouped as {group_name}",
            ttl_sec=3.0,
        )
    else:
        app._set_status(f"Inserted component: {comp_name} ({len(new_indices)} widgets)", ttl_sec=3.0)
    app._mark_dirty()
