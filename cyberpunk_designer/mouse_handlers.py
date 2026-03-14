"""Mouse event processing handlers."""

from __future__ import annotations

from typing import List, Tuple

import pygame

from . import layout_tools
from .constants import GRID, safe_save_state, snap


def on_mouse_down(app, pos: Tuple[int, int]) -> None:
    """Handle mouse down (toolbar/palette/inspector/canvas)."""
    lx, ly = pos
    mods = pygame.key.get_mods()

    if bool(getattr(app, "show_help_overlay", False)):
        pinned = bool(getattr(app, "_help_pinned", False))
        app._set_help_overlay(False)
        if pinned:
            return

    if app.state.inspector_selected_field and not app.layout.inspector_rect.collidepoint(lx, ly):
        if not app._inspector_commit_edit():
            return

    # Toolbar click
    if app.layout.toolbar_rect.collidepoint(lx, ly):
        if not getattr(app, "toolbar_hitboxes", None):
            app._draw_toolbar()
        for rect, key in getattr(app, "toolbar_hitboxes", []):
            if rect.collidepoint(lx, ly):
                if key == "refresh_ports":
                    try:
                        app._refresh_available_ports()
                    except OSError:
                        pass
                    return
                for label, action in app.toolbar_actions:
                    if label.lower() == key and action:
                        action()
                        return
        return

    # Scene tab click
    if app.layout.scene_tabs_rect.collidepoint(lx, ly):
        # Scroll arrows
        for rect, direction in getattr(app, "tab_scroll_hitboxes", []):
            if rect.collidepoint(lx, ly):
                scroll = int(getattr(app, "_tab_scroll", 0) or 0)
                step = 40
                app._tab_scroll = max(0, scroll + direction * step)
                app._mark_dirty()
                return
        # Close button (x) on tab
        for rect, tab_idx, _tab_name in getattr(app, "tab_close_hitboxes", []):
            if rect.collidepoint(lx, ly):
                app._jump_to_scene(tab_idx)
                app._delete_current_scene()
                return
        for rect, tab_idx, tab_name in getattr(app, "tab_hitboxes", []):
            if rect.collidepoint(lx, ly):
                if tab_idx == -1:
                    # "+ New" button
                    app._add_new_scene()
                else:
                    app._jump_to_scene(tab_idx)
                    # Start tab drag
                    app._tab_drag_idx = tab_idx
                    app._tab_drag_name = tab_name
                return
        return

    # Palette click (actions + widget list)
    if app.layout.palette_rect.collidepoint(lx, ly):
        if not getattr(app, "palette_hitboxes", None):
            app._draw_palette()
        # Section header toggle
        for rect, sec_name in getattr(app, "palette_section_hitboxes", []):
            if rect.collidepoint(lx, ly):
                collapsed = getattr(app, "palette_collapsed", set())
                if sec_name in collapsed:
                    collapsed.discard(sec_name)
                else:
                    collapsed.add(sec_name)
                app._mark_dirty()
                return
        # Action items — match by flat index across visible sections
        for idx, (rect, _label, enabled) in enumerate(getattr(app, "palette_hitboxes", [])):
            if rect.collidepoint(lx, ly) and enabled:
                try:
                    # Find the actual action from palette_sections
                    flat_idx = 0
                    collapsed = getattr(app, "palette_collapsed", set())
                    for sec_name, items in getattr(app, "palette_sections", []):
                        if sec_name in collapsed:
                            continue
                        for _lbl, act in items:
                            if flat_idx == idx:
                                if act:
                                    act()
                                return
                            flat_idx += 1
                except (IndexError, TypeError, AttributeError):
                    pass
                return
        for rect, widget_idx in getattr(app, "palette_widget_hitboxes", []):
            if rect.collidepoint(lx, ly):
                sc = app.state.current_scene()
                if 0 <= widget_idx < len(sc.widgets):
                    app._apply_click_selection(widget_idx, mods)
                return
        return

    # Inspector click (layer list select)
    if app.layout.inspector_rect.collidepoint(lx, ly):
        # Section header toggle
        for rect, sec_name in getattr(app, "inspector_section_hitboxes", []):
            if rect.collidepoint(lx, ly):
                collapsed = getattr(app, "inspector_collapsed", set())
                if sec_name in collapsed:
                    collapsed.discard(sec_name)
                else:
                    collapsed.add(sec_name)
                app._mark_dirty()
                return
        if not getattr(app, "inspector_hitboxes", None):
            app._draw_inspector()
        for rect, key in getattr(app, "inspector_hitboxes", []):
            if not rect.collidepoint(lx, ly):
                continue
            if key.startswith("group:"):
                if app.state.inspector_selected_field:
                    if not app._inspector_commit_edit():
                        return
                gname = key.split(":", 1)[1]
                members = app._group_members(gname)
                if members:
                    app._set_selection(members, anchor_idx=members[0])
                    app._set_status(f"Selected {gname} ({len(members)}).", ttl_sec=2.0)
                    app._mark_dirty()
                return
            if key.startswith("layer:"):
                if app.state.inspector_selected_field:
                    if not app._inspector_commit_edit():
                        return
                try:
                    idx = int(key.split(":", 1)[1])
                except (ValueError, TypeError):
                    return
                sc = app.state.current_scene()
                if 0 <= idx < len(sc.widgets):
                    app._apply_click_selection(idx, mods)
                    # Start layer drag for reorder
                    app._layer_drag_idx = idx
                return
            toggles = {"border", "visible", "enabled", "locked", "checked"}
            editable = {
                "text",
                "runtime",
                "x",
                "y",
                "width",
                "height",
                "text_overflow",
                "max_lines",
                "value",
                "min_value",
                "max_value",
                "z_index",
                "color_fg",
                "color_bg",
                "align",
                "valign",
                "border_style",
                "data_points",
                "chart_mode",
            }
            if key in toggles:
                if app.state.inspector_selected_field:
                    if not app._inspector_commit_edit():
                        return
                if not app.state.selected:
                    app._set_status("No selection.", ttl_sec=2.0)
                    return
                sc = app.state.current_scene()
                safe_save_state(app.designer)
                default = key in {"border", "visible", "enabled"}
                values: List[bool] = []
                for idx in app.state.selected:
                    if not (0 <= idx < len(sc.widgets)):
                        continue
                    ww = sc.widgets[idx]
                    if key == "checked" and str(getattr(ww, "type", "")).lower() != "checkbox":
                        continue
                    values.append(bool(getattr(ww, key, default)))
                if not values:
                    app._set_status("Nothing to toggle.", ttl_sec=2.0)
                    return
                new_val = not all(values)
                for idx in app.state.selected:
                    if not (0 <= idx < len(sc.widgets)):
                        continue
                    ww = sc.widgets[idx]
                    if key == "checked" and str(getattr(ww, "type", "")).lower() != "checkbox":
                        continue
                    setattr(ww, key, new_val)
                app._set_status(f"{key}: {'on' if new_val else 'off'}", ttl_sec=2.0)
                app._mark_dirty()
                return
            if key.startswith("comp.") or key in editable:
                if app.state.inspector_selected_field == key:
                    return
                if app.state.inspector_selected_field and app.state.inspector_selected_field != key:
                    if not app._inspector_commit_edit():
                        return
                app._inspector_start_edit(key)
                return
        return

    # Canvas click: selection + drag/resize
    cr = app.layout.canvas_rect
    if not cr.collidepoint(lx, ly):
        return
    sr = getattr(app, "scene_rect", cr)
    if not isinstance(sr, pygame.Rect):
        sr = cr

    # In device input simulation mode, clicking only sets focus (no dragging/resizing).
    if app.sim_input_mode:
        hit = app.state.hit_test_at((lx, ly), sr)
        if hit is None:
            return
        sc = app.state.current_scene()
        if 0 <= hit < len(sc.widgets) and app._is_widget_focusable(sc.widgets[hit]):
            app._set_focus(hit, sync_selection=True)
            app._mark_dirty()
        return

    hit = app.state.hit_test_at((lx, ly), sr)
    if hit is None:
        app._set_selection([], anchor_idx=None)
        # Start box select on empty canvas
        app.state.box_select_start = (lx, ly)
        app.state.box_select_rect = None
        return
    app._apply_click_selection(hit, mods)
    if not app.state.selected:
        return
    if mods & pygame.KMOD_CTRL:
        return
    sc = app.state.current_scene()
    if any(bool(getattr(sc.widgets[i], "locked", False)) for i in app.state.selected):
        app._set_status("Selection contains locked widget(s).", ttl_sec=2.0)
        return

    bounds = app._selection_bounds(app.state.selected)
    if bounds is None:
        return

    mx = lx - sr.x
    my = ly - sr.y
    app.state.drag_offset = (int(mx - bounds.x), int(my - bounds.y))
    app.state.drag_start_rect = bounds.copy()
    app.state.drag_start_positions = {
        i: (int(getattr(sc.widgets[i], "x", 0) or 0), int(getattr(sc.widgets[i], "y", 0) or 0))
        for i in app.state.selected
        if 0 <= i < len(sc.widgets)
    }
    app.state.drag_start_sizes = {
        i: (
            int(getattr(sc.widgets[i], "width", GRID) or GRID),
            int(getattr(sc.widgets[i], "height", GRID) or GRID),
        )
        for i in app.state.selected
        if 0 <= i < len(sc.widgets)
    }
    app.state.resize_start_rect = bounds.copy()

    handle = pygame.Rect(
        sr.x + bounds.x + bounds.width - GRID,
        sr.y + bounds.y + bounds.height - GRID,
        GRID,
        GRID,
    )
    if handle.collidepoint(lx, ly):
        app.state.resizing = True
        app.state.dragging = False
        app.state.resize_anchor = "br"
    else:
        # Alt+drag = clone selection first, then drag the clones
        if mods & pygame.KMOD_ALT:
            from dataclasses import asdict

            from ui_designer import WidgetConfig

            new_indices: List[int] = []
            for idx in list(app.state.selected):
                if 0 <= idx < len(sc.widgets):
                    nw = WidgetConfig(**asdict(sc.widgets[idx]))
                    sc.widgets.append(nw)
                    new_indices.append(len(sc.widgets) - 1)
            if new_indices:
                app.state.selected = new_indices
                app.state.selected_idx = new_indices[0]
                app.designer.selected_widget = new_indices[0]
                # Rebuild drag positions for the new clones
                bounds = app._selection_bounds(new_indices)
                if bounds:
                    app.state.drag_start_rect = bounds.copy()
                    app.state.resize_start_rect = bounds.copy()
                    app.state.drag_start_positions = {
                        i: (int(sc.widgets[i].x), int(sc.widgets[i].y))
                        for i in new_indices
                        if 0 <= i < len(sc.widgets)
                    }
                    app.state.drag_start_sizes = {
                        i: (int(sc.widgets[i].width), int(sc.widgets[i].height))
                        for i in new_indices
                        if 0 <= i < len(sc.widgets)
                    }
                app._set_status(f"Cloned {len(new_indices)} widget(s)", ttl_sec=1.5)
        app.state.dragging = True
        app.state.resizing = False
        app.state.resize_anchor = None

    if not app.state.saved_this_drag:
        safe_save_state(app.designer)
        app.state.saved_this_drag = True


