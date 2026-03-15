import pygame

from cyberpunk_designer import drawing, focus_nav, layout_tools, windowing
from cyberpunk_editor import GRID, PALETTE
from ui_designer import UIDesigner, WidgetConfig


def test_toolbar_hover_and_pressed_use_pixel_fill(make_app):
    app = make_app(size=(256, 192))
    app.logical_surface.fill(PALETTE["bg"])
    app._draw_toolbar()

    first_rect, _ = app.toolbar_hitboxes[0]
    assert first_rect.x % GRID == 0
    assert first_rect.y % GRID == 0

    inner = (first_rect.x + 2, first_rect.y + 2)
    app.pointer_pos = first_rect.center

    app.pointer_down = False
    app.logical_surface.fill(PALETTE["bg"])
    app._draw_toolbar()
    hover_color = app.logical_surface.get_at(inner)[:3]
    assert hover_color == app._shade(PALETTE["panel"], 12)

    app.pointer_down = True
    app.logical_surface.fill(PALETTE["bg"])
    app._draw_toolbar()
    pressed_color = app.logical_surface.get_at(inner)[:3]
    assert pressed_color == app._shade(PALETTE["panel"], -4)


def test_palette_and_inspector_grid_alignment(make_app):
    app = make_app(size=(256, 192))
    app.pointer_pos = (-9999, -9999)

    app.logical_surface.fill(PALETTE["bg"])
    app._draw_palette()
    palette_rect = app.layout.palette_rect
    top_left_color = app.logical_surface.get_at((palette_rect.x, palette_rect.y))[:3]
    assert top_left_color == PALETTE["panel_border"]
    assert app.palette_hitboxes, "palette rows should be cached"
    prow = app.palette_hitboxes[0][0]
    assert prow.height == app.pixel_row_height
    assert prow.x % GRID == 0

    app.logical_surface.fill(PALETTE["bg"])
    app._draw_inspector()
    inspector_rect = app.layout.inspector_rect
    insp_color = app.logical_surface.get_at((inspector_rect.x, inspector_rect.y))[:3]
    assert insp_color == PALETTE["panel_border"]
    assert app.inspector_hitboxes, "inspector rows should be cached"
    irow = app.inspector_hitboxes[0][0]
    assert irow.height == app.pixel_row_height
    assert irow.x % GRID == 0


def test_palette_click_adds_widget_and_canvas_renders(make_app):
    app = make_app(size=(256, 192))
    app.pointer_pos = (-9999, -9999)

    sc = app.state.current_scene()
    assert not sc.widgets

    app.logical_surface.fill(PALETTE["bg"])
    app._draw_palette()
    button_rect, _label, enabled = next(row for row in app.palette_hitboxes if row[1] == "button")
    assert enabled

    app._on_mouse_down(button_rect.center)
    assert len(sc.widgets) == 1
    assert app.state.selected_idx == 0

    app.logical_surface.fill(PALETTE["bg"])
    app._draw_canvas()
    w = sc.widgets[0]
    sr = getattr(app, "scene_rect", app.layout.canvas_rect)
    inside = (sr.x + w.x + 1, sr.y + w.y + 1)
    assert app.logical_surface.get_at(inside)[:3] != PALETTE["canvas_bg"]


def test_window_resize_expands_layout_and_draws_device_viewport(make_app):
    app = make_app(size=(256, 192))
    base_w = app.layout.width
    base_h = app.layout.height

    windowing.handle_video_resize(app, 1600, 900)
    assert app.layout.width >= base_w
    assert app.layout.height >= base_h
    assert app.state.layout is app.layout

    cr = app.layout.canvas_rect
    assert cr.width >= int(getattr(app.designer, "width", 0) or 0)
    assert cr.height >= int(getattr(app.designer, "height", 0) or 0)

    app.logical_surface.fill(PALETTE["bg"])
    app._draw_canvas()
    sr = getattr(app, "scene_rect", cr)
    inside = (sr.x + 1, sr.y + 1)
    assert app.logical_surface.get_at(inside)[:3] == PALETTE["canvas_bg"]

    if cr.width > int(getattr(app.designer, "width", 0) or 0) + 2:
        outside = (sr.right + 1, sr.y + 1)
        assert app.logical_surface.get_at(outside)[:3] == PALETTE["panel"]


def test_palette_scroll_is_clipped_to_panel_rect(make_app):
    app = make_app(size=(256, 192))
    app.pointer_pos = (-9999, -9999)

    # Fill with a sentinel so we can detect draw bleed.
    sentinel = (123, 45, 67)
    app.logical_surface.fill(sentinel)

    # Force palette content to start drawing into the toolbar area (y=2) if unclipped.
    r = app.layout.palette_rect
    row_h = int(app.pixel_row_height)
    app.state.palette_scroll = int(r.y + row_h - 2)

    app._draw_palette()

    # Toolbar area must remain untouched by palette content.
    x = int(r.x + app.pixel_padding + 1)
    y = 3
    assert app.logical_surface.get_at((x, y))[:3] == sentinel


