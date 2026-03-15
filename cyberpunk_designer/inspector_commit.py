"""Inspector commit-edit logic: validate and apply inspector field changes.

Validation/parsing utilities live in :mod:`.inspector_values`.
Special-field handlers live in :mod:`.inspector_handlers`.
This module re-exports everything for backward compatibility.
"""

from __future__ import annotations

from typing import List, Optional

from .constants import GRID, clamp, safe_save_state, snap
from .inspector_handlers import (
    _SPECIAL_HANDLERS as _SPECIAL_HANDLERS,
)

# Re-export handlers for backward compat
from .inspector_handlers import (
    _handle_array_dup as _handle_array_dup,
)
from .inspector_handlers import (
    _handle_goto_widget as _handle_goto_widget,
)
from .inspector_handlers import (
    _handle_margin as _handle_margin,
)
from .inspector_handlers import (
    _handle_padding as _handle_padding,
)
from .inspector_handlers import (
    _handle_position as _handle_position,
)
from .inspector_handlers import (
    _handle_scene_name as _handle_scene_name,
)
from .inspector_handlers import (
    _handle_search as _handle_search,
)
from .inspector_handlers import (
    _handle_size as _handle_size,
)
from .inspector_handlers import (
    _handle_spacing as _handle_spacing,
)
from .inspector_handlers import (
    _handle_template_name as _handle_template_name,
)
from .inspector_handlers import (
    _handle_value_range as _handle_value_range,
)
from .inspector_utils import parse_int_list

# Re-export validation/parsing utilities for backward compat
from .inspector_values import (
    _CHOICE_FIELDS as _CHOICE_FIELDS,
)
from .inspector_values import (
    _commit_choice as _commit_choice,
)
from .inspector_values import (
    _commit_color as _commit_color,
)
from .inspector_values import (
    _commit_epilogue as _commit_epilogue,
)
from .inspector_values import (
    _commit_str_attr as _commit_str_attr,
)
from .inspector_values import (
    _parse_active_count as _parse_active_count,
)
from .inspector_values import (
    _parse_pair as _parse_pair,
)
from .inspector_values import (
    _sorted_role_indices as _sorted_role_indices,
)


