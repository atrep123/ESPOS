from __future__ import annotations

from typing import List, Tuple

import pygame

from . import focus_nav, layout_tools
from .constants import GRID, snap

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
}


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
    if event.key == pygame.K_F6 and mods & pygame.KMOD_CTRL and not app.sim_input_mode:
        app._auto_flow_layout()
        return
    if event.key == pygame.K_F7 and mods & pygame.KMOD_CTRL and not app.sim_input_mode:
        app._measure_selection()
        return
    if event.key == pygame.K_F8 and mods & pygame.KMOD_CTRL and not app.sim_input_mode:
        app._space_evenly_h()
        return
    if event.key == pygame.K_F9 and mods & pygame.KMOD_CTRL and not app.sim_input_mode:
        app._space_evenly_v()
        return
    if event.key == pygame.K_F5 and mods & pygame.KMOD_CTRL and not app.sim_input_mode:
        app._replace_text_in_scene()
        return
    if event.key == pygame.K_F3 and mods & pygame.KMOD_CTRL and not app.sim_input_mode:
        app._select_same_type_as_current()
        return
    if event.key == pygame.K_F4 and mods & pygame.KMOD_CTRL and not app.sim_input_mode:
        app._zoom_to_selection()
        return
    if event.key == pygame.K_F10 and mods & pygame.KMOD_CTRL and not app.sim_input_mode:
        app._scene_overview()
        return
    if event.key == pygame.K_F2 and mods & pygame.KMOD_CTRL and not app.sim_input_mode:
        app._toggle_focus_order_overlay()
        return
    if event.key == pygame.K_F11 and mods & pygame.KMOD_CTRL and not app.sim_input_mode:
        app._export_selection_json()
        return
    # Ctrl+1..9: jump to scene by index
    if mods & pygame.KMOD_CTRL and not (mods & (pygame.KMOD_ALT | pygame.KMOD_SHIFT)) and not app.sim_input_mode:
        scene_keys = {
            pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2,
            pygame.K_4: 3, pygame.K_5: 4, pygame.K_6: 5,
            pygame.K_7: 6, pygame.K_8: 7, pygame.K_9: 8,
        }
        if event.key in scene_keys:
            app._jump_to_scene(scene_keys[event.key])
            return
    # Shift+F: quick-create composites
    if mods & pygame.KMOD_SHIFT and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)) and not app.sim_input_mode:
        if event.key in _SHIFT_FKEY_TABLE:
            getattr(app, _SHIFT_FKEY_TABLE[event.key])()
            return
    # Ctrl+F12: split layout
    if event.key == pygame.K_F12 and mods & pygame.KMOD_CTRL and not app.sim_input_mode:
        app._create_split_layout()
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
    elif event.key == pygame.K_s and mods & pygame.KMOD_CTRL:
        if mods & pygame.KMOD_SHIFT and not app.sim_input_mode:
            app._sort_widgets_by_position()
        else:
            app.save_json()
    elif event.key == pygame.K_l and mods & pygame.KMOD_CTRL:
        if mods & pygame.KMOD_SHIFT and not app.sim_input_mode:
            app._unlock_all_widgets()
        else:
            app.load_json()
    elif event.key == pygame.K_c and mods & pygame.KMOD_CTRL:
        if mods & pygame.KMOD_SHIFT:
            app._copy_style()
        else:
            app._copy_selection()
    elif event.key == pygame.K_x and mods & pygame.KMOD_CTRL:
        if mods & pygame.KMOD_SHIFT and not app.sim_input_mode:
            app._remove_degenerate_widgets()
        else:
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
        if mods & pygame.KMOD_SHIFT and not app.sim_input_mode:
            app._enable_all_widgets()
        elif app.designer.redo():
            app.state.selected_idx = None
            app.state.selected = []
            app._mark_dirty()
    elif event.key == pygame.K_v and mods & pygame.KMOD_CTRL:
        if mods & pygame.KMOD_SHIFT:
            app._paste_style()
        else:
            app._paste_clipboard()
    elif event.key == pygame.K_d and mods & pygame.KMOD_CTRL:
        if mods & pygame.KMOD_SHIFT and not app.sim_input_mode:
            app._duplicate_current_scene()
        else:
            app._duplicate_selection()
    elif event.key == pygame.K_f and mods & pygame.KMOD_CTRL:
        if mods & pygame.KMOD_SHIFT:
            app._fit_selection_to_widget()
        else:
            app._fit_selection_to_text()
    elif event.key == pygame.K_a and mods & pygame.KMOD_CTRL:
        if (mods & pygame.KMOD_SHIFT) and not app.sim_input_mode:
            app._select_same_type()
        else:
            app._select_all()
    elif event.key == pygame.K_t and mods & pygame.KMOD_CTRL and not app.sim_input_mode and not (mods & pygame.KMOD_ALT):
        if mods & pygame.KMOD_SHIFT:
            app._list_templates()
        else:
            app._save_selection_as_template()
    elif event.key == pygame.K_n and mods & pygame.KMOD_CTRL and not app.sim_input_mode:
        if mods & pygame.KMOD_SHIFT:
            app._compact_widgets()
        else:
            app._add_new_scene()
    elif event.key == pygame.K_r and mods & pygame.KMOD_CTRL and not app.sim_input_mode:
        if mods & pygame.KMOD_SHIFT:
            app._reset_to_defaults()
        else:
            app._rename_current_scene()
    elif event.key == pygame.K_j and mods & pygame.KMOD_CTRL and not app.sim_input_mode:
        if mods & pygame.KMOD_SHIFT:
            app._snap_sizes_to_grid()
        else:
            app._goto_widget_prompt()
    elif event.key == pygame.K_i and mods & pygame.KMOD_CTRL and not app.sim_input_mode and not (mods & pygame.KMOD_ALT):
        if mods & pygame.KMOD_SHIFT:
            app._show_all_widgets()
        else:
            app._invert_selection()
    elif event.key == pygame.K_b and mods & pygame.KMOD_CTRL and not app.sim_input_mode and not (mods & pygame.KMOD_ALT):
        if mods & pygame.KMOD_SHIFT:
            app._select_bordered()
        else:
            app._select_same_color()
    elif event.key == pygame.K_w and mods & pygame.KMOD_CTRL and not app.sim_input_mode and not (mods & pygame.KMOD_ALT):
        if mods & pygame.KMOD_SHIFT:
            app._fit_scene_to_content()
        else:
            app._scene_stats()
    elif event.key == pygame.K_h and mods & pygame.KMOD_CTRL and not app.sim_input_mode and not (mods & pygame.KMOD_ALT):
        if mods & pygame.KMOD_SHIFT:
            app._hide_unselected()
        else:
            app._select_parent_panel()
    elif event.key == pygame.K_k and mods & pygame.KMOD_CTRL and not app.sim_input_mode and not (mods & pygame.KMOD_ALT):
        if mods & pygame.KMOD_SHIFT:
            app._clear_padding()
        else:
            app._select_children()
    elif event.key == pygame.K_o and mods & pygame.KMOD_CTRL and not app.sim_input_mode and not (mods & pygame.KMOD_ALT):
        if mods & pygame.KMOD_SHIFT:
            app._toggle_all_borders()
        else:
            app._copy_to_next_scene()
    elif event.key == pygame.K_m and mods & pygame.KMOD_CTRL and not app.sim_input_mode and not (mods & pygame.KMOD_ALT):
        if mods & pygame.KMOD_SHIFT:
            app._move_selection_to_origin()
        else:
            app._snap_selection_to_grid()
    elif event.key == pygame.K_p and mods & pygame.KMOD_CTRL and not app.sim_input_mode and not (mods & pygame.KMOD_ALT):
        if mods & pygame.KMOD_SHIFT:
            app._select_all_panels()
        else:
            app._paste_in_place()
    elif event.key == pygame.K_q and mods & pygame.KMOD_CTRL and not app.sim_input_mode and not (mods & pygame.KMOD_ALT):
        if mods & pygame.KMOD_SHIFT:
            app._quick_clone()
        else:
            app._broadcast_to_all_scenes()
    elif event.key == pygame.K_u and mods & pygame.KMOD_CTRL and not app.sim_input_mode and not (mods & pygame.KMOD_ALT):
        if mods & pygame.KMOD_SHIFT:
            app._select_overlapping()
        else:
            app._select_same_size()
    elif event.key == pygame.K_e and mods & pygame.KMOD_CTRL and not app.sim_input_mode:
        if mods & pygame.KMOD_SHIFT:
            app._extract_to_new_scene()
        else:
            app._export_c_header()
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
                if mods & pygame.KMOD_SHIFT:
                    idx = (idx - 1) % len(names)
                else:
                    idx = (idx + 1) % len(names)
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
    elif event.key == pygame.K_s and not app.sim_input_mode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        if mods & pygame.KMOD_SHIFT:
            app._select_same_style()
        else:
            app._cycle_style()
    elif event.key == pygame.K_v and not app.sim_input_mode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        if mods & pygame.KMOD_SHIFT:
            if app.state.selected:
                app._inspector_start_edit("_value_range")
        else:
            app._toggle_visibility()
    elif event.key == pygame.K_t and not app.sim_input_mode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        if mods & pygame.KMOD_SHIFT:
            if app.state.selected:
                app._inspector_start_edit("text_overflow")
        else:
            app._cycle_widget_type()
    elif event.key == pygame.K_b and not app.sim_input_mode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        if mods & pygame.KMOD_SHIFT:
            if app.state.selected:
                app._inspector_start_edit("border_width")
        else:
            app._cycle_border_style()
    elif event.key == pygame.K_q and not app.sim_input_mode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        if mods & pygame.KMOD_SHIFT:
            app._swap_fg_bg()
        else:
            app._cycle_color_preset()
    elif event.key == pygame.K_c and not app.sim_input_mode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        if app.state.selected:
            if mods & pygame.KMOD_SHIFT:
                app._inspector_start_edit("color_bg")
            else:
                app._inspector_start_edit("color_fg")
    elif event.key == pygame.K_u and not app.sim_input_mode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        if mods & pygame.KMOD_SHIFT:
            app._select_same_z()
        elif app.state.selected:
            app._inspector_start_edit("z_index")
    elif event.key == pygame.K_j and not app.sim_input_mode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        if mods & pygame.KMOD_SHIFT:
            app._clear_margins()
        elif app.state.selected:
            app._inspector_start_edit("_margin")
    elif event.key == pygame.K_d and not app.sim_input_mode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        if mods & pygame.KMOD_SHIFT:
            app._array_duplicate_prompt()
        elif app.state.selected:
            app._inspector_start_edit("data_points")
    elif event.key == pygame.K_y and not app.sim_input_mode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        if mods & pygame.KMOD_SHIFT:
            app._select_hidden()
        else:
            app._toggle_checked()
    elif event.key == pygame.K_f and not app.sim_input_mode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        if mods & pygame.KMOD_SHIFT:
            app._make_full_height()
        elif app.state.selected:
            app._inspector_start_edit("max_lines")
    elif event.key == pygame.K_w and not app.sim_input_mode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        if mods & pygame.KMOD_SHIFT:
            app._make_full_width()
        else:
            app._toggle_border()
    elif event.key == pygame.K_o and not app.sim_input_mode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        if mods & pygame.KMOD_SHIFT:
            app._select_overflow()
        else:
            app._cycle_text_overflow()
    elif event.key == pygame.K_a and not app.sim_input_mode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        if mods & pygame.KMOD_SHIFT:
            app._cycle_valign()
        else:
            app._cycle_align()
    elif event.key == pygame.K_m and not app.sim_input_mode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        if mods & pygame.KMOD_SHIFT:
            app._mirror_selection("v")
        else:
            app._mirror_selection("h")
    elif event.key == pygame.K_i and not app.sim_input_mode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        if mods & pygame.KMOD_SHIFT:
            app._widget_info()
        elif app.state.selected:
            app._inspector_start_edit("icon_char")
    elif event.key == pygame.K_e and not app.sim_input_mode and (mods & pygame.KMOD_SHIFT) and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        if app.state.selected:
            app._inspector_start_edit("runtime")
    elif event.key == pygame.K_e and not app.sim_input_mode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        app._smart_edit()
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
    elif event.key == pygame.K_h and not app.sim_input_mode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        if app.state.selected:
            if mods & pygame.KMOD_SHIFT:
                app._inspector_start_edit("_position")
            else:
                app._inspector_start_edit("_size")
    elif event.key == pygame.K_r and not app.sim_input_mode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        if mods & pygame.KMOD_SHIFT:
            app._auto_rename()
        elif app.state.selected:
            app._inspector_start_edit("text")
    elif event.key == pygame.K_SLASH and not app.sim_input_mode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        app._search_widgets_prompt()
    elif event.key == pygame.K_k and not app.sim_input_mode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        if mods & pygame.KMOD_SHIFT:
            app._set_all_spacing_prompt()
        elif app.state.selected:
            app._inspector_start_edit("_padding")
    elif event.key == pygame.K_n and not app.sim_input_mode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        _cycle_widget_selection(app, 1, extend=(mods & pygame.KMOD_SHIFT) != 0)
    elif event.key == pygame.K_p and not app.sim_input_mode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
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
    elif not app.sim_input_mode and event.key in _NUMBER_WIDGET_TABLE and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        app._add_widget(_NUMBER_WIDGET_TABLE[event.key])
    elif not app.sim_input_mode and event.key == pygame.K_0 and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        if mods & pygame.KMOD_SHIFT:
            app._add_widget("radiobutton")
        else:
            app._add_widget("textbox")
    elif event.key == pygame.K_F11:
        app._toggle_fullscreen()
        app._mark_dirty()
    elif event.key == pygame.K_F12:
        app._screenshot_canvas()
    elif event.key == pygame.K_BACKQUOTE and not app.sim_input_mode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        if mods & pygame.KMOD_SHIFT:
            app._toggle_z_labels()
        else:
            app._toggle_widget_ids()
    elif event.key == pygame.K_SEMICOLON and not app.sim_input_mode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        if mods & pygame.KMOD_SHIFT:
            app._equalize_heights()
        else:
            app._stack_vertical()
    elif event.key == pygame.K_QUOTE and not app.sim_input_mode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        if mods & pygame.KMOD_SHIFT:
            app._equalize_widths()
        else:
            app._stack_horizontal()
    elif event.key == pygame.K_BACKSLASH and not app.sim_input_mode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        if mods & pygame.KMOD_SHIFT:
            app._cycle_gray_bg()
        else:
            app._cycle_gray_fg()
    elif event.key == pygame.K_COMMA and not app.sim_input_mode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        if mods & pygame.KMOD_SHIFT:
            app._duplicate_below()
        else:
            app._swap_positions()
    elif event.key == pygame.K_PERIOD and not app.sim_input_mode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        if mods & pygame.KMOD_SHIFT:
            app._duplicate_right()
        else:
            app._center_in_scene()
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
    elif event.key in (pygame.K_EQUALS, pygame.K_KP_PLUS) and not app.sim_input_mode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
        step = 5 if mods & pygame.KMOD_SHIFT else 1
        app._adjust_value(step)
    elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS) and not app.sim_input_mode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
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
                except Exception:
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
                        for i in new_indices if 0 <= i < len(sc.widgets)
                    }
                    app.state.drag_start_sizes = {
                        i: (int(sc.widgets[i].width), int(sc.widgets[i].height))
                        for i in new_indices if 0 <= i < len(sc.widgets)
                    }
                app._set_status(f"Cloned {len(new_indices)} widget(s)", ttl_sec=1.5)
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
    except Exception:
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
            except Exception:
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