def on_mouse_up(app, _pos: Tuple[int, int]) -> None:
    # Finish box select
    if app.state.box_select_start is not None and app.state.box_select_rect is not None:
        _finish_box_select(app)
    app.state.box_select_start = None
    app.state.box_select_rect = None

    # Clear tab drag
    app._tab_drag_idx = None
    app._tab_drag_name = None

    # Clear layer drag
    app._layer_drag_idx = None

    app.state.dragging = False
    app.state.resizing = False
    app.state.resize_anchor = None
    app.state.saved_this_drag = False
    try:
        layout_tools.clear_active_guides(app)
    except AttributeError:
        pass
    app.state.drag_start_positions.clear()
    app.state.drag_start_sizes.clear()
    app.state.drag_start_rect = None
    app.state.resize_start_rect = None


def _finish_box_select(app) -> None:
    """Complete rubber-band selection: select all widgets that intersect the rect."""
    rect = app.state.box_select_rect
    if rect is None or rect.width < 4 or rect.height < 4:
        return
    sr = getattr(app, "scene_rect", app.layout.canvas_rect)
    if not isinstance(sr, pygame.Rect):
        sr = app.layout.canvas_rect
    sc = app.state.current_scene()
    hits: List[int] = []
    for idx, w in enumerate(sc.widgets):
        if not getattr(w, "visible", True):
            continue
        wr = pygame.Rect(int(w.x) + sr.x, int(w.y) + sr.y, int(w.width), int(w.height))
        if rect.colliderect(wr):
            hits.append(idx)
    if hits:
        app._set_selection(hits, anchor_idx=hits[0])
        app._set_status(f"Selected {len(hits)} widget(s)", ttl_sec=1.5)
    app._mark_dirty()


