from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import pygame

from ui_designer import HARDWARE_PROFILES, WidgetConfig

from .constants import GRID, snap
from .inspector_utils import format_int_list, parse_int_list


def _sorted_role_indices(role_idx: Dict[str, int], prefix: str) -> List[Tuple[int, int]]:
    out: List[Tuple[int, int]] = []
    p = str(prefix or "")
    if not p:
        return out
    for role, idx in (role_idx or {}).items():
        r = str(role or "")
        if not r.startswith(p):
            continue
        suffix = r[len(p) :]
        if suffix.isdigit():
            out.append((int(suffix), int(idx)))
    out.sort(key=lambda t: t[0])
    return out


def _parse_active_count(text: str) -> Optional[Tuple[int, int]]:
    """Parse 'active/count' as (active_0_based, count)."""
    s = str(text or "").strip()
    if not s or "/" not in s:
        return None
    left, right = s.split("/", 1)
    try:
        a = int(left.strip())
        b = int(right.strip())
    except Exception:
        return None
    if b <= 0:
        return 0, 0
    a = max(1, min(a, b))
    return a - 1, b


def inspector_field_to_str(app, field: str, w: WidgetConfig) -> str:
    f = str(field or "")
    selection = list(getattr(app.state, "selected", []) or [])
    try:
        sc = app.state.current_scene()
    except Exception:
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
                        except Exception:
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
            uniq = sorted(set([v for v in values if v]))
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
    if f in {"x", "y", "width", "height", "value", "min_value", "max_value", "z_index"}:
        try:
            return str(int(getattr(w, f)))
        except Exception:
            return "0"
    if f in {"color_fg", "color_bg", "border_style", "align", "valign"}:
        return str(getattr(w, f, "") or "")
    return str(getattr(w, f, "") or "")


