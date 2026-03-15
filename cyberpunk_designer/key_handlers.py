"""Keyboard event processing handlers."""

from __future__ import annotations

import pygame

from . import focus_nav, layout_tools
from .constants import GRID

# Ctrl+Alt key dispatch: key → (method_name, *args)
_CTRL_ALT_TABLE = {
    pygame.K_LEFT: ("align_selection", "left"),
    pygame.K_RIGHT: ("align_selection", "right"),
    pygame.K_UP: ("align_selection", "top"),
    pygame.K_DOWN: ("align_selection", "bottom"),
    pygame.K_h: ("distribute_selection", "h"),
    pygame.K_v: ("distribute_selection", "v"),
    pygame.K_w: ("match_size_selection", "width"),
    pygame.K_t: ("match_size_selection", "height"),
    pygame.K_c: ("center_selection_in_scene", "both"),
}

# Ctrl+Alt actions dispatched directly on app (no args from table):
_CTRL_ALT_APP_TABLE = {
    pygame.K_e: "_equalize_gaps",
    pygame.K_g: "_grid_arrange",
    pygame.K_r: "_reverse_widget_order",
    pygame.K_f: "_flip_vertical",
    pygame.K_n: "_normalize_sizes",
    pygame.K_a: "_auto_name_scene",
    pygame.K_b: "_propagate_border",
    pygame.K_d: "_remove_duplicates",
    pygame.K_i: "_increment_text",
    pygame.K_p: "_propagate_style",
    pygame.K_x: "_swap_content",
    pygame.K_o: "_outline_mode",
    pygame.K_l: "_clone_text",
    pygame.K_j: "_propagate_align",
    pygame.K_k: "_propagate_colors",
    pygame.K_m: "_flip_horizontal",
    pygame.K_q: "_propagate_value",
    pygame.K_u: "_propagate_padding",
    pygame.K_y: "_propagate_margin",
    pygame.K_z: "_propagate_appearance",
}

# Shift+F-key dispatch: key → method_name on app
_SHIFT_FKEY_TABLE = {
    pygame.K_F1: "_create_header_bar",
    pygame.K_F2: "_create_nav_row",
    pygame.K_F3: "_create_form_pair",
    pygame.K_F4: "_create_status_bar",
    pygame.K_F5: "_create_toggle_group",
    pygame.K_F6: "_create_slider_with_label",
    pygame.K_F7: "_create_gauge_panel",
    pygame.K_F8: "_create_progress_section",
    pygame.K_F9: "_create_icon_button_row",
    pygame.K_F11: "_create_card_layout",
    pygame.K_F12: "_create_dashboard_grid",
}

# Number keys → widget type (no mods, not sim mode)
_NUMBER_WIDGET_TABLE = {
    pygame.K_1: "label",
    pygame.K_2: "button",
    pygame.K_3: "panel",
    pygame.K_4: "progressbar",
    pygame.K_5: "gauge",
    pygame.K_6: "slider",
    pygame.K_7: "checkbox",
    pygame.K_8: "chart",
    pygame.K_9: "icon",
    pygame.K_0: "list",
}

# Ctrl+Fkey dispatch: key → method_name on app
_CTRL_FKEY_TABLE = {
    pygame.K_F2: "_toggle_focus_order_overlay",
    pygame.K_F3: "_select_same_type_as_current",
    pygame.K_F4: "_zoom_to_selection",
    pygame.K_F5: "_replace_text_in_scene",
    pygame.K_F6: "_auto_flow_layout",
    pygame.K_F7: "_measure_selection",
    pygame.K_F8: "_space_evenly_h",
    pygame.K_F9: "_space_evenly_v",
    pygame.K_F10: "_scene_overview",
    pygame.K_F11: "_export_selection_json",
    pygame.K_F12: "_create_split_layout",
}

# Ctrl+1..9: jump to scene by index
_CTRL_SCENE_JUMP = {
    pygame.K_1: 0,
    pygame.K_2: 1,
    pygame.K_3: 2,
    pygame.K_4: 3,
    pygame.K_5: 4,
    pygame.K_6: 5,
    pygame.K_7: 6,
    pygame.K_8: 7,
    pygame.K_9: 8,
}