def on_mouse_move(app, pos: Tuple[int, int], _buttons: Tuple[int, int, int]) -> None:
    """Handle mouse move; apply drag/resize when active."""
    if not app.pointer_down:
        return

    # Tab drag reorder
    drag_idx = getattr(app, "_tab_drag_idx", None)
    if drag_idx is not None:
        lx, ly = pos
        for rect, tab_idx, _tab_name in getattr(app, "tab_hitboxes", []):
            if tab_idx >= 0 and tab_idx != drag_idx and rect.collidepoint(lx, ly):
                names = list(app.designer.scenes.keys())
                if 0 <= drag_idx < len(names) and 0 <= tab_idx < len(names):
                    # Swap adjacent positions by rebuilding dict
                    ordered = list(names)
                    name = ordered.pop(drag_idx)
                    ordered.insert(tab_idx, name)
                    app.designer.scenes = {n: app.designer.scenes[n] for n in ordered}
                    app._tab_drag_idx = tab_idx
                    app._mark_dirty()
                break
        return

    # Layer drag reorder in inspector
    layer_drag = getattr(app, "_layer_drag_idx", None)
    if layer_drag is not None:
        lx, ly = pos
        for rect, key in getattr(app, "inspector_hitboxes", []):
            if not key.startswith("layer:") or not rect.collidepoint(lx, ly):
                continue
            try:
                target = int(key.split(":", 1)[1])
            except (ValueError, TypeError):
                continue
            if target != layer_drag:
                sc = app.state.current_scene()
                if 0 <= layer_drag < len(sc.widgets) and 0 <= target < len(sc.widgets):
                    w = sc.widgets.pop(layer_drag)
                    sc.widgets.insert(target, w)
                    # Update selection to follow the moved widget
                    app.state.selected = [target]
                    app.state.selected_idx = target
                    app._layer_drag_idx = target
                    app._mark_dirty()
            break
        return

    # Box select (rubber band)
    if app.state.box_select_start is not None:
        sx, sy = app.state.box_select_start
        ex, ey = pos
        x0, x1 = min(sx, ex), max(sx, ex)
        y0, y1 = min(sy, ey), max(sy, ey)
        app.state.box_select_rect = pygame.Rect(x0, y0, max(1, x1 - x0), max(1, y1 - y0))
        app._dirty = True
        return

    cr = app.layout.canvas_rect
    sr = getattr(app, "scene_rect", cr)
    if not isinstance(sr, pygame.Rect):
        sr = cr
    sc = app.state.current_scene()
    if not app.state.selected:
        return
    if any(
        bool(getattr(sc.widgets[i], "locked", False))
        for i in app.state.selected
        if 0 <= i < len(sc.widgets)
    ):
        return

    mx = max(0, min(int(sc.width), int(pos[0] - sr.x)))
    my = max(0, min(int(sc.height), int(pos[1] - sr.y)))

    if app.state.dragging:
        start_rect = app.state.drag_start_rect
        if start_rect is None:
            return
        new_x = int(mx - app.state.drag_offset[0])
        new_y = int(my - app.state.drag_offset[1])
        if app.snap_enabled:
            new_x = snap(new_x)
            new_y = snap(new_y)
        max_x = max(0, int(sc.width) - int(start_rect.width))
        max_y = max(0, int(sc.height) - int(start_rect.height))
        new_x = max(0, min(max_x, new_x))
        new_y = max(0, min(max_y, new_y))
        if app.snap_enabled:
            new_x = snap(new_x)
            new_y = snap(new_y)
            new_x = max(0, min(max_x, new_x))
            new_y = max(0, min(max_y, new_y))
        try:
            new_x, new_y = layout_tools.snap_drag_to_guides(app, new_x, new_y, start_rect)
        except (ValueError, TypeError):
            pass
        new_x = max(0, min(max_x, int(new_x)))
        new_y = max(0, min(max_y, int(new_y)))
        if app.snap_enabled:
            new_x = snap(int(new_x))
            new_y = snap(int(new_y))
            new_x = max(0, min(max_x, int(new_x)))
            new_y = max(0, min(max_y, int(new_y)))
        dx = int(new_x - int(start_rect.x))
        dy = int(new_y - int(start_rect.y))
        for idx in app.state.selected:
            if idx not in app.state.drag_start_positions:
                continue
            if not (0 <= idx < len(sc.widgets)):
                continue
            sx, sy = app.state.drag_start_positions[idx]
            sc.widgets[idx].x = int(sx + dx)
            sc.widgets[idx].y = int(sy + dy)
        app._dirty = True
        return

    if app.state.resizing and (app.state.resize_anchor == "br"):
        try:
            layout_tools.clear_active_guides(app)
        except AttributeError:
            pass
        start_rect = app.state.resize_start_rect
        if start_rect is None:
            return
        new_w = int(mx - int(start_rect.x))
        new_h = int(my - int(start_rect.y))
        if app.snap_enabled:
            new_w = max(GRID, snap(new_w))
            new_h = max(GRID, snap(new_h))
        else:
            new_w = max(GRID, new_w)
            new_h = max(GRID, new_h)
        max_w = max(GRID, int(sc.width) - int(start_rect.x))
        max_h = max(GRID, int(sc.height) - int(start_rect.y))
        new_w = max(GRID, min(max_w, new_w))
        new_h = max(GRID, min(max_h, new_h))

        try:
            sx = float(new_w) / float(max(1, int(start_rect.width)))
            sy = float(new_h) / float(max(1, int(start_rect.height)))
        except (ValueError, TypeError):
            sx, sy = 1.0, 1.0

        for idx in app.state.selected:
            if idx not in app.state.drag_start_positions or idx not in app.state.drag_start_sizes:
                continue
            if not (0 <= idx < len(sc.widgets)):
                continue
            ox, oy = app.state.drag_start_positions[idx]
            ow, oh = app.state.drag_start_sizes[idx]
            rel_x = float(ox - int(start_rect.x))
            rel_y = float(oy - int(start_rect.y))
            nx = float(int(start_rect.x)) + rel_x * sx
            ny = float(int(start_rect.y)) + rel_y * sy
            nw = float(int(ow)) * sx
            nh = float(int(oh)) * sy
            ix = round(nx)
            iy = round(ny)
            iw = max(GRID, round(nw))
            ih = max(GRID, round(nh))
            if app.snap_enabled:
                ix = snap(ix)
                iy = snap(iy)
                iw = max(GRID, snap(iw))
                ih = max(GRID, snap(ih))
            max_ix = max(0, int(sc.width) - iw)
            max_iy = max(0, int(sc.height) - ih)
            ix = max(0, min(max_ix, ix))
            iy = max(0, min(max_iy, iy))
            w = sc.widgets[idx]
            w.x = ix
            w.y = iy
            w.width = iw
            w.height = ih
        app._dirty = True