def test_palette_scroll_does_not_overdraw_header_row(make_app):
    app = make_app(size=(256, 192))
    app.pointer_pos = (-9999, -9999)

    r = app.layout.palette_rect
    row_h = int(app.pixel_row_height)
    probe = (int(r.right - 6), int(r.y + 2))

    app.logical_surface.fill(PALETTE["bg"])
    app.state.palette_scroll = 0
    app._draw_palette()
    base = app.logical_surface.get_at(probe)[:3]

    # If content is not clipped to the scroll area, this would overwrite pixels in the header row.
    app.logical_surface.fill(PALETTE["bg"])
    app.state.palette_scroll = max(0, row_h - 2)
    app._draw_palette()
    assert app.logical_surface.get_at(probe)[:3] == base


def test_inspector_scroll_does_not_overdraw_header_row(make_app):
    app = make_app(size=(256, 192))
    app.pointer_pos = (-9999, -9999)

    r = app.layout.inspector_rect
    row_h = int(app.pixel_row_height)
    probe = (int(r.right - 6), int(r.y + 2))

    app.logical_surface.fill(PALETTE["bg"])
    app.state.inspector_scroll = 0
    app._draw_inspector()
    base = app.logical_surface.get_at(probe)[:3]

    app.logical_surface.fill(PALETTE["bg"])
    app.state.inspector_scroll = max(0, row_h - 2)
    app._draw_inspector()
    assert app.logical_surface.get_at(probe)[:3] == base


def test_scanlines_drawn_over_frame(make_app):
    app = make_app(size=(256, 192))
    app.window = pygame.Surface((app.layout.width, app.layout.height))
    app._draw_frame()
    # Background should be flat fill with no scanlines
    assert app.window.get_at((0, 0))[:3] == PALETTE["bg"]
    assert app.window.get_at((0, GRID * 2))[:3] == PALETTE["bg"]


def test_help_overlay_draws_and_can_be_disabled(make_app):
    from cyberpunk_designer import drawing

    app = make_app(size=(256, 192))
    app._set_help_overlay(True, pinned=True)
    sentinel = (200, 100, 50)
    app.logical_surface.fill(sentinel)
    drawing.draw_help_overlay(app)
    assert app.logical_surface.get_at((0, 0))[:3] != sentinel

    app._set_help_overlay(False)
    app.logical_surface.fill(sentinel)
    drawing.draw_help_overlay(app)
    assert app.logical_surface.get_at((0, 0))[:3] == sentinel


def test_ascii_border_pixel_perfect_single_stroke():
    designer = UIDesigner(32, 16)
    canvas = [["." for _ in range(designer.width)] for _ in range(designer.height)]
    widget = WidgetConfig(
        type="box", x=4, y=4, width=8, height=6, border=True, border_style="single"
    )
    border_chars = designer._get_border_chars(widget.border_style)

    designer._draw_border(canvas, widget, border_chars, designer.width, designer.height)

    assert canvas[4][4] == border_chars["tl"]
    assert canvas[4][11] == border_chars["tr"]
    assert canvas[9][4] == border_chars["bl"]
    assert canvas[9][11] == border_chars["br"]
    assert canvas[5][4] == border_chars["v"]
    assert canvas[4][5] == border_chars["h"]
    assert canvas[5][5] == "."


def test_component_card_inserts_multiple_widgets(make_app):
    app = make_app(size=(256, 192))
    sc = app.state.current_scene()
    assert not sc.widgets

    app._add_component("card")
    assert len(sc.widgets) >= 3
    assert app.state.selected_idx == 0
    assert len(app.state.selected) == len(sc.widgets)
    assert any(w.type == "panel" for w in sc.widgets)
    assert any(w.type == "progressbar" for w in sc.widgets)


def test_component_insert_creates_group(make_app):
    app = make_app(size=(256, 192))
    sc = app.state.current_scene()
    app._add_component("card")
    assert sc.widgets
    assert app.designer.groups
    assert any(name.startswith("comp:card:") for name in app.designer.groups)


def test_component_insert_uses_unique_root_prefix_for_multiple_instances(make_app):
    app = make_app(size=(256, 192))
    sc = app.state.current_scene()

    app._add_component("card")
    first_ids = [getattr(w, "_widget_id", "") for w in sc.widgets]
    assert any(str(wid).startswith("card.") for wid in first_ids)

    app._add_component("card")
    all_ids = [
        str(getattr(w, "_widget_id", "") or "")
        for w in sc.widgets
        if str(getattr(w, "_widget_id", "") or "")
    ]
    assert any(wid.startswith("card.") for wid in all_ids)
    assert any(wid.startswith("card_2.") for wid in all_ids)
    assert len(all_ids) == len(set(all_ids)), "widget ids must be unique for export/runtime"