# ---------------------------------------------------------------------------
# Dispatch flags & tables for Ctrl+key and plain-key shortcuts
# ---------------------------------------------------------------------------
_F_SHIFT_NOSIM = 1  # shift variant requires not sim_input_mode
_F_NOSIM = 2  # entire entry requires not sim_input_mode
_F_NOALT = 4  # requires not KMOD_ALT

# Ctrl+key: (plain_method, shift_method | None, flags)
_CTRL_DISPATCH: dict = {
    pygame.K_s: ("save_json", "_sort_widgets_by_position", _F_SHIFT_NOSIM),
    pygame.K_l: ("load_json", "_unlock_all_widgets", _F_SHIFT_NOSIM),
    pygame.K_c: ("_copy_selection", "_copy_style", 0),
    pygame.K_x: ("_cut_selection", "_remove_degenerate_widgets", _F_SHIFT_NOSIM),
    pygame.K_v: ("_paste_clipboard", "_paste_style", 0),
    pygame.K_d: ("_duplicate_selection", "_duplicate_current_scene", _F_SHIFT_NOSIM),
    pygame.K_f: ("_fit_selection_to_text", "_fit_selection_to_widget", 0),
    pygame.K_a: ("_select_all", "_select_same_type", _F_SHIFT_NOSIM),
    pygame.K_e: ("_export_c_header", "_extract_to_new_scene", _F_NOSIM),
    pygame.K_n: ("_add_new_scene", "_compact_widgets", _F_NOSIM),
    pygame.K_r: ("_rename_current_scene", "_reset_to_defaults", _F_NOSIM),
    pygame.K_j: ("_goto_widget_prompt", "_snap_sizes_to_grid", _F_NOSIM),
    pygame.K_t: ("_save_selection_as_template", "_list_templates", _F_NOSIM | _F_NOALT),
    pygame.K_i: ("_invert_selection", "_show_all_widgets", _F_NOSIM | _F_NOALT),
    pygame.K_b: ("_select_same_color", "_select_bordered", _F_NOSIM | _F_NOALT),
    pygame.K_w: ("_scene_stats", "_fit_scene_to_content", _F_NOSIM | _F_NOALT),
    pygame.K_h: ("_select_parent_panel", "_hide_unselected", _F_NOSIM | _F_NOALT),
    pygame.K_k: ("_select_children", "_clear_padding", _F_NOSIM | _F_NOALT),
    pygame.K_o: ("_copy_to_next_scene", "_toggle_all_borders", _F_NOSIM | _F_NOALT),
    pygame.K_m: ("_snap_selection_to_grid", "_move_selection_to_origin", _F_NOSIM | _F_NOALT),
    pygame.K_p: ("_paste_in_place", "_select_all_panels", _F_NOSIM | _F_NOALT),
    pygame.K_q: ("_broadcast_to_all_scenes", "_quick_clone", _F_NOSIM | _F_NOALT),
    pygame.K_u: ("_select_same_size", "_select_overlapping", _F_NOSIM | _F_NOALT),
}