def on_mouse_wheel(app, _dx: int, dy: int) -> None:
    """Scroll palette/inspector panels, or zoom canvas."""
    if dy == 0:
        return
    if bool(getattr(app, "show_help_overlay", False)):
        pinned = bool(getattr(app, "_help_pinned", False))
        app._set_help_overlay(False)
        if pinned:
            return
    step = max(GRID, int(app.pixel_row_height))
    header_h = int(getattr(app, "pixel_row_height", 0) or 0)
    # Scroll wheel over scene tabs: switch scenes
    if app.layout.scene_tabs_rect.collidepoint(app.pointer_pos):
        app._switch_scene(-1 if dy > 0 else 1)
        return
    if app.layout.palette_rect.collidepoint(app.pointer_pos):
        view_h = max(0, int(app.layout.palette_rect.height) - header_h)
        max_scroll = max(0, int(app._palette_content_height()) - view_h)
        app.state.palette_scroll = max(
            0, min(max_scroll, int(app.state.palette_scroll) - dy * step)
        )
        return
    if app.layout.inspector_rect.collidepoint(app.pointer_pos):
        view_h = max(0, int(app.layout.inspector_rect.height) - header_h)
        max_scroll = max(0, int(app._inspector_content_height()) - view_h)
        app.state.inspector_scroll = max(
            0, min(max_scroll, int(app.state.inspector_scroll) - dy * step)
        )
        return
    # Scroll wheel on canvas: zoom in/out
    cr = app.layout.canvas_rect
    if cr.collidepoint(app.pointer_pos):
        new_scale = int(getattr(app, "scale", 2) or 2) + (1 if dy > 0 else -1)
        app._set_scale(new_scale)
        return
