"""Context menu building and dispatch — extracted from app.py."""
# pyright: reportPrivateUsage=false

from __future__ import annotations

from typing import TYPE_CHECKING, Tuple

import pygame

if TYPE_CHECKING:
    from .app import CyberpunkEditorApp


# Action → method-name mapping for context menu dispatch.
CONTEXT_ACTION_MAP: dict[str, str] = {
    # Tab actions
    "tab_rename": "_rename_current_scene",
    "tab_duplicate": "_duplicate_current_scene",
    "tab_new": "_add_new_scene",
    "tab_close": "_delete_current_scene",
    "tab_close_others": "_close_other_scenes",
    "tab_close_right": "_close_scenes_to_right",
    # Clipboard / edit
    "duplicate": "_duplicate_selection",
    "delete": "_delete_selected",
    "copy": "_copy_selection",
    "cut": "_cut_selection",
    "paste": "_paste_clipboard",
    "paste_style": "_paste_style",
    "smart_edit": "_smart_edit",
    # Z-order
    "z_front": "_z_order_bring_to_front",
    "z_back": "_z_order_send_to_back",
    # Flags
    "toggle_lock": "_toggle_lock_selection",
    "toggle_visibility": "_toggle_visibility",
    "toggle_enabled": "_toggle_enabled",
    # Style / type cycles
    "cycle_style": "_cycle_style",
    "cycle_type": "_cycle_widget_type",
    "cycle_border": "_cycle_border_style",
    # Single-widget transform
    "mirror": "_mirror_selection",
    "center_in_scene": "_center_in_scene",
    "snap_to_grid": "_snap_selection_to_grid",
    "wrap_in_panel": "_wrap_in_panel",
    "fill_scene": "_fill_scene",
    "shrink_to_content": "_shrink_to_content",
    "select_children": "_select_children",
    "select_overlapping": "_select_overlapping",
    "auto_label": "_auto_label_widgets",
    "inset_widgets": "_inset_widgets",
    "outset_widgets": "_outset_widgets",
    "align_scene_top": "_align_to_scene_top",
    "align_scene_bottom": "_align_to_scene_bottom",
    "align_scene_left": "_align_to_scene_left",
    "align_scene_right": "_align_to_scene_right",
    "center_h": "_center_horizontal",
    "center_v": "_center_vertical",
    "tile_fill": "_tile_fill_scene",
    "delete_hidden": "_delete_hidden_widgets",
    "delete_offscreen": "_delete_offscreen_widgets",
    "swap_dims": "_swap_dimensions",
    "scatter_random": "_scatter_random",
    "toggle_checked": "_toggle_all_checked",
    "reset_values": "_reset_all_values",
    "flatten_z": "_flatten_z_index",
    "number_ids": "_number_widget_ids",
    "z_by_position": "_z_by_position",
    "clone_grid": "_clone_to_grid",
    "mirror_scene_h": "_mirror_scene_horizontal",
    "mirror_scene_v": "_mirror_scene_vertical",
    "sort_by_z": "_sort_widgets_by_z",
    "clamp_to_scene": "_clamp_to_scene",
    "select_unlocked": "_select_unlocked",
    "select_disabled": "_select_disabled",
    "snap_all_grid": "_snap_all_to_grid",
    "center_in_parent": "_center_in_parent",
    "size_to_text": "_size_to_text",
    "fill_parent": "_fill_parent",
    "clear_all_text": "_clear_all_text",
    "move_to_origin": "_move_to_origin",
    "make_square": "_make_square",
    "scale_up": "_scale_up",
    "scale_down": "_scale_down",
    "number_text": "_number_text",
    "reset_padding": "_reset_padding",
    "reset_colors": "_reset_colors",
    "outline_only": "_outline_only",
    "select_largest": "_select_largest",
    "select_smallest": "_select_smallest",
    "set_inverse": "_set_inverse_style",
    "set_bold": "_set_bold_style",
    "set_default_style": "_set_default_style",
    # Multi-widget layout
    "swap_positions": "_swap_positions",
    "stack_vertical": "_stack_vertical",
    "stack_horizontal": "_stack_horizontal",
    "equalize_gaps": "_equalize_gaps",
    "grid_arrange": "_grid_arrange",
    "reverse_order": "_reverse_widget_order",
    "normalize_sizes": "_normalize_sizes",
    "flow_layout": "_auto_flow_layout",
    "space_h": "_space_evenly_h",
    "space_v": "_space_evenly_v",
    "distribute_columns": "_distribute_columns",
    "distribute_rows": "_distribute_rows",
    "distribute_3col": "_distribute_columns_3",
    "cascade_arrange": "_cascade_arrange",
    "pack_left": "_pack_left",
    "pack_top": "_pack_top",
    "align_h_centers": "_align_h_centers",
    "align_v_centers": "_align_v_centers",
    "align_left_edges": "_align_left_edges",
    "align_top_edges": "_align_top_edges",
    "align_right_edges": "_align_right_edges",
    "align_bottom_edges": "_align_bottom_edges",
    "match_first_width": "_match_first_width",
    "match_first_height": "_match_first_height",
    # Multi-widget propagate
    "propagate_border": "_propagate_border",
    "propagate_style": "_propagate_style",
    "propagate_align": "_propagate_align",
    "propagate_colors": "_propagate_colors",
    "propagate_value": "_propagate_value",
    "propagate_padding": "_propagate_padding",
    "propagate_margin": "_propagate_margin",
    "propagate_appearance": "_propagate_appearance",
    "propagate_text": "_propagate_text",
    "spread_values": "_spread_values",
    # Clone / duplicate
    "quick_clone": "_quick_clone",
    "dup_below": "_duplicate_below",
    "dup_right": "_duplicate_right",
    "clone_text": "_clone_text",
    "increment_text": "_increment_text",
    # Info
    "measure": "_measure_selection",
    # View toggles (simple delegates)
    "view_guides": "_toggle_center_guides",
    "view_ids": "_toggle_widget_ids",
    "view_zlabels": "_toggle_z_labels",
    # Quick composites
    "create_header_bar": "_create_header_bar",
    "create_nav_row": "_create_nav_row",
    "create_form_pair": "_create_form_pair",
    "create_status_bar": "_create_status_bar",
    "create_toggle_group": "_create_toggle_group",
    "create_slider_label": "_create_slider_with_label",
    "create_gauge_panel": "_create_gauge_panel",
    "create_progress_section": "_create_progress_section",
    "create_icon_btn_row": "_create_icon_button_row",
    "create_card_layout": "_create_card_layout",
    "create_dashboard_grid": "_create_dashboard_grid",
    "create_split_layout": "_create_split_layout",
}