# Plain key dispatch (not sim, no ctrl, no alt): (plain_action, shift_action)
# Action: str → app.method()  |  (str, str) → app.method(arg)
#         ("@edit", field) → app._inspector_start_edit(field) if selected
_PLAIN_NOSIM_DISPATCH: dict = {
    pygame.K_s: ("_cycle_style", "_select_same_style"),
    pygame.K_v: ("_toggle_visibility", ("@edit", "_value_range")),
    pygame.K_t: ("_cycle_widget_type", ("@edit", "text_overflow")),
    pygame.K_b: ("_cycle_border_style", ("@edit", "border_width")),
    pygame.K_q: ("_cycle_color_preset", "_swap_fg_bg"),
    pygame.K_c: (("@edit", "color_fg"), ("@edit", "color_bg")),
    pygame.K_u: (("@edit", "z_index"), "_select_same_z"),
    pygame.K_j: (("@edit", "_margin"), "_clear_margins"),
    pygame.K_d: (("@edit", "data_points"), "_array_duplicate_prompt"),
    pygame.K_y: ("_toggle_checked", "_select_hidden"),
    pygame.K_f: (("@edit", "max_lines"), "_make_full_height"),
    pygame.K_w: ("_toggle_border", "_make_full_width"),
    pygame.K_o: ("_cycle_text_overflow", "_select_overflow"),
    pygame.K_a: ("_cycle_align", "_cycle_valign"),
    pygame.K_m: (("_mirror_selection", "h"), ("_mirror_selection", "v")),
    pygame.K_i: (("@edit", "icon_char"), "_widget_info"),
    pygame.K_e: ("_smart_edit", ("@edit", "runtime")),
    pygame.K_h: (("@edit", "_size"), ("@edit", "_position")),
    pygame.K_r: (("@edit", "text"), "_auto_rename"),
    pygame.K_SLASH: ("_search_widgets_prompt", None),
    pygame.K_k: (("@edit", "_padding"), "_set_all_spacing_prompt"),
    pygame.K_BACKQUOTE: ("_toggle_widget_ids", "_toggle_z_labels"),
    pygame.K_SEMICOLON: ("_stack_vertical", "_equalize_heights"),
    pygame.K_QUOTE: ("_stack_horizontal", "_equalize_widths"),
    pygame.K_BACKSLASH: ("_cycle_gray_fg", "_cycle_gray_bg"),
    pygame.K_COMMA: ("_swap_positions", "_duplicate_below"),
    pygame.K_PERIOD: ("_center_in_scene", "_duplicate_right"),
}


def _run_action(app, action) -> None:
    """Execute a dispatch action: str, (method, arg), or (@edit, field)."""
    if action is None:
        return
    if isinstance(action, str):
        getattr(app, action)()
    elif action[0] == "@edit":
        if app.state.selected:
            app._inspector_start_edit(action[1])
    else:
        getattr(app, action[0])(action[1])


def _dispatch_ctrl_key(app, key: int, mods: int) -> bool:
    """Try Ctrl+key dispatch table. Returns True if handled."""
    entry = _CTRL_DISPATCH.get(key)
    if entry is None:
        return False
    plain, shift, flags = entry
    if (flags & _F_NOSIM) and app.sim_input_mode:
        return False
    if (flags & _F_NOALT) and (mods & pygame.KMOD_ALT):
        return False
    if (mods & pygame.KMOD_SHIFT) and shift:
        if (flags & _F_SHIFT_NOSIM) and app.sim_input_mode:
            getattr(app, plain)()
        else:
            getattr(app, shift)()
    else:
        getattr(app, plain)()
    return True


