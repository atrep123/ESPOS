from __future__ import annotations

from typing import List, Tuple

import pygame

from . import focus_nav, layout_tools
from .constants import GRID, snap


def on_key_down(app, event: pygame.event.Event) -> None:
    """Handle key down event."""
    if event.key == pygame.K_F1:
        app._toggle_help_overlay()
        return

    if bool(getattr(app, "show_help_overlay", False)) and bool(getattr(app, "_help_pinned", False)):
        if event.key == pygame.K_ESCAPE:
            app._set_help_overlay(False)
        return
    if bool(getattr(app, "show_help_overlay", False)):
        # Auto-shown hint: dismiss on first input, but don't swallow the action.
        app._set_help_overlay(False)

    if app.state.inspector_selected_field:
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            app._inspector_commit_edit()
            return
        if event.key == pygame.K_ESCAPE:
            app._inspector_cancel_edit()
            return
        if event.key == pygame.K_BACKSPACE:
            app.state.inspector_input_buffer = app.state.inspector_input_buffer[:-1]
            app._mark_dirty()
            return
        # Ignore global shortcuts while editing.
        return

    mods = pygame.key.get_mods()
    if (mods & pygame.KMOD_CTRL) and (mods & pygame.KMOD_ALT) and not app.sim_input_mode:
        if event.key == pygame.K_LEFT:
            layout_tools.align_selection(app, "left")
            return
        if event.key == pygame.K_RIGHT:
            layout_tools.align_selection(app, "right")
            return
        if event.key == pygame.K_UP:
            layout_tools.align_selection(app, "top")
            return
        if event.key == pygame.K_DOWN:
            layout_tools.align_selection(app, "bottom")
            return
        if event.key == pygame.K_h:
            layout_tools.distribute_selection(app, "h")
            return
        if event.key == pygame.K_v:
            layout_tools.distribute_selection(app, "v")
            return
        if event.key == pygame.K_w:
            layout_tools.match_size_selection(app, "width")
            return
        if event.key == pygame.K_t:
            layout_tools.match_size_selection(app, "height")
            return
        if event.key == pygame.K_c:
            layout_tools.center_selection_in_scene(app, "both")
            return
    if event.key == pygame.K_F2:
        app.sim_input_mode = not app.sim_input_mode
        app.focus_edit_value = False
        if app.sim_input_mode:
            focus_nav.sim_runtime_reset(app)
            app._ensure_focus()
            if app.focus_idx is not None:
                app._set_focus(app.focus_idx, sync_selection=True)
            app._set_status("Input mode: ON (F2=exit Enter=A Backspace/Esc=B)", ttl_sec=4.0)
        else:
            focus_nav.sim_runtime_restore(app)
            app._set_status("Input mode: OFF", ttl_sec=2.0)
        app._mark_dirty()
        return

    if event.key == pygame.K_ESCAPE:
        if app.sim_input_mode:
            if app.focus_edit_value:
                app.focus_edit_value = False
                app._set_status("B: exit edit", ttl_sec=2.0)
            else:
                app._set_status("B pressed", ttl_sec=1.5)
            app._mark_dirty()
            return
        app.running = False
    elif app.sim_input_mode and event.key == pygame.K_BACKSPACE:
        if app.focus_edit_value:
            app.focus_edit_value = False
            app._set_status("B: exit edit", ttl_sec=2.0)
        else:
            app._set_status("B pressed", ttl_sec=1.5)
        app._mark_dirty()
        return
    elif event.key == pygame.K_s and mods & pygame.KMOD_CTRL:
        app.save_json()
    elif event.key == pygame.K_l and mods & pygame.KMOD_CTRL:
        app.load_json()
    elif event.key == pygame.K_c and mods & pygame.KMOD_CTRL:
        app._copy_selection()
    elif event.key == pygame.K_x and mods & pygame.KMOD_CTRL:
        app._cut_selection()
    elif event.key == pygame.K_z and mods & pygame.KMOD_CTRL:
        if mods & pygame.KMOD_SHIFT:
            if app.designer.redo():
                app.state.selected_idx = None
                app.state.selected = []
                app._mark_dirty()
        else:
            if app.designer.undo():
                app.state.selected_idx = None
                app.state.selected = []
                app._mark_dirty()
    elif event.key == pygame.K_y and mods & pygame.KMOD_CTRL:
        if app.designer.redo():
            app.state.selected_idx = None
            app.state.selected = []
            app._mark_dirty()
    elif event.key == pygame.K_v and mods & pygame.KMOD_CTRL:
        app._paste_clipboard()
    elif event.key == pygame.K_d and mods & pygame.KMOD_CTRL:
        app._duplicate_selection()
    elif event.key == pygame.K_f and mods & pygame.KMOD_CTRL:
        if mods & pygame.KMOD_SHIFT:
            app._fit_selection_to_widget()
        else:
            app._fit_selection_to_text()
    elif event.key == pygame.K_a and mods & pygame.KMOD_CTRL:
        app._select_all()
    elif event.key == pygame.K_DELETE:
        app._delete_selected()
    elif event.key == pygame.K_F3:
        app._toggle_overflow_warnings()
    elif event.key == pygame.K_g and mods & pygame.KMOD_CTRL:
        if mods & pygame.KMOD_SHIFT:
            app._ungroup_selection()
        else:
            app._group_selection()
        app._mark_dirty()
    elif event.key == pygame.K_g:
        app.show_grid = not app.show_grid
        app._mark_dirty()
    elif event.key == pygame.K_x:
        app.snap_enabled = not app.snap_enabled
        app._mark_dirty()
    elif event.key == pygame.K_TAB:
        app._toggle_panels()
        app._mark_dirty()
    elif event.key == pygame.K_F11:
        app._toggle_fullscreen()
        app._mark_dirty()
    elif event.key == pygame.K_F12:
        app._screenshot_canvas()
    elif event.key == pygame.K_F5:
        app._send_live_preview()
    elif event.key == pygame.K_EQUALS and mods & pygame.KMOD_CTRL:
        app._set_scale(app.scale + 1)
    elif event.key == pygame.K_MINUS and mods & pygame.KMOD_CTRL:
        app._set_scale(app.scale - 1)
    elif event.key == pygame.K_0 and mods & pygame.KMOD_CTRL:
        app._reset_zoom()
    elif app.sim_input_mode and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        if mods & pygame.KMOD_SHIFT:
            app._set_status("Hold pressed (not bound yet)", ttl_sec=2.0)
        else:
            app._activate_focused()
        return
    elif app.sim_input_mode and event.key == pygame.K_SPACE:
        app._activate_focused()
        return
    elif app.sim_input_mode and event.key == pygame.K_PAGEUP:
        step = 5 if mods & pygame.KMOD_SHIFT else 1
        app._adjust_focused_value(step)
        return
    elif app.sim_input_mode and event.key == pygame.K_PAGEDOWN:
        step = 5 if mods & pygame.KMOD_SHIFT else 1
        app._adjust_focused_value(-step)
        return
    elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
        if app.sim_input_mode:
            if app.focus_edit_value and event.key in (pygame.K_UP, pygame.K_DOWN):
                step = 5 if mods & pygame.KMOD_SHIFT else 1
                app._adjust_focused_value(step if event.key == pygame.K_DOWN else -step)
                return
            if event.key == pygame.K_LEFT:
                app._focus_move_direction("left")
            elif event.key == pygame.K_RIGHT:
                app._focus_move_direction("right")
            elif event.key == pygame.K_UP:
                app._focus_move_direction("up")
            elif event.key == pygame.K_DOWN:
                app._focus_move_direction("down")
            app._mark_dirty()
            return

        if not app.state.selected:
            return
        step = GRID if app.snap_enabled else 1
        if mods & pygame.KMOD_SHIFT:
            step *= 4
        dx = 0
        dy = 0
        if event.key == pygame.K_LEFT:
            dx = -step
        elif event.key == pygame.K_RIGHT:
            dx = step
        elif event.key == pygame.K_UP:
            dy = -step
        elif event.key == pygame.K_DOWN:
            dy = step
        app._move_selection(dx, dy)


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
                    except Exception:
                        pass
                    return
                for label, action in app.toolbar_actions:
                    if label.lower() == key and action:
                        action()
                        return
        return

    # Palette click (actions + widget list)
    if app.layout.palette_rect.collidepoint(lx, ly):
        if not getattr(app, "palette_hitboxes", None):
            app._draw_palette()
        for idx, (rect, _label, enabled) in enumerate(getattr(app, "palette_hitboxes", [])):
            if rect.collidepoint(lx, ly) and enabled:
                try:
                    _act = app.palette_actions[idx][1]
                    if _act:
                        _act()
                except Exception:
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
                except Exception:
                    return
                sc = app.state.current_scene()
                if 0 <= idx < len(sc.widgets):
                    app._apply_click_selection(idx, mods)
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
                try:
                    app.designer._save_state()
                except Exception:
                    pass
                default = True if key in {"border", "visible", "enabled"} else False
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
        app.state.dragging = True
        app.state.resizing = False
        app.state.resize_anchor = None

    if not app.state.saved_this_drag:
        try:
            app.designer._save_state()
        except Exception:
            pass
        app.state.saved_this_drag = True


def on_mouse_up(app, _pos: Tuple[int, int]) -> None:
    app.state.dragging = False
    app.state.resizing = False
    app.state.resize_anchor = None
    app.state.saved_this_drag = False
    try:
        layout_tools.clear_active_guides(app)
    except Exception:
        pass
    app.state.drag_start_positions.clear()
    app.state.drag_start_sizes.clear()
    app.state.drag_start_rect = None
    app.state.resize_start_rect = None


def on_mouse_move(app, pos: Tuple[int, int], _buttons: Tuple[int, int, int]) -> None:
    """Handle mouse move; apply drag/resize when active."""
    if not app.pointer_down:
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
        except Exception:
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
        except Exception:
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
        except Exception:
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
            ix = int(round(nx))
            iy = int(round(ny))
            iw = max(GRID, int(round(nw)))
            ih = max(GRID, int(round(nh)))
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
    """Scroll palette/inspector panels."""
    if dy == 0:
        return
    if bool(getattr(app, "show_help_overlay", False)):
        pinned = bool(getattr(app, "_help_pinned", False))
        app._set_help_overlay(False)
        if pinned:
            return
    step = max(GRID, int(app.pixel_row_height))
    header_h = int(getattr(app, "pixel_row_height", 0) or 0)
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