def inspector_commit_edit(app) -> bool:
    field = app.state.inspector_selected_field
    if not field:
        return True
    f = str(field or "")
    selection = list(getattr(app.state, "selected", []) or [])
    w = app.state.selected_widget()
    if w is None or not selection:
        app._inspector_cancel_edit()
        return True
    sc = app.state.current_scene()

    raw = app.state.inspector_input_buffer
    buf = raw.strip()

    def _finish_ok(message: str) -> bool:
        app.state.inspector_selected_field = None
        app.state.inspector_input_buffer = ""
        try:
            pygame.key.stop_text_input()
        except Exception:
            pass
        app._set_status(str(message or "Updated."), ttl_sec=2.0)
        app._mark_dirty()
        return True

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
                if not wid:
                    continue
                if wid == str(root or ""):
                    cand = new_root
                elif wid.startswith(f"{root}."):
                    cand = f"{new_root}{wid[len(str(root or '')):]}"
                else:
                    continue
                if cand in used_ids:
                    app._set_status(f"root rename would collide with id: {cand}", ttl_sec=4.0)
                    return False
                new_ids.append(cand)

            try:
                app.designer._save_state()
            except Exception:
                pass

            for i in all_indices:
                ww = sc.widgets[i]
                wid = str(getattr(ww, "_widget_id", "") or "")
                if not wid:
                    continue
                if wid == str(root or ""):
                    ww._widget_id = new_root
                elif wid.startswith(f"{root}."):
                    ww._widget_id = f"{new_root}{wid[len(str(root or '')):]}"

            # Rename the component group itself to keep type/root discoverable.
            try:
                groups = getattr(app.designer, "groups", None)
            except Exception:
                groups = None
            if isinstance(groups, dict) and group_name in groups:
                members_copy = list(groups.get(group_name) or [])
                groups.pop(group_name, None)
                new_gname = app._next_group_name(f"comp:{comp_type}:{new_root}:")
                groups[new_gname] = members_copy

            # Invalidate runtime listmodel cache (simulation mode) if present.
            try:
                models = getattr(app, "_sim_listmodels", None)
            except Exception:
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
        try:
            app.designer._save_state()
        except Exception:
            pass
        if kind == "menu_active":
            items = _sorted_role_indices(role_idx, "item")
            if not items:
                app._set_status("No menu items found.", ttl_sec=3.0)
                return False
            try:
                v = int(buf)
            except Exception:
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
            except Exception:
                pass
            try:
                active_idx = items[active_pos][1]
                if 0 <= active_idx < len(sc.widgets):
                    app._set_focus(active_idx, sync_selection=False)
            except Exception:
                pass
            return _finish_ok(f"Updated {suffix}.")
        if kind == "tabs_active":
            tabs = _sorted_role_indices(role_idx, "tab")
            if not tabs:
                app._set_status("No tabs found.", ttl_sec=3.0)
                return False
            try:
                v = int(buf)
            except Exception:
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
            except Exception:
                pass
            return _finish_ok(f"Updated {suffix}.")
        if kind == "list_count":
            try:
                new_count = int(buf)
            except Exception:
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
            except Exception:
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
            except Exception:
                app._set_status(f"Invalid {suffix}: {buf!r}", ttl_sec=4.0)
                return False
            if attr == "max_value":
                v = max(1, v)
                try:
                    cur = int(getattr(target, "value", 0) or 0)
                    if cur > v:
                        target.value = v
                except Exception:
                    pass
            if attr == "value":
                try:
                    mn = int(getattr(target, "min_value", 0) or 0)
                    mx = int(getattr(target, "max_value", 100) or 100)
                    v = max(mn, min(mx, v))
                except Exception:
                    pass
            setattr(target, attr, v)
        else:
            setattr(target, attr, raw)

        return _finish_ok(f"Updated {suffix}.")

    if len(selection) > 1:
        if f in {"x", "y"}:
            try:
                v = int(buf)
            except Exception:
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
            except Exception:
                app._set_status(f"Invalid {f}: {buf!r}", ttl_sec=4.0)
                return False
            bounds = app._selection_bounds(selection)
            if bounds is None:
                return False
            new_w = int(v) if f == "width" else int(bounds.width)
            new_h = int(v) if f == "height" else int(bounds.height)
            if not app._resize_selection_to(new_w, new_h):
                return False
        elif f in {"color_fg", "color_bg"}:
            if not app._is_valid_color_str(buf):
                app._set_status(f"Invalid {f}: {buf!r}", ttl_sec=4.0)
                return False
            try:
                app.designer._save_state()
            except Exception:
                pass
            for idx in selection:
                if 0 <= idx < len(sc.widgets):
                    setattr(sc.widgets[idx], f, buf)
        elif f == "align":
            val = buf.lower()
            if val not in {"left", "center", "right"}:
                app._set_status("align must be: left|center|right", ttl_sec=4.0)
                return False
            try:
                app.designer._save_state()
            except Exception:
                pass
            for idx in selection:
                if 0 <= idx < len(sc.widgets):
                    sc.widgets[idx].align = val
        elif f == "valign":
            val = buf.lower()
            if val not in {"top", "middle", "bottom"}:
                app._set_status("valign must be: top|middle|bottom", ttl_sec=4.0)
                return False
            try:
                app.designer._save_state()
            except Exception:
                pass
            for idx in selection:
                if 0 <= idx < len(sc.widgets):
                    sc.widgets[idx].valign = val
        elif f == "border_style":
            val = buf.lower()
            if val not in {"none", "single", "double", "rounded", "bold", "dashed"}:
                app._set_status("border_style: none|single|double|rounded|bold|dashed", ttl_sec=4.0)
                return False
            try:
                app.designer._save_state()
            except Exception:
                pass
            for idx in selection:
                if 0 <= idx < len(sc.widgets):
                    sc.widgets[idx].border_style = val
        elif f == "text_overflow":
            val = buf.lower()
            if val not in {"ellipsis", "wrap", "clip", "auto"}:
                app._set_status("text_overflow must be: ellipsis|wrap|clip|auto", ttl_sec=4.0)
                return False
            try:
                app.designer._save_state()
            except Exception:
                pass
            for idx in selection:
                if 0 <= idx < len(sc.widgets):
                    sc.widgets[idx].text_overflow = val
        elif f == "max_lines":
            try:
                ml = None if (not buf or buf == "0") else int(buf)
            except Exception:
                app._set_status(f"Invalid {f}: {buf!r}", ttl_sec=4.0)
                return False
            if ml is not None and ml <= 0:
                ml = None
            try:
                app.designer._save_state()
            except Exception:
                pass
            for idx in selection:
                if 0 <= idx < len(sc.widgets):
                    sc.widgets[idx].max_lines = ml
        elif f == "text":
            try:
                app.designer._save_state()
            except Exception:
                pass
            for idx in selection:
                if 0 <= idx < len(sc.widgets):
                    sc.widgets[idx].text = raw
        elif f == "runtime":
            try:
                app.designer._save_state()
            except Exception:
                pass
            for idx in selection:
                if 0 <= idx < len(sc.widgets):
                    sc.widgets[idx].runtime = raw
        elif f == "data_points":
            pts = parse_int_list(buf)
            if pts is None:
                app._set_status(f"Invalid {f}: {buf!r}", ttl_sec=4.0)
                return False
            try:
                app.designer._save_state()
            except Exception:
                pass
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
            try:
                app.designer._save_state()
            except Exception:
                pass
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
        else:
            app._set_status(f"Not editable: {field}", ttl_sec=3.0)
            app._inspector_cancel_edit()
            return True

        app.state.inspector_selected_field = None
        app.state.inspector_input_buffer = ""
        try:
            pygame.key.stop_text_input()
        except Exception:
            pass
        app._set_status(f"Updated {field}.", ttl_sec=2.0)
        app._mark_dirty()
        return True

    def _apply_int(attr: str, min_value: int = 0, max_value: Optional[int] = None) -> bool:
        try:
            v = int(buf)
        except Exception:
            app._set_status(f"Invalid {attr}: {buf!r}", ttl_sec=4.0)
            return False
        if app.snap_enabled and attr in {"x", "y", "width", "height"}:
            v = snap(v)
        v = max(min_value, v)
        if max_value is not None:
            v = min(max_value, v)
        try:
            setattr(w, attr, v)
        except Exception:
            return False
        return True

    if f == "text":
        try:
            app.designer._save_state()
        except Exception:
            pass
        w.text = raw
    elif f == "runtime":
        try:
            app.designer._save_state()
        except Exception:
            pass
        w.runtime = raw
    elif f in {"x", "y"}:
        try:
            app.designer._save_state()
        except Exception:
            pass
        max_x = max(0, int(sc.width) - int(w.width))
        max_y = max(0, int(sc.height) - int(w.height))
        if not _apply_int(f, min_value=0, max_value=max_x if f == "x" else max_y):
            return False
    elif f in {"width", "height"}:
        try:
            app.designer._save_state()
        except Exception:
            pass
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
        try:
            app.designer._save_state()
        except Exception:
            pass
        if not _apply_int(f, min_value=-1_000_000, max_value=1_000_000):
            return False
    elif f == "z_index":
        try:
            app.designer._save_state()
        except Exception:
            pass
        if not _apply_int("z_index", min_value=-1_000_000, max_value=1_000_000):
            return False
    elif f in {"color_fg", "color_bg"}:
        if not app._is_valid_color_str(buf):
            app._set_status(f"Invalid {f}: {buf!r}", ttl_sec=4.0)
            return False
        try:
            app.designer._save_state()
        except Exception:
            pass
        setattr(w, f, buf)
    elif f == "align":
        val = buf.lower()
        if val not in {"left", "center", "right"}:
            app._set_status("align must be: left|center|right", ttl_sec=4.0)
            return False
        try:
            app.designer._save_state()
        except Exception:
            pass
        w.align = val
    elif f == "valign":
        val = buf.lower()
        if val not in {"top", "middle", "bottom"}:
            app._set_status("valign must be: top|middle|bottom", ttl_sec=4.0)
            return False
        try:
            app.designer._save_state()
        except Exception:
            pass
        w.valign = val
    elif f == "border_style":
        val = buf.lower()
        if val not in {"none", "single", "double", "rounded", "bold", "dashed"}:
            app._set_status("border_style: none|single|double|rounded|bold|dashed", ttl_sec=4.0)
            return False
        try:
            app.designer._save_state()
        except Exception:
            pass
        w.border_style = val
    elif f == "text_overflow":
        val = buf.lower()
        if val not in {"ellipsis", "wrap", "clip", "auto"}:
            app._set_status("text_overflow must be: ellipsis|wrap|clip|auto", ttl_sec=4.0)
            return False
        try:
            app.designer._save_state()
        except Exception:
            pass
        w.text_overflow = val
    elif f == "max_lines":
        try:
            app.designer._save_state()
        except Exception:
            pass
        if not buf or buf == "0":
            w.max_lines = None
        else:
            try:
                ml = int(buf)
            except Exception:
                app._set_status(f"Invalid {f}: {buf!r}", ttl_sec=4.0)
                return False
            w.max_lines = ml if ml > 0 else None
    elif f == "data_points":
        pts = parse_int_list(buf)
        if pts is None:
            app._set_status(f"Invalid {f}: {buf!r}", ttl_sec=4.0)
            return False
        try:
            app.designer._save_state()
        except Exception:
            pass
        w.data_points = pts
    elif f == "chart_mode":
        val = buf.lower()
        if val not in {"bar", "line"}:
            app._set_status("chart_mode must be: bar|line", ttl_sec=4.0)
            return False
        try:
            app.designer._save_state()
        except Exception:
            pass
        w.style = val
    else:
        app._set_status(f"Not editable: {field}", ttl_sec=3.0)
        app._inspector_cancel_edit()
        return True

    app.state.inspector_selected_field = None
    app.state.inspector_input_buffer = ""
    try:
        pygame.key.stop_text_input()
    except Exception:
        pass
    app._set_status(f"Updated {field}.", ttl_sec=2.0)
    app._mark_dirty()
    return True


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
    rows.append(("profile", f"profile: {profile_label or 'none'}"))
    rows.append(("resources", f"resources: {res_text}"))
    if overlaps:
        rows.append(("overlaps", f"overlaps: {overlaps}"))
    live_row = "Live: off"
    if app.live_preview_port:
        live_row = f"Live: {app.live_preview_port}@{app.live_preview_baud}"
    rows.append(("live", f"live: {live_row}"))
    sc = app.state.current_scene()
    selection = list(getattr(app.state, "selected", []) or [])

    def _mixed_str(values: List[str]) -> str:
        uniq = sorted(set([str(v or "") for v in values if str(v or "")]))
        if len(uniq) == 1:
            return uniq[0]
        if not uniq:
            return ""
        return "(mixed)"

    if selection:
        if len(selection) > 1:
            widgets = [sc.widgets[i] for i in selection if 0 <= i < len(sc.widgets)]
            bounds = app._selection_bounds(selection)
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
                    f"max_lines: {'' if getattr(w, 'max_lines', None) is None else int(getattr(w, 'max_lines'))}",
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
            if w.type == "checkbox":
                rows.append(("checked", f"checked: {bool(getattr(w, 'checked', False))}"))
            if w.type in {"progressbar", "slider", "gauge"}:
                rows.append(("value", f"value: {int(getattr(w, 'value', 0) or 0)}"))
                rows.append(("min_value", f"min_value: {int(getattr(w, 'min_value', 0) or 0)}"))
                rows.append(("max_value", f"max_value: {int(getattr(w, 'max_value', 100) or 0)}"))
        else:
            rows.append(("none", "selection: none"))
    else:
        rows.append(("none", "selection: none"))

    rows.append(("snapgrid", f"snap: {bool(app.snap_enabled)}  grid: {bool(app.show_grid)}"))
    rows.append(("panels", f"panels: {'off' if app.panels_collapsed else 'on'}"))
    if sc.widgets:
        rows.append(("layers_header", "layers:"))

        try:
            groups = dict(getattr(app.designer, "groups", {}) or {})
        except Exception:
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
                        continue
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