def _dispatch_plain_key(app, key: int, mods: int) -> bool:
    """Try plain-key dispatch table. Returns True if handled."""
    if app.sim_input_mode or (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        return False
    entry = _PLAIN_NOSIM_DISPATCH.get(key)
    if entry is None:
        return False
    plain, shift = entry
    _run_action(app, shift if (mods & pygame.KMOD_SHIFT) and shift else plain)
    return True


def _cycle_widget_selection(app, direction: int, extend: bool = False) -> None:
    """Cycle widget selection forward (+1) or backward (-1).

    If extend is True, add the new widget to the existing selection.
    """
    sc = app.state.current_scene()
    n = len(sc.widgets)
    if n == 0:
        return
    if app.state.selected_idx is not None and 0 <= app.state.selected_idx < n:
        new_idx = (app.state.selected_idx + direction) % n
    else:
        new_idx = 0 if direction > 0 else n - 1
    if extend:
        sel = list(app.state.selected)
        if new_idx not in sel:
            sel.append(new_idx)
        app._set_selection(sel, anchor_idx=new_idx)
    else:
        app._set_selection([new_idx], anchor_idx=new_idx)
    app._mark_dirty()


def on_key_down(app, event: pygame.event.Event) -> None:
    """Handle key down event."""
    if event.key == pygame.K_F1:
        app._toggle_help_overlay()
        return
    if event.key == pygame.K_SLASH and (pygame.key.get_mods() & pygame.KMOD_CTRL):
        app.show_shortcuts_panel = not app.show_shortcuts_panel
        app._mark_dirty()
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
        if event.key in _CTRL_ALT_TABLE:
            method_name, *args = _CTRL_ALT_TABLE[event.key]
            getattr(layout_tools, method_name)(app, *args)
            return
        if event.key == pygame.K_s:
            from .fit_widget import fit_selection_to_widget

            fit_selection_to_widget(app)
            return
        if event.key in _CTRL_ALT_APP_TABLE:
            getattr(app, _CTRL_ALT_APP_TABLE[event.key])()
            return
    # Ctrl+Fkey: consolidated dispatch table
    if mods & pygame.KMOD_CTRL and not app.sim_input_mode and event.key in _CTRL_FKEY_TABLE:
        getattr(app, _CTRL_FKEY_TABLE[event.key])()
        return
    # Ctrl+1..9: jump to scene by index
    if (
        mods & pygame.KMOD_CTRL
        and not (mods & (pygame.KMOD_ALT | pygame.KMOD_SHIFT))
        and not app.sim_input_mode
        and event.key in _CTRL_SCENE_JUMP
    ):
        app._jump_to_scene(_CTRL_SCENE_JUMP[event.key])
        return
    # Shift+F: quick-create composites
    if (
        mods & pygame.KMOD_SHIFT
        and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT))
        and not app.sim_input_mode
        and event.key in _SHIFT_FKEY_TABLE
    ):
        getattr(app, _SHIFT_FKEY_TABLE[event.key])()
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

    # Dispatch tables for Ctrl+key and plain-key shortcuts
    if (mods & pygame.KMOD_CTRL) and _dispatch_ctrl_key(app, event.key, mods):
        return
    if _dispatch_plain_key(app, event.key, mods):
        return

    if event.key == pygame.K_ESCAPE:
        if getattr(app, "show_shortcuts_panel", False):
            app.show_shortcuts_panel = False
            app._mark_dirty()
            return
        if app.sim_input_mode:
            if app.focus_edit_value:
                app.focus_edit_value = False
                app._set_status("B: exit edit", ttl_sec=2.0)
            else:
                app._set_status("B pressed", ttl_sec=1.5)
            app._mark_dirty()
            return
        # Deselect first, quit only when nothing is selected
        if app.state.selected:
            app._set_selection([], anchor_idx=None)
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
        if mods & pygame.KMOD_SHIFT and not app.sim_input_mode:
            app._enable_all_widgets()
        elif app.designer.redo():
            app.state.selected_idx = None
            app.state.selected = []
            app._mark_dirty()
    elif event.key == pygame.K_DELETE:
        if (mods & pygame.KMOD_CTRL) and (mods & pygame.KMOD_SHIFT) and not app.sim_input_mode:
            app._delete_current_scene()
        else:
            app._delete_selected()
    elif event.key == pygame.K_LEFTBRACKET and not app.sim_input_mode:
        if mods & pygame.KMOD_CTRL:
            app._z_order_send_to_back()
        else:
            app._z_order_step(-1)
    elif event.key == pygame.K_RIGHTBRACKET and not app.sim_input_mode:
        if mods & pygame.KMOD_CTRL:
            app._z_order_bring_to_front()
        else:
            app._z_order_step(1)
    elif event.key == pygame.K_F3:
        app._toggle_overflow_warnings()
    elif event.key == pygame.K_g and mods & pygame.KMOD_CTRL:
        if mods & pygame.KMOD_SHIFT:
            app._ungroup_selection()
        else:
            app._group_selection()
        app._mark_dirty()
    elif event.key == pygame.K_g:
        if mods & pygame.KMOD_SHIFT and not app.sim_input_mode:
            app._toggle_center_guides()
        else:
            app.show_grid = not app.show_grid
        app._mark_dirty()
    elif event.key == pygame.K_x:
        if mods & pygame.KMOD_SHIFT and not app.sim_input_mode:
            app._swap_dimensions()
        else:
            app.snap_enabled = not app.snap_enabled
        app._mark_dirty()
    elif event.key == pygame.K_TAB:
        if mods & pygame.KMOD_CTRL and not app.sim_input_mode:
            # Ctrl+Tab / Ctrl+Shift+Tab: next/prev scene
            names = list(app.designer.scenes.keys())
            if len(names) > 1:
                cur = getattr(app.designer, "current_scene", "")
                idx = names.index(cur) if cur in names else 0
                idx = (idx - 1) % len(names) if mods & pygame.KMOD_SHIFT else (idx + 1) % len(names)
                app._jump_to_scene(idx)
        else:
            app._toggle_panels()
        app._mark_dirty()
    elif event.key == pygame.K_PAGEDOWN and mods & pygame.KMOD_CTRL and not app.sim_input_mode:
        names = list(app.designer.scenes.keys())
        if len(names) > 1:
            cur = getattr(app.designer, "current_scene", "")
            idx = names.index(cur) if cur in names else 0
            app._jump_to_scene((idx + 1) % len(names))
    elif event.key == pygame.K_PAGEUP and mods & pygame.KMOD_CTRL and not app.sim_input_mode:
        names = list(app.designer.scenes.keys())
        if len(names) > 1:
            cur = getattr(app.designer, "current_scene", "")
            idx = names.index(cur) if cur in names else 0
            app._jump_to_scene((idx - 1) % len(names))
    elif event.key == pygame.K_l and not app.sim_input_mode and not (mods & pygame.KMOD_CTRL):
        if mods & pygame.KMOD_SHIFT:
            app._select_locked()
        else:
            app._toggle_lock_selection()
    elif event.key == pygame.K_F8 and not app.sim_input_mode:
        app._toggle_enabled()
    elif event.key == pygame.K_F9:
        app._toggle_clean_preview()
    elif event.key == pygame.K_F10 and not app.sim_input_mode:
        if mods & pygame.KMOD_SHIFT:
            app._switch_scene(-1)
        else:
            app._switch_scene(1)
    elif event.key == pygame.K_F6 and not app.sim_input_mode:
        app._arrange_in_row()
    elif event.key == pygame.K_F7 and not app.sim_input_mode:
        app._arrange_in_column()
    elif (
        event.key == pygame.K_n
        and not app.sim_input_mode
        and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT))
    ):
        _cycle_widget_selection(app, 1, extend=(mods & pygame.KMOD_SHIFT) != 0)
    elif (
        event.key == pygame.K_p
        and not app.sim_input_mode
        and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT))
    ):
        _cycle_widget_selection(app, -1, extend=(mods & pygame.KMOD_SHIFT) != 0)
    elif event.key == pygame.K_HOME and not app.sim_input_mode:
        sc = app.state.current_scene()
        if sc.widgets:
            app._set_selection([0], anchor_idx=0)
            app._mark_dirty()
    elif event.key == pygame.K_END and not app.sim_input_mode:
        sc = app.state.current_scene()
        if sc.widgets:
            last = len(sc.widgets) - 1
            app._set_selection([last], anchor_idx=last)
            app._mark_dirty()
    elif event.key == pygame.K_F4:
        app._zoom_to_fit()
    elif (
        not app.sim_input_mode
        and event.key in _NUMBER_WIDGET_TABLE
        and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT))
    ):
        app._add_widget(_NUMBER_WIDGET_TABLE[event.key])
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
        if mods & pygame.KMOD_SHIFT and not app.sim_input_mode:
            app._flatten_z_indices()
        else:
            app._reset_zoom()
    elif (
        event.key in (pygame.K_EQUALS, pygame.K_KP_PLUS)
        and not app.sim_input_mode
        and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT))
    ):
        step = 5 if mods & pygame.KMOD_SHIFT else 1
        app._adjust_value(step)
    elif (
        event.key in (pygame.K_MINUS, pygame.K_KP_MINUS)
        and not app.sim_input_mode
        and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT))
    ):
        step = 5 if mods & pygame.KMOD_SHIFT else 1
        app._adjust_value(-step)
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
        # Ctrl+Shift+Up/Down: reorder widget in list
        if (mods & pygame.KMOD_CTRL) and (mods & pygame.KMOD_SHIFT):
            if event.key == pygame.K_UP:
                app._reorder_selection(-1)
                return
            if event.key == pygame.K_DOWN:
                app._reorder_selection(1)
                return
        # Ctrl+Arrow: 1px precise nudge (overrides snap)
        if mods & pygame.KMOD_CTRL and not (mods & pygame.KMOD_SHIFT):
            step = 1
        else:
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