def open_tab_context_menu(app: CyberpunkEditorApp, pos: Tuple[int, int]) -> None:
    """Open right-click context menu for scene tabs."""
    lx, ly = pos
    for rect, tab_idx, _tab_name in getattr(app, "tab_hitboxes", []):
        if tab_idx >= 0 and rect.collidepoint(lx, ly):
            app._jump_to_scene(tab_idx)
            break
    items: list = []
    items.append(("Rename Scene", "DblClick", "tab_rename"))
    items.append(("Duplicate Scene", "", "tab_duplicate"))
    items.append(("New Scene", "Ctrl+N", "tab_new"))
    names = list(app.designer.scenes.keys())
    if len(names) > 1:
        items.append(("---", "", None))
        items.append(("Close Scene", "MidClick", "tab_close"))
        items.append(("Close Others", "", "tab_close_others"))
        cur_idx = (
            names.index(app.designer.current_scene) if app.designer.current_scene in names else 0
        )
        if cur_idx < len(names) - 1:
            items.append(("Close Right", "", "tab_close_right"))
    app._context_menu = {"visible": True, "pos": pos, "items": items}


def open_context_menu(app: CyberpunkEditorApp, pos: Tuple[int, int]) -> None:
    """Open right-click context menu at pos."""
    sr = getattr(app, "scene_rect", app.layout.canvas_rect)
    if not isinstance(sr, pygame.Rect):
        sr = app.layout.canvas_rect
    items: list = []
    hit = app.state.hit_test_at(pos, sr) if sr.collidepoint(*pos) else None
    if hit is not None and hit not in app.state.selected:
        app._set_selection([hit], anchor_idx=hit)

    SEP = ("---", "", None)

    if app.state.selected:
        items.extend(ctx_single_items(app, SEP))
    if len(app.state.selected) >= 2:
        items.append(SEP)
        items.extend(ctx_multi_items(app, SEP))
    if getattr(app, "_clipboard", None):
        items.append(SEP)
        items.append(("Paste", "Ctrl+V", "paste"))
    if getattr(app, "_style_clipboard", None):
        items.append(("Paste Style", "C+S+V", "paste_style"))

    items.append(SEP)
    items.extend(ctx_view_items(app))
    items.append(SEP)
    items.extend(ctx_add_items(app, SEP))

    # Collapse consecutive separators and strip leading/trailing
    cleaned: list = []
    for lbl, sc, act in items:
        if act is None:
            if not cleaned or cleaned[-1][2] is None:
                continue
            cleaned.append((lbl, sc, act))
        else:
            cleaned.append((lbl, sc, act))
    while cleaned and cleaned[-1][2] is None:
        cleaned.pop()
    while cleaned and cleaned[0][2] is None:
        cleaned.pop(0)

    app._context_menu = {"visible": True, "pos": pos, "items": cleaned}