def test_component_os_menu_list_inserts_focusable_items(make_app):
    app = make_app(size=(256, 192))
    sc = app.state.current_scene()

    app._add_component("menu_list")
    assert sc.widgets
    assert any(w.type == "button" for w in sc.widgets), (
        "menu list should contain focusable button items"
    )
    assert app.designer.groups
    assert any(name.startswith("comp:menu_list:") for name in app.designer.groups)


def test_component_os_menu_alias_inserts_focusable_items(make_app):
    app = make_app(size=(256, 192))
    sc = app.state.current_scene()

    app._add_component("menu")
    assert sc.widgets
    assert any(getattr(w, "_widget_id", "") == "menu.item0" for w in sc.widgets)
    assert any(w.type == "button" for w in sc.widgets), "menu should contain focusable button items"
    assert app.designer.groups
    assert any(name.startswith("comp:menu:") for name in app.designer.groups)


def test_component_menu_scroll_comp_edit_updates_widget_text(make_app):
    app = make_app(size=(256, 192))
    sc = app.state.current_scene()

    app._add_component("menu")
    scroll = next(w for w in sc.widgets if getattr(w, "_widget_id", "") == "menu.scroll")

    rows, _, _ = app._compute_inspector_rows()
    keys = [key for key, _ in rows]
    assert "comp.scroll" in keys

    app.state.inspector_selected_field = "comp.scroll"
    app.state.inspector_input_buffer = "2/10"
    assert app._inspector_commit_edit()
    assert scroll.text == "2/10"


def test_component_menu_count_comp_edit_updates_scroll_text(make_app):
    app = make_app(size=(256, 192))
    sc = app.state.current_scene()

    app._add_component("menu")
    scroll = next(w for w in sc.widgets if getattr(w, "_widget_id", "") == "menu.scroll")

    rows, _, _ = app._compute_inspector_rows()
    keys = [key for key, _ in rows]
    assert "comp.count" in keys

    app.state.inspector_selected_field = "comp.count"
    app.state.inspector_input_buffer = "12"
    assert app._inspector_commit_edit()
    assert scroll.text == "1/12"


def test_component_root_rename_updates_widget_ids_and_group_name(make_app):
    app = make_app(size=(256, 192))
    sc = app.state.current_scene()

    app._add_component("modal")
    assert any(str(getattr(w, "_widget_id", "") or "") == "modal.overlay" for w in sc.widgets)
    old_groups = set(app.designer.groups.keys())
    assert any(g.startswith("comp:modal:") for g in old_groups)

    app.state.inspector_selected_field = "comp.root"
    app.state.inspector_input_buffer = "modal2"
    assert app._inspector_commit_edit()

    assert any(str(getattr(w, "_widget_id", "") or "") == "modal2.overlay" for w in sc.widgets)
    assert not any(str(getattr(w, "_widget_id", "") or "").startswith("modal.") for w in sc.widgets)
    assert any(g.startswith("comp:modal:modal2:") for g in app.designer.groups)


def test_component_tabs_comp_edit_updates_widget_text(make_app):
    app = make_app(size=(256, 192))
    sc = app.state.current_scene()

    app._add_component("tabs")
    tab1 = next(w for w in sc.widgets if getattr(w, "_widget_id", "") == "tabs.tab1")
    assert tab1.text == "Tab 1"

    rows, _, _ = app._compute_inspector_rows()
    keys = [key for key, _ in rows]
    assert "comp.tab1" in keys

    app.state.inspector_selected_field = "comp.tab1"
    app.state.inspector_input_buffer = "Home"
    assert app._inspector_commit_edit()
    assert tab1.text == "Home"


def test_component_tabs_active_tab_updates_style_keeps_component_selected(make_app):
    app = make_app(size=(256, 192))
    sc = app.state.current_scene()

    app._add_component("tabs")
    tab1 = next(w for w in sc.widgets if getattr(w, "_widget_id", "") == "tabs.tab1")
    tab2 = next(w for w in sc.widgets if getattr(w, "_widget_id", "") == "tabs.tab2")
    assert "highlight" in str(getattr(tab1, "style", "") or "").lower()

    group = app._selected_group_exact()
    assert group and group.startswith("comp:tabs:")

    rows, _, _ = app._compute_inspector_rows()
    keys = [key for key, _ in rows]
    assert "comp.active_tab" in keys

    app.state.inspector_selected_field = "comp.active_tab"
    app.state.inspector_input_buffer = "2"
    assert app._inspector_commit_edit()

    assert "highlight" in str(getattr(tab2, "style", "") or "").lower()
    assert app._selected_group_exact() == group