def inspector_commit_edit(app) -> bool:
    field = app.state.inspector_selected_field
    if not field:
        return True
    f = str(field or "")

    handler = _SPECIAL_HANDLERS.get(f)
    if handler is not None:
        return handler(app)

    selection = app.state.selection_list()
    w = app.state.selected_widget()
    if w is None or not selection:
        app._inspector_cancel_edit()
        return True
    sc = app.state.current_scene()

    raw = app.state.inspector_input_buffer
    buf = raw.strip()

    def _finish_ok(message: str) -> bool:
        return _commit_epilogue(app, message)

    if f.startswith("comp."):
        ctx = app._selected_component_group()
        if not ctx:
            app._set_status("No component selected.", ttl_sec=3.0)
            return False
        group_name, comp_type, root, members = ctx
        suffix = f.split(".", 1)[1]
        if suffix == "root":
            new_root = buf.lower()
            if not new_root or "." in new_root or " " in new_root:
                app._set_status("root must be a simple name (no spaces/dots).", ttl_sec=4.0)
                return False
            if new_root == str(root or ""):
                return _finish_ok("Root unchanged.")
            if not all(ch.isalnum() or ch == "_" for ch in new_root):
                app._set_status("root may contain only [a-z0-9_].", ttl_sec=4.0)
                return False

            # Build full membership by id prefix (includes locked overlay panels, etc.).
            all_indices: List[int] = []
            for i, ww in enumerate(getattr(sc, "widgets", []) or []):
                wid = str(getattr(ww, "_widget_id", "") or "")
                if wid == str(root or "") or wid.startswith(f"{root}."):
                    all_indices.append(int(i))

            used_ids = {
                str(getattr(ww, "_widget_id", "") or "")
                for i, ww in enumerate(getattr(sc, "widgets", []) or [])
                if int(i) not in set(all_indices)
            }
            new_ids: List[str] = []
            for i in all_indices:
                wid = str(getattr(sc.widgets[i], "_widget_id", "") or "")
                if wid == str(root or ""):
                    cand = new_root
                elif wid.startswith(f"{root}."):
                    cand = f"{new_root}{wid[len(str(root or '')) :]}"
                else:
                    continue  # pragma: no cover
                if cand in used_ids:
                    app._set_status(f"root rename would collide with id: {cand}", ttl_sec=4.0)
                    return False
                new_ids.append(cand)

            safe_save_state(app.designer)

            for i in all_indices:
                ww = sc.widgets[i]
                wid = str(getattr(ww, "_widget_id", "") or "")
                if wid == str(root or ""):
                    ww._widget_id = new_root
                elif wid.startswith(f"{root}."):
                    ww._widget_id = f"{new_root}{wid[len(str(root or '')) :]}"

            # Rename the component group itself to keep type/root discoverable.
            try:
                groups = getattr(app.designer, "groups", None)
            except (AttributeError, TypeError):  # pragma: no cover
                groups = None
            if isinstance(groups, dict) and group_name in groups:
                members_copy = list(groups.get(group_name) or [])
                groups.pop(group_name, None)
                new_gname = app._next_group_name(f"comp:{comp_type}:{new_root}:")
                groups[new_gname] = members_copy

            # Invalidate runtime listmodel cache (simulation mode) if present.
            try:
                models = getattr(app, "_sim_listmodels", None)
            except (AttributeError, TypeError):  # pragma: no cover
                models = None
            if isinstance(models, dict):
                models.pop(str(root or ""), None)
                models.pop(new_root, None)

            return _finish_ok(f"Renamed root: {root} -> {new_root}")

        spec = app._component_field_specs(comp_type).get(suffix)
        if not spec:
            app._set_status(f"Not editable: {field}", ttl_sec=3.0)
            app._inspector_cancel_edit()
            return True
        role, attr, kind = spec
        role_idx = app._component_role_index(members, root)
        wi = role_idx.get(role)
        if wi is None or not (0 <= wi < len(sc.widgets)):
            app._set_status(f"Missing role: {role}", ttl_sec=3.0)
            return False
        target = sc.widgets[wi]
        safe_save_state(app.designer)
        if kind == "menu_active":
            items = _sorted_role_indices(role_idx, "item")
            if not items:
                app._set_status("No menu items found.", ttl_sec=3.0)
                return False
            try:
                v = int(buf)
            except (ValueError, TypeError):
                app._set_status(f"Invalid {suffix}: {buf!r}", ttl_sec=4.0)
                return False
            n_items = len(items)
            # Accept 0-based (0..n-1) and 1-based (1..n) input.
            if 1 <= v <= n_items:
                active_pos = v - 1
            elif 0 <= v < n_items:
                active_pos = v
            else:
                app._set_status(f"{suffix} must be 0..{n_items - 1} or 1..{n_items}", ttl_sec=4.0)
                return False
            for pos, (_n, wi2) in enumerate(items):
                if not (0 <= wi2 < len(sc.widgets)):
                    continue
                ww = sc.widgets[wi2]
                ww.style = "highlight" if pos == active_pos else "default"
            # Keep scroll label in sync if present (active/count).
            try:
                scroll_idx = role_idx.get("scroll")
                if scroll_idx is not None and 0 <= int(scroll_idx) < len(sc.widgets):
                    sw = sc.widgets[int(scroll_idx)]
                    parsed = _parse_active_count(str(getattr(sw, "text", "") or ""))
                    count = parsed[1] if parsed is not None else len(items)
                    sw.text = f"{active_pos + 1}/{count}" if count > 0 else "0/0"
            except (ValueError, TypeError):
                pass
            try:
                active_idx = items[active_pos][1]
                if 0 <= active_idx < len(sc.widgets):
                    app._set_focus(active_idx, sync_selection=False)
            except (IndexError, TypeError):
                pass
            return _finish_ok(f"Updated {suffix}.")
        if kind == "tabs_active":
            tabs = _sorted_role_indices(role_idx, "tab")
            if not tabs:
                app._set_status("No tabs found.", ttl_sec=3.0)
                return False
            try:
                v = int(buf)
            except (ValueError, TypeError):
                app._set_status(f"Invalid {suffix}: {buf!r}", ttl_sec=4.0)
                return False
            tab_nums = [n for n, _wi2 in tabs]
            # Accept 0-based (0..count-1) and 1-based (tab numbers, usually 1..3).
            if v in tab_nums:
                want_num = v
            elif 0 <= v < len(tab_nums):
                want_num = tab_nums[v]
            else:
                app._set_status(
                    f"{suffix} must be 0..{len(tab_nums) - 1} or {tab_nums[0]}..{tab_nums[-1]}",
                    ttl_sec=4.0,
                )
                return False
            for n, wi2 in tabs:
                if not (0 <= wi2 < len(sc.widgets)):
                    continue
                ww = sc.widgets[wi2]
                ww.style = "bold highlight" if n == want_num else "default"
            try:
                active_idx = next(wi2 for n, wi2 in tabs if n == want_num)
                if 0 <= active_idx < len(sc.widgets):
                    app._set_focus(active_idx, sync_selection=False)
            except StopIteration:
                pass
            return _finish_ok(f"Updated {suffix}.")
        if kind == "list_count":
            try:
                new_count = int(buf)
            except (ValueError, TypeError):
                app._set_status(f"Invalid {suffix}: {buf!r}", ttl_sec=4.0)
                return False
            if new_count < 0:
                app._set_status(f"{suffix} must be >= 0", ttl_sec=4.0)
                return False
            items = _sorted_role_indices(role_idx, "item")
            visible = len(items)
            parsed = _parse_active_count(str(getattr(target, attr, "") or ""))
            active = parsed[0] if parsed is not None else 0
            if new_count <= 0:
                active = 0
                target.text = "0/0"
            else:
                active = max(0, min(active, new_count - 1))
                target.text = f"{active + 1}/{new_count}"
            if visible > 0 and new_count < visible:
                # Keep the active index visible even when list shrinks below slot count.
                active = max(0, min(active, max(0, new_count - 1)))
            try:
                models = getattr(app, "_sim_listmodels", None)
            except (AttributeError, TypeError):  # pragma: no cover
                models = None
            if isinstance(models, dict):
                models.pop(str(root or ""), None)
            return _finish_ok(f"Updated {suffix}.")
        if kind.startswith("choice:"):
            allowed = {x.strip().lower() for x in kind.split(":", 1)[1].split("|") if x.strip()}
            val = buf.lower()
            if val not in allowed:
                app._set_status(f"{suffix} must be: {'|'.join(sorted(allowed))}", ttl_sec=4.0)
                return False
            setattr(target, attr, val)
        elif kind == "int_list":
            pts = parse_int_list(buf)
            if pts is None:
                app._set_status(f"Invalid {suffix}: {buf!r}", ttl_sec=4.0)
                return False
            setattr(target, attr, pts)
        elif kind == "int":
            try:
                v = int(buf)
            except (ValueError, TypeError):
                app._set_status(f"Invalid {suffix}: {buf!r}", ttl_sec=4.0)
                return False
            if attr == "max_value":
                v = max(1, v)
                try:
                    cur = int(getattr(target, "value", 0) or 0)
                    if cur > v:
                        target.value = v
                except (ValueError, TypeError):
                    pass
            if attr == "value":
                try:
                    mn = int(getattr(target, "min_value", 0) or 0)
                    mx = int(getattr(target, "max_value", 100) or 100)
                    v = max(mn, min(mx, v))
                except (ValueError, TypeError):
                    pass
            setattr(target, attr, v)
        else:
            setattr(target, attr, raw)

        return _finish_ok(f"Updated {suffix}.")

    if len(selection) > 1:
        if f in {"x", "y"}:
            try:
                v = int(buf)
            except (ValueError, TypeError):
                app._set_status(f"Invalid {f}: {buf!r}", ttl_sec=4.0)
                return False
            bounds = app._selection_bounds(selection)
            if bounds is None:
                return False
            dx = int(v - int(bounds.x)) if f == "x" else 0
            dy = int(v - int(bounds.y)) if f == "y" else 0
            app._move_selection(dx, dy)
        elif f in {"width", "height"}:
            try:
                v = int(buf)
            except (ValueError, TypeError):
                app._set_status(f"Invalid {f}: {buf!r}", ttl_sec=4.0)
                return False
            bounds = app._selection_bounds(selection)
            if bounds is None:
                return False
            new_w = int(v) if f == "width" else int(bounds.width)
            new_h = int(v) if f == "height" else int(bounds.height)
            if not app._resize_selection_to(new_w, new_h):
                return False
        else:
            targets = [sc.widgets[i] for i in selection if 0 <= i < len(sc.widgets)]
            # Try shared commit helpers (color, choice, text)
            result = _commit_color(app, f, buf, targets)
            if result is None:
                result = _commit_choice(app, f, buf, targets)
            if result is None:
                result = _commit_str_attr(app, f, raw, targets)
            if result is not None:
                if not result:
                    return False
            elif f == "max_lines":
                try:
                    ml = None if (not buf or buf == "0") else int(buf)
                except (ValueError, TypeError):
                    app._set_status(f"Invalid {f}: {buf!r}", ttl_sec=4.0)
                    return False
                if ml is not None and ml <= 0:
                    ml = None
                safe_save_state(app.designer)
                for idx in selection:
                    if 0 <= idx < len(sc.widgets):
                        sc.widgets[idx].max_lines = ml
            elif f == "data_points":
                pts = parse_int_list(buf)
                if pts is None:
                    app._set_status(f"Invalid {f}: {buf!r}", ttl_sec=4.0)
                    return False
                safe_save_state(app.designer)
                applied = 0
                for idx in selection:
                    if (
                        0 <= idx < len(sc.widgets)
                        and str(getattr(sc.widgets[idx], "type", "")).lower() == "chart"
                    ):
                        sc.widgets[idx].data_points = pts
                        applied += 1
                if not applied:
                    app._set_status("No chart widgets in selection.", ttl_sec=3.0)
                    return False
            elif f == "chart_mode":
                val = buf.lower()
                if val not in {"bar", "line"}:
                    app._set_status("chart_mode must be: bar|line", ttl_sec=4.0)
                    return False
                safe_save_state(app.designer)
                applied = 0
                for idx in selection:
                    if (
                        0 <= idx < len(sc.widgets)
                        and str(getattr(sc.widgets[idx], "type", "")).lower() == "chart"
                    ):
                        sc.widgets[idx].style = val
                        applied += 1
                if not applied:
                    app._set_status("No chart widgets in selection.", ttl_sec=3.0)
                    return False
            elif f == "z_index":
                try:
                    v = int(buf)
                except (ValueError, TypeError):
                    app._set_status(f"Invalid {f}: {buf!r}", ttl_sec=4.0)
                    return False
                v = clamp(v, -1_000_000, 1_000_000)
                safe_save_state(app.designer)
                for idx in selection:
                    if 0 <= idx < len(sc.widgets):
                        sc.widgets[idx].z_index = v
            elif f in {"value", "min_value", "max_value"}:
                try:
                    v = int(buf)
                except (ValueError, TypeError):
                    app._set_status(f"Invalid {f}: {buf!r}", ttl_sec=4.0)
                    return False
                v = clamp(v, -1_000_000, 1_000_000)
                safe_save_state(app.designer)
                for idx in selection:
                    if 0 <= idx < len(sc.widgets):
                        setattr(sc.widgets[idx], f, v)
            elif f == "checked":
                checked = buf.lower() in {"true", "1", "yes", "on"}
                safe_save_state(app.designer)
                for idx in selection:
                    if 0 <= idx < len(sc.widgets):
                        sc.widgets[idx].checked = checked
            elif f == "items":
                parts = [s.strip() for s in buf.replace(",", "\n").split("\n") if s.strip()]
                safe_save_state(app.designer)
                for idx in selection:
                    if 0 <= idx < len(sc.widgets):
                        sc.widgets[idx].items = parts
                        sc.widgets[idx].text = "\n".join(parts)
            else:
                app._set_status(f"Not editable: {field}", ttl_sec=3.0)
                app._inspector_cancel_edit()
                return True

        return _commit_epilogue(app, f"Updated {field}.")

    def _apply_int(attr: str, min_value: int = 0, max_value: Optional[int] = None) -> bool:
        try:
            v = int(buf)
        except (ValueError, TypeError):
            app._set_status(f"Invalid {attr}: {buf!r}", ttl_sec=4.0)
            return False
        if app.snap_enabled and attr in {"x", "y", "width", "height"}:
            v = snap(v)
        v = max(min_value, v)
        if max_value is not None:
            v = min(max_value, v)
        try:
            setattr(w, attr, v)
        except (TypeError, AttributeError):
            return False
        return True

    # Try shared commit helpers first (text/runtime, color, choice fields)
    result = _commit_str_attr(app, f, raw, [w])
    if result is None:
        result = _commit_color(app, f, buf, [w])
    if result is None:
        result = _commit_choice(app, f, buf, [w])
    if result is not None:
        if not result:
            return False
        return _commit_epilogue(app, f"Updated {field}.")

    if f in {"x", "y"}:
        safe_save_state(app.designer)
        max_x = max(0, int(sc.width) - int(w.width))
        max_y = max(0, int(sc.height) - int(w.height))
        if not _apply_int(f, min_value=0, max_value=max_x if f == "x" else max_y):
            return False
    elif f in {"width", "height"}:
        safe_save_state(app.designer)
        max_w = max(GRID, int(sc.width) - int(w.x))
        max_h = max(GRID, int(sc.height) - int(w.y))
        if f == "width":
            if not _apply_int("width", min_value=GRID, max_value=max_w):
                return False
        else:
            if not _apply_int("height", min_value=GRID, max_value=max_h):
                return False
        # Keep widget inside scene after resize.
        w.x = max(0, min(int(w.x), max(0, int(sc.width) - int(w.width))))
        w.y = max(0, min(int(w.y), max(0, int(sc.height) - int(w.height))))
    elif f in {"value", "min_value", "max_value"}:
        safe_save_state(app.designer)
        if not _apply_int(f, min_value=-1_000_000, max_value=1_000_000):
            return False
    elif f == "checked":
        safe_save_state(app.designer)
        w.checked = buf.lower() in {"true", "1", "yes", "on"}
    elif f == "items":
        safe_save_state(app.designer)
        parts = [s.strip() for s in buf.replace(",", "\n").split("\n") if s.strip()]
        w.items = parts
        w.text = "\n".join(parts)
    elif f == "z_index":
        safe_save_state(app.designer)
        if not _apply_int("z_index", min_value=-1_000_000, max_value=1_000_000):
            return False
    elif f == "max_lines":
        safe_save_state(app.designer)
        if not buf or buf == "0":
            w.max_lines = None
        else:
            try:
                ml = int(buf)
            except (ValueError, TypeError):
                app._set_status(f"Invalid {f}: {buf!r}", ttl_sec=4.0)
                return False
            w.max_lines = ml if ml > 0 else None
    elif f == "data_points":
        pts = parse_int_list(buf)
        if pts is None:
            app._set_status(f"Invalid {f}: {buf!r}", ttl_sec=4.0)
            return False
        safe_save_state(app.designer)
        w.data_points = pts
    elif f == "chart_mode":
        val = buf.lower()
        if val not in {"bar", "line"}:
            app._set_status("chart_mode must be: bar|line", ttl_sec=4.0)
            return False
        safe_save_state(app.designer)
        w.style = val
    else:
        app._set_status(f"Not editable: {field}", ttl_sec=3.0)
        app._inspector_cancel_edit()
        return True

    return _commit_epilogue(app, f"Updated {field}.")