def ctx_single_items(app: CyberpunkEditorApp, SEP: tuple) -> list:
    """Context menu items when 1+ widgets selected."""
    return [
        ("Edit Text", "DblClick", "edit_text"),
        ("Smart Edit", "E", "smart_edit"),
        SEP,
        ("Copy", "Ctrl+C", "copy"),
        ("Cut", "Ctrl+X", "cut"),
        ("Duplicate", "Ctrl+D", "duplicate"),
        ("Delete", "Del", "delete"),
        SEP,
        ("Bring Forward", "]", "z_forward"),
        ("Send Backward", "[", "z_backward"),
        ("Bring to Front", "Ctrl+]", "z_front"),
        ("Send to Back", "Ctrl+[", "z_back"),
        ("Move Up", "C+S+Up", "reorder_up"),
        ("Move Down", "C+S+Dn", "reorder_down"),
        SEP,
        ("Cycle Style", "S", "cycle_style"),
        ("Cycle Type", "T", "cycle_type"),
        ("Cycle Border", "B", "cycle_border"),
        SEP,
        ("Mirror", "M", "mirror"),
        ("Center in Scene", ".", "center_in_scene"),
        ("Snap to Grid", "Ctrl+M", "snap_to_grid"),
        ("Wrap in Panel", "", "wrap_in_panel"),
        ("Fill Scene", "", "fill_scene"),
        ("Shrink Panel", "", "shrink_to_content"),
        ("Select Children", "", "select_children"),
        ("Select Overlap", "", "select_overlapping"),
        ("Auto-Label", "", "auto_label"),
        ("Inset 8px", "", "inset_widgets"),
        ("Outset 8px", "", "outset_widgets"),
        ("Align Top", "", "align_scene_top"),
        ("Align Bottom", "", "align_scene_bottom"),
        ("Align Left", "", "align_scene_left"),
        ("Align Right", "", "align_scene_right"),
        ("Center Horiz", "", "center_h"),
        ("Center Vert", "", "center_v"),
        ("Tile Fill", "", "tile_fill"),
        ("Del Hidden", "", "delete_hidden"),
        ("Del Offscreen", "", "delete_offscreen"),
        ("Swap W\u2194H", "", "swap_dims"),
        ("Scatter Random", "", "scatter_random"),
        ("Toggle Checked", "", "toggle_checked"),
        ("Reset Values", "", "reset_values"),
        ("Flatten Z", "", "flatten_z"),
        ("Number IDs", "", "number_ids"),
        ("Z by Position", "", "z_by_position"),
        ("Clone Grid", "", "clone_grid"),
        ("Mirror Scene H", "", "mirror_scene_h"),
        ("Mirror Scene V", "", "mirror_scene_v"),
        ("Sort by Z", "", "sort_by_z"),
        ("Clamp to Scene", "", "clamp_to_scene"),
        ("Select Unlocked", "", "select_unlocked"),
        ("Select Disabled", "", "select_disabled"),
        ("Snap All Grid", "", "snap_all_grid"),
        ("Center in Parent", "", "center_in_parent"),
        ("Size to Text", "", "size_to_text"),
        ("Fill Parent", "", "fill_parent"),
        ("Clear Text", "", "clear_all_text"),
        ("Move to Origin", "", "move_to_origin"),
        ("Make Square", "", "make_square"),
        ("Scale Up 2\u00d7", "", "scale_up"),
        ("Scale Down \u00bd", "", "scale_down"),
        ("Number Text", "", "number_text"),
        ("Reset Padding", "", "reset_padding"),
        ("Reset Colors", "", "reset_colors"),
        ("Outline Only", "", "outline_only"),
        ("Select Largest", "", "select_largest"),
        ("Select Smallest", "", "select_smallest"),
        ("Set Inverse", "", "set_inverse"),
        ("Set Bold", "", "set_bold"),
        ("Set Default Style", "", "set_default_style"),
        SEP,
        ("Lock/Unlock", "L", "toggle_lock"),
        ("Show/Hide", "V", "toggle_visibility"),
        ("Enable/Disable", "F8", "toggle_enabled"),
    ]