def test_component_menu_list_active_item_updates_highlight_keeps_component_selected(make_app):
    app = make_app(size=(256, 192))
    sc = app.state.current_scene()

    app._add_component("menu_list")
    item1 = next(w for w in sc.widgets if getattr(w, "_widget_id", "") == "menu_list.item0")
    item2 = next(w for w in sc.widgets if getattr(w, "_widget_id", "") == "menu_list.item1")
    assert "highlight" in str(getattr(item1, "style", "") or "").lower()

    group = app._selected_group_exact()
    assert group and group.startswith("comp:menu_list:")

    rows, _, _ = app._compute_inspector_rows()
    keys = [key for key, _ in rows]
    assert "comp.active_item" in keys

    app.state.inspector_selected_field = "comp.active_item"
    app.state.inspector_input_buffer = "2"
    assert app._inspector_commit_edit()

    assert "highlight" in str(getattr(item2, "style", "") or "").lower()
    assert app._selected_group_exact() == group


def test_component_list_comp_edit_updates_rows_and_active_item(make_app):
    app = make_app(size=(256, 192))
    sc = app.state.current_scene()

    app._add_component("list")
    item1 = next(w for w in sc.widgets if getattr(w, "_widget_id", "") == "list.item0")
    item2 = next(w for w in sc.widgets if getattr(w, "_widget_id", "") == "list.item1")
    item1_label = next(w for w in sc.widgets if getattr(w, "_widget_id", "") == "list.item0.label")
    item1_value = next(w for w in sc.widgets if getattr(w, "_widget_id", "") == "list.item0.value")
    assert item1.type == "button"
    assert "highlight" in str(getattr(item1, "style", "") or "").lower()

    group = app._selected_group_exact()
    assert group and group.startswith("comp:list:")

    rows, _, _ = app._compute_inspector_rows()
    keys = [key for key, _ in rows]
    assert "comp.item0" in keys
    assert "comp.value0" in keys
    assert "comp.active_item" in keys

    app.state.inspector_selected_field = "comp.item0"
    app.state.inspector_input_buffer = "Speed"
    assert app._inspector_commit_edit()
    assert item1_label.text == "Speed"

    app.state.inspector_selected_field = "comp.value0"
    app.state.inspector_input_buffer = "42"
    assert app._inspector_commit_edit()
    assert item1_value.text == "42"

    app.state.inspector_selected_field = "comp.active_item"
    app.state.inspector_input_buffer = "2"
    assert app._inspector_commit_edit()
    assert "highlight" in str(getattr(item2, "style", "") or "").lower()
    assert app._selected_group_exact() == group


def test_component_list_scroll_comp_edit_updates_widget_text(make_app):
    app = make_app(size=(256, 192))
    sc = app.state.current_scene()

    app._add_component("list")
    scroll = next(w for w in sc.widgets if getattr(w, "_widget_id", "") == "list.scroll")

    rows, _, _ = app._compute_inspector_rows()
    keys = [key for key, _ in rows]
    assert "comp.scroll" in keys

    app.state.inspector_selected_field = "comp.scroll"
    app.state.inspector_input_buffer = "3/12"
    assert app._inspector_commit_edit()
    assert scroll.text == "3/12"


def test_sim_input_list_scrolls_virtualized_items_and_restores(make_app):
    app = make_app(size=(256, 192))
    sc = app.state.current_scene()

    app._add_component("list")
    scroll = next(w for w in sc.widgets if getattr(w, "_widget_id", "") == "list.scroll")
    scroll.text = "1/12"

    app.sim_input_mode = True
    app._ensure_focus()
    assert app.focus_idx is not None
    assert getattr(sc.widgets[int(app.focus_idx)], "_widget_id", "") == "list.item0"

    for _ in range(6):
        app._focus_move_direction("down")

    assert scroll.text == "7/12"
    assert getattr(sc.widgets[int(app.focus_idx)], "_widget_id", "") == "list.item5"
    item5_label = next(w for w in sc.widgets if getattr(w, "_widget_id", "") == "list.item5.label")
    assert item5_label.text == "Item 7"

    focus_nav.sim_runtime_restore(app)
    assert scroll.text == "1/12"
    assert item5_label.text == "Item 6"


def test_group_drag_moves_all_widgets(make_app):
    app = make_app(size=(256, 192))
    sc = app.state.current_scene()
    app._add_component("card")

    before = [(w.x, w.y) for w in sc.widgets]
    sr = getattr(app, "scene_rect", app.layout.canvas_rect)
    w0 = sc.widgets[0]
    start_pos = (sr.x + w0.x + 2, sr.y + w0.y + 2)
    app.pointer_down = True
    app._on_mouse_down(start_pos)
    move_pos = (start_pos[0] + GRID * 2, start_pos[1] + GRID * 2)
    app._on_mouse_move(move_pos, (1, 0, 0))
    app.pointer_down = False
    app._on_mouse_up(move_pos)

    dx = sc.widgets[0].x - before[0][0]
    dy = sc.widgets[0].y - before[0][1]
    assert (dx, dy) != (0, 0)
    after = [(w.x, w.y) for w in sc.widgets]
    assert [(x - bx, y - by) for (x, y), (bx, by) in zip(after, before)] == [(dx, dy)] * len(
        sc.widgets
    )


