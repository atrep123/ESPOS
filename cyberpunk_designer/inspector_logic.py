"""Property inspector: field display and row computation.

Commit-edit logic lives in :mod:`cyberpunk_designer.inspector_commit`.
This module re-exports ``inspector_commit_edit`` for backward compatibility.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ui_designer import HARDWARE_PROFILES, WidgetConfig

from .inspector_commit import (
    _parse_active_count as _parse_active_count,  # pyright: ignore[reportPrivateUsage]
)
from .inspector_commit import (
    _parse_pair as _parse_pair,  # pyright: ignore[reportPrivateUsage]
)
from .inspector_commit import (
    _sorted_role_indices as _sorted_role_indices,  # pyright: ignore[reportPrivateUsage]
)
from .inspector_commit import (
    inspector_commit_edit as inspector_commit_edit,
)
from .inspector_utils import format_int_list


def inspector_field_to_str(app, field: str, w: WidgetConfig) -> str:
    f = str(field or "")
    selection = app.state.selection_list()
    try:
        sc = app.state.current_scene()
    except AttributeError:
        sc = None

    if f.startswith("comp.") and sc is not None:
        ctx = app._selected_component_group()
        if ctx:
            _group_name, comp_type, root, members = ctx
            suffix = f.split(".", 1)[1]
            if suffix == "root":
                return str(root or "")
            spec = app._component_field_specs(comp_type).get(suffix)
            if spec:
                role, attr, kind = spec
                role_idx = app._component_role_index(members, root)
                if kind == "menu_active":
                    items = _sorted_role_indices(role_idx, "item")
                    if not items:
                        return ""
                    active_pos = 1
                    for pos, (_n, wi2) in enumerate(items):
                        if 0 <= wi2 < len(sc.widgets):
                            st = str(getattr(sc.widgets[wi2], "style", "") or "").lower()
                            if "highlight" in st:
                                active_pos = pos + 1
                                break
                    return str(active_pos)
                if kind == "tabs_active":
                    tabs = _sorted_role_indices(role_idx, "tab")
                    if not tabs:
                        return ""
                    active = tabs[0][0]
                    for n, wi2 in tabs:
                        if 0 <= wi2 < len(sc.widgets):
                            st = str(getattr(sc.widgets[wi2], "style", "") or "").lower()
                            if "highlight" in st:
                                active = n
                                break
                    else:
                        for n, wi2 in tabs:
                            if 0 <= wi2 < len(sc.widgets):
                                st = str(getattr(sc.widgets[wi2], "style", "") or "").lower()
                                if "bold" in st:
                                    active = n
                                    break
                    return str(active)
                if kind == "list_count":
                    items = _sorted_role_indices(role_idx, "item")
                    visible = len(items)
                    wi = role_idx.get(role)
                    if wi is not None and 0 <= wi < len(sc.widgets):
                        parsed = _parse_active_count(str(getattr(sc.widgets[wi], attr, "") or ""))
                        if parsed is not None:
                            return str(parsed[1])
                    return str(visible or 0)
                wi = role_idx.get(role)
                if wi is not None and 0 <= wi < len(sc.widgets):
                    val = getattr(sc.widgets[wi], attr, "")
                    if kind == "int":
                        try:
                            return str(int(val))
                        except (ValueError, TypeError):
                            return "0"
                    if kind == "int_list":
                        return format_int_list(val, max_items=256)
                    if kind.startswith("choice:"):
                        return str(val or "")
                    return str(val or "")
        return ""

    if len(selection) > 1 and sc is not None:
        bounds = app._selection_bounds(selection)
        if bounds is not None and f in {"x", "y", "width", "height"}:
            return str(int(getattr(bounds, f)))

        if f in {"color_fg", "color_bg", "border_style", "align", "valign"}:
            values: List[str] = []
            for idx in selection:
                if 0 <= idx < len(sc.widgets):
                    values.append(str(getattr(sc.widgets[idx], f, "") or ""))
            uniq = sorted({v for v in values if v})
            if len(uniq) == 1:
                return uniq[0]
            return ""

    if f == "data_points":
        pts = getattr(w, "data_points", []) or []
        return format_int_list(pts, max_items=256)
    if f == "chart_mode":
        style = str(getattr(w, "style", "default") or "default").lower()
        label = str(getattr(w, "text", "") or "")
        return style if style in {"bar", "line"} else ("bar" if "bar" in label.lower() else "line")
    if f == "text":
        return str(getattr(w, "text", "") or "")
    if f == "runtime":
        return str(getattr(w, "runtime", "") or "")
    if f == "_size":
        ww = int(getattr(w, "width", 0) or 0)
        wh = int(getattr(w, "height", 0) or 0)
        return f"{ww}x{wh}"
    if f == "_position":
        wx = int(getattr(w, "x", 0) or 0)
        wy = int(getattr(w, "y", 0) or 0)
        return f"{wx},{wy}"
    if f == "_padding":
        px = int(getattr(w, "padding_x", 1) or 0)
        py = int(getattr(w, "padding_y", 0) or 0)
        return f"{px},{py}"
    if f == "_margin":
        mx = int(getattr(w, "margin_x", 0) or 0)
        my = int(getattr(w, "margin_y", 0) or 0)
        return f"{mx},{my}"
    if f == "_spacing":
        px = int(getattr(w, "padding_x", 1) or 0)
        py = int(getattr(w, "padding_y", 0) or 0)
        mx = int(getattr(w, "margin_x", 0) or 0)
        my = int(getattr(w, "margin_y", 0) or 0)
        return f"{px},{py},{mx},{my}"
    if f == "_value_range":
        lo = int(getattr(w, "min_value", 0) or 0)
        hi = int(getattr(w, "max_value", 100) or 100)
        return f"{lo},{hi}"
    if f in {"x", "y", "width", "height", "value", "min_value", "max_value", "z_index"}:
        try:
            return str(int(getattr(w, f)))
        except (ValueError, TypeError):
            return "0"
    if f in {"color_fg", "color_bg", "border_style", "align", "valign"}:
        return str(getattr(w, f, "") or "")
    return str(getattr(w, f, "") or "")



def compute_inspector_rows(app) -> Tuple[List[Tuple[str, str]], bool, Optional[WidgetConfig]]:
    rows: List[Tuple[str, str]] = []
    warning = False
    overlaps = 0
    w = app.state.selected_widget()
    est = app.designer.estimate_resources(profile=app.hardware_profile)
    profile_label = ""
    if app.hardware_profile and app.hardware_profile in HARDWARE_PROFILES:
        profile_label = HARDWARE_PROFILES[app.hardware_profile]["label"]
    res_text = "No profile"
    if est:
        fb_txt = f"{est['framebuffer_kb']:.1f}KB"
        flash_txt = f"{est['flash_kb']:.1f}KB"
        res_text = f"FB {fb_txt} | Flash {flash_txt}"
        overlaps = int(est.get("overlaps", 0) or 0)
        if est.get("fb_over") or est.get("flash_over"):
            warning = True
            res_text += " (!)"
    rows.append(("_section:Info", "Info"))
    rows.append(("profile", f"profile: {profile_label or 'none'}"))
    rows.append(("resources", f"resources: {res_text}"))
    if overlaps:
        rows.append(("overlaps", f"overlaps: {overlaps}"))
    live_row = "Live: off"
    if app.live_preview_port:
        live_row = f"Live: {app.live_preview_port}@{app.live_preview_baud}"
    rows.append(("live", f"live: {live_row}"))
    rows.append(("snapgrid", f"snap: {bool(app.snap_enabled)}  grid: {bool(app.show_grid)}"))
    rows.append(("panels", f"panels: {'off' if app.panels_collapsed else 'on'}"))
    sc = app.state.current_scene()
    selection = app.state.selection_list()

    def _mixed_str(values: List[str]) -> str:
        uniq = sorted({str(v or "") for v in values if str(v or "")})
        if len(uniq) == 1:
            return uniq[0]
        if not uniq:
            return ""
        return "(mixed)"

    if selection:
        if len(selection) > 1:
            widgets = [sc.widgets[i] for i in selection if 0 <= i < len(sc.widgets)]
            bounds = app._selection_bounds(selection)
            rows.append(("_section:Selection", f"Selection ({len(selection)})"))
            rows.append(("selection", f"selection: {len(selection)} widgets"))
            rows.append(("type", "type: (multiple)"))
            if bounds is not None:
                rows.append(("x", f"x: {int(bounds.x)}"))
                rows.append(("y", f"y: {int(bounds.y)}"))
                rows.append(("width", f"width: {int(bounds.width)}"))
                rows.append(("height", f"height: {int(bounds.height)}"))
            rows.append(
                (
                    "color_fg",
                    f"color_fg: {_mixed_str([getattr(x, 'color_fg', '') for x in widgets])}",
                )
            )
            rows.append(
                (
                    "color_bg",
                    f"color_bg: {_mixed_str([getattr(x, 'color_bg', '') for x in widgets])}",
                )
            )
            rows.append(
                (
                    "border",
                    f"border: {app._tri_state([bool(getattr(x, 'border', True)) for x in widgets])}",
                )
            )
            rows.append(
                (
                    "border_style",
                    f"border_style: {_mixed_str([getattr(x, 'border_style', '') for x in widgets])}",
                )
            )
            rows.append(
                ("align", f"align: {_mixed_str([getattr(x, 'align', '') for x in widgets])}")
            )
            rows.append(
                ("valign", f"valign: {_mixed_str([getattr(x, 'valign', '') for x in widgets])}")
            )
            rows.append(
                (
                    "visible",
                    f"visible: {app._tri_state([bool(getattr(x, 'visible', True)) for x in widgets])}",
                )
            )
            rows.append(
                (
                    "locked",
                    f"locked: {app._tri_state([bool(getattr(x, 'locked', False)) for x in widgets])}",
                )
            )

            ctx = app._selected_component_group()
            if ctx:
                group_name, comp_type, root, members = ctx
                rows.append(("group", f"group: {group_name}"))
                rows.append(("component", f"component: {comp_type}"))
                rows.append(("comp.root", f"root: {root}"))
                role_idx = app._component_role_index(members, root)
                for key_suffix, spec in app._component_field_specs(comp_type).items():
                    role, _attr, _kind = spec
                    wi = role_idx.get(role)
                    if wi is None or not (0 <= wi < len(sc.widgets)):
                        continue
                    disp = inspector_field_to_str(app, f"comp.{key_suffix}", sc.widgets[wi])
                    rows.append((f"comp.{key_suffix}", f"{key_suffix}: {disp}"))
                rows.append(("hint", "tip: comp.* edits the whole component"))
            else:
                group_name = app._selected_group_exact()
                if group_name:
                    rows.append(("group", f"group: {group_name}"))
        elif w:
            rows.append(("_section:Selection", "Selection"))
            rows += [
                ("type", f"type: {w.type}"),
                ("x", f"x: {int(getattr(w, 'x', 0))}"),
                ("y", f"y: {int(getattr(w, 'y', 0))}"),
                ("width", f"width: {int(getattr(w, 'width', 0))}"),
                ("height", f"height: {int(getattr(w, 'height', 0))}"),
                ("text", f"text: {getattr(w, 'text', '')}"),
                ("text_overflow", f"text_overflow: {getattr(w, 'text_overflow', '')}"),
                (
                    "max_lines",
                    f"max_lines: {'' if getattr(w, 'max_lines', None) is None else int(w.max_lines)}",
                ),
                ("runtime", f"runtime: {getattr(w, 'runtime', '')}"),
                ("color_fg", f"color_fg: {getattr(w, 'color_fg', '')}"),
                ("color_bg", f"color_bg: {getattr(w, 'color_bg', '')}"),
                ("border", f"border: {bool(getattr(w, 'border', True))}"),
                ("border_style", f"border_style: {getattr(w, 'border_style', '')}"),
                ("align", f"align: {getattr(w, 'align', '')}"),
                ("valign", f"valign: {getattr(w, 'valign', '')}"),
                ("visible", f"visible: {bool(getattr(w, 'visible', True))}"),
                ("enabled", f"enabled: {bool(getattr(w, 'enabled', True))}"),
                ("locked", f"locked: {bool(getattr(w, 'locked', False))}"),
                ("z_index", f"z_index: {int(getattr(w, 'z_index', 0) or 0)}"),
            ]
            ctx = app._selected_component_group()
            if ctx:
                group_name, comp_type, root, members = ctx
                rows.append(("group", f"group: {group_name}"))
                rows.append(("component", f"component: {comp_type}"))
                rows.append(("comp.root", f"root: {root}"))
                role_idx = app._component_role_index(members, root)
                for key_suffix, spec in app._component_field_specs(comp_type).items():
                    role, _attr, _kind = spec
                    wi = role_idx.get(role)
                    if wi is None or not (0 <= wi < len(sc.widgets)):
                        continue
                    disp = inspector_field_to_str(app, f"comp.{key_suffix}", sc.widgets[wi])
                    rows.append((f"comp.{key_suffix}", f"{key_suffix}: {disp}"))
                rows.append(("hint", "tip: comp.* edits the whole component"))
            if w.type == "chart":
                pts = list(getattr(w, "data_points", []) or [])
                style = str(getattr(w, "style", "default") or "default").lower()
                label = str(getattr(w, "text", "") or "")
                chart_mode = (
                    style
                    if style in {"bar", "line"}
                    else ("bar" if "bar" in label.lower() else "line")
                )
                rows.append(("chart_mode", f"chart_mode: {chart_mode}"))
                rows.append(("data_points", f"data_points: {format_int_list(pts, max_items=24)}"))
                rows.append(("points", f"points: {len(pts)}"))
            if w.type in {"checkbox", "toggle"}:
                rows.append(("checked", f"checked: {bool(getattr(w, 'checked', False))}"))
            if w.type == "list":
                items = list(getattr(w, "items", None) or [])
                rows.append(("items", f"items: {', '.join(items) if items else '(empty)'}"))
            if w.type in {"progressbar", "slider", "gauge", "list"}:
                rows.append(("value", f"value: {int(getattr(w, 'value', 0) or 0)}"))
                rows.append(("min_value", f"min_value: {int(getattr(w, 'min_value', 0) or 0)}"))
                rows.append(("max_value", f"max_value: {int(getattr(w, 'max_value', 100) or 0)}"))
        else:
            rows.append(("_section:Selection", "Selection"))
            rows.append(("none", "selection: none"))
    else:
        rows.append(("_section:Selection", "Selection"))
        rows.append(("none", "selection: none"))

    if sc.widgets:
        rows.append(("_section:Layers", f"Layers ({len(sc.widgets)})"))

        try:
            groups = dict(getattr(app.designer, "groups", {}) or {})
        except (AttributeError, TypeError):
            groups = {}

        group_items: List[Tuple[int, str, List[int]]] = []
        for gname, members in groups.items():
            valid = [int(i) for i in members if 0 <= int(i) < len(sc.widgets)]
            if len(valid) < 2:
                continue
            group_items.append((min(valid), str(gname), sorted(set(valid))))
        group_items.sort(key=lambda t: t[0])

        groups_starting: Dict[int, List[Tuple[str, List[int]]]] = {}
        for start_idx, gname, members in group_items:
            groups_starting.setdefault(int(start_idx), []).append((gname, members))

        shown_widgets: set[int] = set()
        shown_groups: set[str] = set()
        for idx, item in enumerate(sc.widgets):
            if idx in groups_starting:
                for gname, members in groups_starting[idx]:
                    if gname in shown_groups:
                        continue  # pragma: no cover
                    shown_groups.add(gname)
                    rows.append((f"group:{gname}", app._format_group_label(gname, members)))
                    for mi in members:
                        if 0 <= mi < len(sc.widgets):
                            shown_widgets.add(mi)
                            rows.append((f"layer:{mi}", f"  [{mi}] {sc.widgets[mi].type}"))
            if idx in shown_widgets:
                continue
            rows.append((f"layer:{idx}", f"[{idx}] {item.type}"))
    return rows, warning, w