def ctx_multi_items(app: CyberpunkEditorApp, SEP: tuple) -> list:
    """Context menu items when 2+ widgets selected."""
    return [
        ("Stack Vertical", ";", "stack_vertical"),
        ("Stack Horizontal", "'", "stack_horizontal"),
        ("Equal Gaps", "C+A+E", "equalize_gaps"),
        ("Space Even H", "C+F8", "space_h"),
        ("Space Even V", "C+F9", "space_v"),
        ("Grid Arrange", "C+A+G", "grid_arrange"),
        ("Flow Layout", "C+F6", "flow_layout"),
        SEP,
        ("Swap Positions", ",", "swap_positions"),
        ("Reverse Order", "C+A+R", "reverse_order"),
        ("Normalize Size", "C+A+N", "normalize_sizes"),
        ("Distribute 2-Col", "", "distribute_columns"),
        ("Distribute 2-Row", "", "distribute_rows"),
        ("Pack Left", "", "pack_left"),
        ("Pack Top", "", "pack_top"),
        ("Cascade", "", "cascade_arrange"),
        ("Align Centers H", "", "align_h_centers"),
        ("Align Centers V", "", "align_v_centers"),
        ("Align Left", "", "align_left_edges"),
        ("Align Top", "", "align_top_edges"),
        ("Align Right", "", "align_right_edges"),
        ("Align Bottom", "", "align_bottom_edges"),
        ("Spread Values", "", "spread_values"),
        ("Distribute 3-Col", "", "distribute_3col"),
        ("Match Width", "", "match_first_width"),
        ("Match Height", "", "match_first_height"),
        SEP,
        ("Prop Style", "C+A+P", "propagate_style"),
        ("Prop Colors", "C+A+K", "propagate_colors"),
        ("Prop Border", "C+A+B", "propagate_border"),
        ("Prop Align", "C+A+J", "propagate_align"),
        ("Prop Padding", "C+A+U", "propagate_padding"),
        ("Prop Margin", "C+A+Y", "propagate_margin"),
        ("Prop Value", "C+A+Q", "propagate_value"),
        ("Prop Look", "C+A+Z", "propagate_appearance"),
        ("Prop Text", "", "propagate_text"),
        SEP,
        ("Quick Clone", "C+S+Q", "quick_clone"),
        ("Dup Below", "S+,", "dup_below"),
        ("Dup Right", "S+.", "dup_right"),
        ("Clone Text", "C+A+L", "clone_text"),
        ("Inc Text #", "C+A+I", "increment_text"),
        SEP,
        ("Measure Gaps", "C+F7", "measure"),
    ]