def test_ungroup_then_drag_moves_single_widget(make_app):
    app = make_app(size=(256, 192))
    sc = app.state.current_scene()
    app._add_component("card")
    app._ungroup_selection()

    before = [(w.x, w.y) for w in sc.widgets]
    sr = getattr(app, "scene_rect", app.layout.canvas_rect)
    w0 = sc.widgets[0]
    start_pos = (sr.x + w0.x + 2, sr.y + w0.y + 2)
    app.pointer_down = True
    app._on_mouse_down(start_pos)
    move_pos = (start_pos[0] + GRID * 2, start_pos[1] + GRID * 2)
    app._on_mouse_move(move_pos, (1, 0, 0))
    app.pointer_down = False
    app._on_mouse_up(move_pos)

    after = [(w.x, w.y) for w in sc.widgets]
    assert after[0] != before[0]
    assert after[1:] == before[1:]


def test_inspector_click_to_edit_and_toggle(make_app):
    app = make_app(size=(256, 192))
    app.pointer_pos = (-9999, -9999)
    app.pointer_down = False

    app._add_widget("label")
    w = app.state.selected_widget()
    assert w is not None

    rows, _, _ = app._compute_inspector_rows()
    keys = [key for key, _ in rows]
    text_idx = keys.index("text")
    app.state.inspector_scroll = text_idx * app.pixel_row_height

    app.logical_surface.fill(PALETTE["bg"])
    app._draw_inspector()
    text_rect = next(rect for rect, key in app.inspector_hitboxes if key == "text")

    app._on_mouse_down(text_rect.center)
    assert app.state.inspector_selected_field == "text"

    app.state.inspector_input_buffer = "Hello"
    assert app._inspector_commit_edit()
    assert w.text == "Hello"
    assert app.state.inspector_selected_field is None

    border_idx = keys.index("border")
    app.state.inspector_scroll = border_idx * app.pixel_row_height
    app.logical_surface.fill(PALETTE["bg"])
    app._draw_inspector()
    border_rect = next(rect for rect, key in app.inspector_hitboxes if key == "border")
    before = bool(getattr(w, "border", True))
    app._on_mouse_down(border_rect.center)
    assert bool(getattr(w, "border", True)) is (not before)


def test_layout_align_left_aligns_to_selection_bounds(make_app):
    app = make_app(size=(256, 192))
    sc = app.state.current_scene()

    sc.widgets = [
        WidgetConfig(type="button", x=GRID, y=GRID, width=40, height=16, text="A"),
        WidgetConfig(type="button", x=GRID * 5, y=GRID * 2, width=40, height=16, text="B"),
        WidgetConfig(type="button", x=GRID * 9, y=GRID * 3, width=40, height=16, text="C"),
    ]
    app.state.selected = [0, 1, 2]
    app.state.selected_idx = 0

    layout_tools.align_selection(app, "left")
    assert [int(w.x) for w in sc.widgets] == [GRID, GRID, GRID]


def test_layout_distribute_vertical_sets_even_gaps(make_app):
    app = make_app(size=(256, 192))
    sc = app.state.current_scene()

    sc.widgets = [
        WidgetConfig(type="button", x=GRID, y=0, width=40, height=16, text="A"),
        WidgetConfig(type="button", x=GRID, y=GRID * 4, width=40, height=16, text="B"),
        WidgetConfig(type="button", x=GRID, y=GRID * 12, width=40, height=16, text="C"),
    ]
    app.state.selected = [0, 1, 2]
    app.state.selected_idx = 0

    layout_tools.distribute_selection(app, "v")
    assert int(sc.widgets[0].y) == 0
    assert int(sc.widgets[2].y) == GRID * 12
    assert int(sc.widgets[1].y) == GRID * 6


def test_layout_match_width_uses_anchor_widget(make_app):
    app = make_app(size=(256, 192))
    sc = app.state.current_scene()

    sc.widgets = [
        WidgetConfig(type="button", x=GRID, y=GRID, width=GRID * 5, height=16, text="A"),
        WidgetConfig(type="button", x=GRID * 8, y=GRID, width=GRID * 10, height=16, text="B"),
    ]
    app.state.selected = [0, 1]
    app.state.selected_idx = 0

    layout_tools.match_size_selection(app, "width")
    assert int(sc.widgets[1].width) == int(sc.widgets[0].width)


def test_guides_snap_drag_to_other_widget_edge(make_app):
    app = make_app(size=(256, 192))
    sc = app.state.current_scene()

    sc.widgets = [
        WidgetConfig(type="button", x=10, y=10, width=40, height=16, text="A"),
        WidgetConfig(type="button", x=80, y=10, width=40, height=16, text="B"),
    ]
    app.state.selected = [0]
    app.state.selected_idx = 0

    bounds = pygame.Rect(0, 0, int(sc.widgets[0].width), int(sc.widgets[0].height))
    x, y = layout_tools.snap_drag_to_guides(app, desired_x=79, desired_y=10, bounds=bounds)
    assert x == 80
    assert any(g[0] == "v" and g[1] == 80 for g in app.state.active_guides)