def ctx_view_items(app: CyberpunkEditorApp) -> list:
    """Context menu view-toggle items."""
    gc = "\u2713 " if app.show_grid else "  "
    rc = "\u2713 " if getattr(app, "show_rulers", True) else "  "
    cc = "\u2713 " if getattr(app, "show_center_guides", False) else "  "
    xc = "\u2713 " if app.snap_enabled else "  "
    ic = "\u2713 " if getattr(app, "show_widget_ids", False) else "  "
    zc = "\u2713 " if getattr(app, "show_z_labels", False) else "  "
    return [
        (f"{gc}Grid", "G", "view_grid"),
        (f"{rc}Rulers", "", "view_rulers"),
        (f"{cc}Center Guides", "Shift+G", "view_guides"),
        (f"{xc}Snap", "X", "view_snap"),
        (f"{ic}Widget IDs", "", "view_ids"),
        (f"{zc}Z-Labels", "", "view_zlabels"),
    ]


def ctx_add_items(app: CyberpunkEditorApp, SEP: tuple) -> list:
    """Context menu add-widget and composite items."""
    return [
        ("Add Label", "1", "add_label"),
        ("Add Button", "2", "add_button"),
        ("Add Panel", "3", "add_panel"),
        ("Add Progress", "4", "add_progressbar"),
        ("Add Gauge", "5", "add_gauge"),
        ("Add Slider", "6", "add_slider"),
        ("Add Checkbox", "7", "add_checkbox"),
        ("Add Chart", "8", "add_chart"),
        ("Add Icon", "9", "add_icon"),
        ("Add Textbox", "0", "add_textbox"),
        ("Add Radiobutton", "S+0", "add_radiobutton"),
        SEP,
        ("Header Bar", "S+F1", "create_header_bar"),
        ("Nav Row", "S+F2", "create_nav_row"),
        ("Form Pair", "S+F3", "create_form_pair"),
        ("Status Bar", "S+F4", "create_status_bar"),
        ("Toggle Group", "S+F5", "create_toggle_group"),
        ("Slider+Label", "S+F6", "create_slider_label"),
        ("Gauge Panel", "S+F7", "create_gauge_panel"),
        ("Progress Row", "S+F8", "create_progress_section"),
        ("Icon Btn Row", "S+F9", "create_icon_btn_row"),
        ("Card Layout", "S+F11", "create_card_layout"),
        ("Dashboard 2x2", "S+F12", "create_dashboard_grid"),
        ("Split Layout", "C+F12", "create_split_layout"),
    ]


def click_context_menu(app: CyberpunkEditorApp, pos: Tuple[int, int]) -> None:
    """Process a click on the context menu, or dismiss it."""
    menu = getattr(app, "_context_menu", None)
    if not menu or not menu.get("visible"):
        return
    hitboxes = menu.get("hitboxes", [])
    for rect, action in hitboxes:
        if rect.collidepoint(pos[0], pos[1]):
            menu["visible"] = False
            app._execute_context_action(action)
            return
    menu["visible"] = False


def execute_context_action(app: CyberpunkEditorApp, action: str) -> None:
    """Execute a context menu action."""
    # Parameterised actions
    if action == "edit_text":
        app._inspector_start_edit("text")
    elif action == "z_forward":
        app._z_order_step(1)
    elif action == "z_backward":
        app._z_order_step(-1)
    elif action == "reorder_up":
        app._reorder_selection(-1)
    elif action == "reorder_down":
        app._reorder_selection(1)
    elif action == "view_grid":
        app.show_grid = not app.show_grid
        app._mark_dirty()
    elif action == "view_rulers":
        app.show_rulers = not getattr(app, "show_rulers", True)
        app._mark_dirty()
    elif action == "view_snap":
        app.snap_enabled = not app.snap_enabled
        app._mark_dirty()
    elif action.startswith("add_"):
        app._add_widget(action[4:])
    else:
        method_name = CONTEXT_ACTION_MAP.get(action)
        if method_name is not None:
            getattr(app, method_name)()