def test_fit_text_grows_width_for_ellipsis(make_app):
    app = make_app(size=(256, 192))
    app._add_widget("label")
    w = app.state.selected_widget()
    assert w is not None

    sc = app.state.current_scene()
    pad = max(2, app.pixel_padding // 2)
    base_w = int(getattr(w, "width", 0) or 0)
    w.text_overflow = "ellipsis"

    text = ""
    max_allowed = int(sc.width) - GRID
    while True:
        candidate = text + "W"
        needed = app._text_width_px(candidate) + pad * 2
        if needed > max_allowed:
            break
        text = candidate
        if needed > base_w + GRID:
            break

    assert text, "test needs a non-empty label"
    w.text = text
    needed_w = app._text_width_px(text) + pad * 2
    assert needed_w > base_w

    app._fit_selection_to_text()
    assert int(getattr(w, "width", 0) or 0) >= needed_w
    assert int(getattr(w, "x", 0) or 0) + int(getattr(w, "width", 0) or 0) <= int(sc.width)


def test_fit_text_grows_height_for_wrap(make_app):
    app = make_app(size=(256, 192))
    app._add_widget("label")
    w = app.state.selected_widget()
    assert w is not None

    w.width = GRID * 5
    w.height = GRID * 2
    w.text_overflow = "wrap"
    w.text = "one two three four five six seven eight nine ten"

    pad = max(2, app.pixel_padding // 2)
    avail_w = max(1, int(w.width) - pad * 2)
    lines = app._wrap_text_px(w.text, max_width_px=avail_w, max_lines=9999)
    needed_h = max(1, len(lines)) * int(app.pixel_font.get_height()) + pad * 2
    assert needed_h > int(w.height)

    app._fit_selection_to_text()
    assert int(getattr(w, "height", 0) or 0) >= needed_h


def test_fit_widget_shrinks_width_for_ellipsis(make_app):
    app = make_app(size=(256, 192))
    app._add_widget("label")
    w = app.state.selected_widget()
    assert w is not None

    sc = app.state.current_scene()
    pad = max(2, app.pixel_padding // 2)

    w.text_overflow = "ellipsis"
    w.text = "Hello"
    w.width = GRID * 20
    before_w = int(getattr(w, "width", 0) or 0)

    needed_w = app._text_width_px(w.text) + pad * 2
    assert needed_w < before_w

    app._fit_selection_to_widget()
    after_w = int(getattr(w, "width", 0) or 0)
    assert after_w <= before_w
    assert after_w >= needed_w
    assert int(getattr(w, "x", 0) or 0) + after_w <= int(sc.width)


def test_fit_widget_shrinks_height_for_wrap(make_app):
    app = make_app(size=(256, 192))
    app._add_widget("label")
    w = app.state.selected_widget()
    assert w is not None

    w.width = GRID * 6
    w.text_overflow = "wrap"
    w.text = "one two three four five six seven eight nine ten"

    before_w = int(getattr(w, "width", 0) or 0)

    pad = max(2, app.pixel_padding // 2)
    avail_w = max(1, int(w.width) - pad * 2)
    lines = app._wrap_text_px(w.text, max_width_px=avail_w, max_lines=9999)
    needed_h = max(1, len(lines)) * int(app.pixel_font.get_height()) + pad * 2
    # Make sure we start above the computed content height (font metrics vary by OS/font).
    w.height = max(GRID * 12, needed_h + GRID * 4)
    before_h = int(getattr(w, "height", 0) or 0)
    assert needed_h < before_h

    app._fit_selection_to_widget()
    after_w = int(getattr(w, "width", 0) or 0)
    after_h = int(getattr(w, "height", 0) or 0)
    assert after_w == before_w
    assert after_h <= before_h
    assert after_h >= needed_h


def test_input_mode_focus_navigation_and_activation(make_app):
    app = make_app(size=(256, 192))
    sc = app.state.current_scene()
    sc.widgets.clear()
    sc.widgets.append(
        WidgetConfig(type="button", x=8, y=8, width=48, height=20, text="OK", border=True)
    )
    sc.widgets.append(
        WidgetConfig(type="checkbox", x=8, y=40, width=96, height=16, text="Option", checked=False)
    )
    sc.widgets.append(
        WidgetConfig(
            type="label", x=8, y=64, width=96, height=16, text="Not focusable", border=False
        )
    )

    app.sim_input_mode = True
    app._ensure_focus()
    assert app.focus_idx == 0

    app._focus_move_direction("down")
    assert app.focus_idx == 1
    assert app.state.selected_idx == 1

    app._activate_focused()
    assert bool(getattr(sc.widgets[1], "checked", False)) is True


def test_input_mode_focus_navigation_prefers_beam_overlap(make_app):
    app = make_app(size=(256, 192))
    sc = app.state.current_scene()
    sc.widgets.clear()
    sc.widgets.append(WidgetConfig(type="button", x=100, y=50, width=50, height=20, text="CUR"))
    sc.widgets.append(WidgetConfig(type="button", x=110, y=10, width=50, height=20, text="BEAM"))
    sc.widgets.append(WidgetConfig(type="button", x=0, y=30, width=50, height=20, text="CLOSE"))

    app.sim_input_mode = True
    app._set_focus(0, sync_selection=True)
    assert app.focus_idx == 0

    app._focus_move_direction("up")
    assert app.focus_idx == 1


def test_input_mode_slider_edit_and_adjust(make_app):
    app = make_app(size=(256, 192))
    sc = app.state.current_scene()
    sc.widgets.clear()
    sc.widgets.append(
        WidgetConfig(
            type="slider",
            x=8,
            y=8,
            width=120,
            height=24,
            text="Vol",
            value=10,
            min_value=0,
            max_value=20,
        )
    )

    app.sim_input_mode = True
    app._set_focus(0, sync_selection=True)
    assert app.focus_idx == 0

    app._activate_focused()
    assert app.focus_edit_value is True

    app._adjust_focused_value(3)
    assert int(getattr(sc.widgets[0], "value", 0)) == 13


# ── Per-widget-type draw_widget_preview pixel tests ───────────────────────

BG_COLOR = (0, 0, 0)
FG_COLOR = (240, 240, 240)
SURF_W, SURF_H = 128, 64


def _render_widget(app, wtype, **kwargs):
    """Render a single widget on a black surface and return the surface."""
    ww = kwargs.pop("width", 100)
    wh = kwargs.pop("height", 40)
    defaults = dict(color_fg="#f0f0f0", color_bg="black")
    defaults.update(kwargs)
    surf = pygame.Surface((SURF_W, SURF_H))
    surf.fill(BG_COLOR)
    w = WidgetConfig(type=wtype, x=0, y=0, width=ww, height=wh, **defaults)
    rect = pygame.Rect(4, 4, ww, wh)
    drawing.draw_widget_preview(app, surf, w, rect, BG_COLOR, 2, False)
    return surf


def _has_nonbg_pixels(surf, region):
    """Check if any pixel in region differs from BG_COLOR."""
    for x in range(region.left, min(region.right, surf.get_width())):
        for y in range(region.top, min(region.bottom, surf.get_height())):
            if surf.get_at((x, y))[:3] != BG_COLOR:
                return True
    return False


def test_widget_label_renders_text(make_app):
    app = make_app(size=(256, 192))
    surf = _render_widget(app, "label", text="HELLO", border=False, border_style="none")
    text_area = pygame.Rect(4, 4, 60, 20)
    assert _has_nonbg_pixels(surf, text_area), "label text should produce pixels"


def test_widget_button_renders_bevel(make_app):
    app = make_app(size=(256, 192))
    surf = _render_widget(
        app, "button", text="OK", border=True, border_style="single", color_bg="#303030"
    )
    # Button fills its rect with bg (non-black), so it should differ from surface
    full_area = pygame.Rect(4, 4, 100, 40)
    assert _has_nonbg_pixels(surf, full_area), "button should have visible fill/text"


def test_widget_checkbox_unchecked(make_app):
    app = make_app(size=(256, 192))
    surf = _render_widget(app, "checkbox", text="OPT", checked=False)
    box_area = pygame.Rect(4, 4, GRID + 4, GRID + 4)
    assert _has_nonbg_pixels(surf, box_area), "checkbox box should be visible"


def test_widget_checkbox_checked_has_cross(make_app):
    app = make_app(size=(256, 192))
    surf_unchecked = _render_widget(app, "checkbox", text="OPT", checked=False)
    surf_checked = _render_widget(app, "checkbox", text="OPT", checked=True)
    # Count non-bg pixels in the checkbox box area
    box_area = pygame.Rect(4, 4, GRID + 4, GRID + 4)
    unchecked_px = sum(
        1
        for x in range(box_area.left, box_area.right)
        for y in range(box_area.top, box_area.bottom)
        if surf_unchecked.get_at((x, y))[:3] != BG_COLOR
    )
    checked_px = sum(
        1
        for x in range(box_area.left, box_area.right)
        for y in range(box_area.top, box_area.bottom)
        if surf_checked.get_at((x, y))[:3] != BG_COLOR
    )
    assert checked_px > unchecked_px, "checked checkbox should have more pixels (cross)"


def test_widget_radiobutton_renders_circle(make_app):
    app = make_app(size=(256, 192))
    surf = _render_widget(
        app, "radiobutton", text="OPT", checked=False, border=False, border_style="none"
    )
    circle_area = pygame.Rect(4, 4, GRID + 4, 40)
    assert _has_nonbg_pixels(surf, circle_area), "radiobutton ring should be visible"


def test_widget_radiobutton_checked_fills(make_app):
    app = make_app(size=(256, 192))
    surf_off = _render_widget(
        app, "radiobutton", text="R", checked=False, border=False, border_style="none"
    )
    surf_on = _render_widget(
        app, "radiobutton", text="R", checked=True, border=False, border_style="none"
    )
    area = pygame.Rect(4, 4, GRID + 4, 40)
    off_px = sum(
        1
        for x in range(area.left, area.right)
        for y in range(area.top, area.bottom)
        if surf_off.get_at((x, y))[:3] != BG_COLOR
    )
    on_px = sum(
        1
        for x in range(area.left, area.right)
        for y in range(area.top, area.bottom)
        if surf_on.get_at((x, y))[:3] != BG_COLOR
    )
    assert on_px > off_px, "checked radiobutton should have filled inner circle"


def test_widget_progressbar_fill(make_app):
    app = make_app(size=(256, 192))
    surf_empty = _render_widget(app, "progressbar", value=0, min_value=0, max_value=100)
    surf_half = _render_widget(app, "progressbar", value=50, min_value=0, max_value=100)
    # Right half should have more pixels when 50% filled
    right = pygame.Rect(50, 4, 50, 40)
    empty_right = sum(
        1
        for x in range(right.left, right.right)
        for y in range(right.top, right.bottom)
        if surf_empty.get_at((x, y))[:3] != BG_COLOR
    )
    half_right = sum(
        1
        for x in range(right.left, right.right)
        for y in range(right.top, right.bottom)
        if surf_half.get_at((x, y))[:3] != BG_COLOR
    )
    assert half_right > empty_right, "50% progressbar should fill more than 0%"


def test_widget_slider_renders_knob(make_app):
    app = make_app(size=(256, 192))
    surf = _render_widget(
        app, "slider", value=50, min_value=0, max_value=100, border=False, border_style="none"
    )
    # Slider track + knob should produce visible pixels in center
    center = pygame.Rect(20, 8, 60, 30)
    assert _has_nonbg_pixels(surf, center), "slider should have visible track+knob"


def test_widget_gauge_renders_arc_or_bar(make_app):
    app = make_app(size=(256, 192))
    surf = _render_widget(
        app,
        "gauge",
        value=50,
        min_value=0,
        max_value=100,
        width=60,
        height=60,
        border=False,
        border_style="none",
    )
    area = pygame.Rect(4, 4, 60, 60)
    assert _has_nonbg_pixels(surf, area), "gauge should render arc or bar"


def test_widget_chart_bar_renders_bars(make_app):
    app = make_app(size=(256, 192))
    surf = _render_widget(
        app,
        "chart",
        text="BAR",
        style="bar",
        data_points=[10, 30, 20, 50],
        width=100,
        height=50,
        border=False,
        border_style="none",
    )
    chart_area = pygame.Rect(4, 10, 96, 40)
    assert _has_nonbg_pixels(surf, chart_area), "bar chart should have visible bars"


def test_widget_chart_line_renders_lines(make_app):
    app = make_app(size=(256, 192))
    surf = _render_widget(
        app,
        "chart",
        text="LINE",
        style="line",
        data_points=[5, 15, 10, 20],
        width=100,
        height=50,
        border=False,
        border_style="none",
    )
    chart_area = pygame.Rect(4, 10, 96, 40)
    assert _has_nonbg_pixels(surf, chart_area), "line chart should have visible lines"


def test_widget_textbox_renders_input(make_app):
    app = make_app(size=(256, 192))
    surf = _render_widget(app, "textbox", text="INPUT", border=True, border_style="single")
    text_area = pygame.Rect(4, 4, 80, 40)
    assert _has_nonbg_pixels(surf, text_area), "textbox should render text+border"


def test_widget_icon_renders_char(make_app):
    app = make_app(size=(256, 192))
    surf = _render_widget(
        app, "icon", icon_char="@", width=24, height=24, border=False, border_style="none"
    )
    area = pygame.Rect(4, 4, 24, 24)
    assert _has_nonbg_pixels(surf, area), "icon should render character"


def test_widget_box_renders_filled_rect(make_app):
    app = make_app(size=(256, 192))
    surf = _render_widget(app, "box", border=True, border_style="single", width=60, height=30)
    area = pygame.Rect(4, 4, 60, 30)
    assert _has_nonbg_pixels(surf, area), "box should render filled rect with border"


def test_widget_panel_renders_hatching(make_app):
    app = make_app(size=(256, 192))
    surf = _render_widget(app, "panel", border=True, border_style="single", width=80, height=40)
    area = pygame.Rect(4, 4, 80, 40)
    assert _has_nonbg_pixels(surf, area), "panel should render bg+hatching"


def test_widget_border_styles_all_visible(make_app):
    app = make_app(size=(256, 192))
    for bs in ["single", "double", "rounded", "bold", "dashed"]:
        surf = _render_widget(app, "label", text="X", border=True, border_style=bs)
        edge = pygame.Rect(4, 4, 100, 2)
        assert _has_nonbg_pixels(surf, edge), f"border_style '{bs}' should be visible"
