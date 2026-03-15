"""Tests for untested batch_ops functions (lines 641–1408).

Covers: measure_selection, replace_text_in_scene, scene_overview,
widget_type_summary, toggle_focus_order_overlay, fill_scene,
auto_label_widgets, inset_widgets, outset_widgets, delete_hidden_widgets,
delete_offscreen_widgets, tile_fill_scene, match_first_width,
match_first_height, scatter_random, toggle_all_checked, reset_all_values,
flatten_z_index, number_widget_ids, z_by_position, clone_to_grid,
sort_widgets_by_z, clamp_to_scene, snap_all_to_grid, size_to_text,
fill_parent, clear_all_text, number_text, spread_values, reset_padding,
reset_colors.
"""

from __future__ import annotations

from cyberpunk_designer.constants import GRID
from cyberpunk_designer.selection_ops import (
    auto_label_widgets,
    clamp_to_scene,
    clear_all_text,
    clone_to_grid,
    delete_hidden_widgets,
    delete_offscreen_widgets,
    fill_parent,
    fill_scene,
    flatten_z_index,
    inset_widgets,
    match_first_height,
    match_first_width,
    measure_selection,
    number_text,
    number_widget_ids,
    outset_widgets,
    replace_text_in_scene,
    reset_all_values,
    reset_colors,
    reset_padding,
    scatter_random,
    scene_overview,
    size_to_text,
    snap_all_to_grid,
    sort_widgets_by_z,
    spread_values,
    tile_fill_scene,
    toggle_all_checked,
    toggle_focus_order_overlay,
    widget_type_summary,
    z_by_position,
)
from ui_designer import WidgetConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _add(app, **kw):
    defaults = dict(type="label", x=0, y=0, width=80, height=16, text="W")
    defaults.update(kw)
    w = WidgetConfig(**defaults)
    sc = app.state.current_scene()
    sc.widgets.append(w)
    return w


def _w(app, idx):
    return app.state.current_scene().widgets[idx]


def _sel(app, *indices):
    app.state.selected = list(indices)
    app.state.selected_idx = indices[0] if indices else None


def _count(app):
    return len(app.state.current_scene().widgets)


# ===========================================================================
# measure_selection
# ===========================================================================


class TestMeasureSelection:
    def test_single_widget(self, make_app):
        app = make_app()
        _add(app, x=10, y=20, width=80, height=16)
        _sel(app, 0)
        measure_selection(app)  # status shows pos/size

    def test_two_widgets(self, make_app):
        app = make_app()
        _add(app, x=0, y=0, width=40, height=16)
        _add(app, x=60, y=0, width=40, height=16)
        _sel(app, 0, 1)
        measure_selection(app)  # status shows bbox + gaps

    def test_three_plus_widgets(self, make_app):
        app = make_app()
        for i in range(3):
            _add(app, x=i * 30, y=0, width=20, height=10)
        _sel(app, 0, 1, 2)
        measure_selection(app)  # status shows count + bbox

    def test_empty_selection(self, make_app):
        app = make_app()
        _add(app)
        _sel(app)
        measure_selection(app)  # no crash


# ===========================================================================
# replace_text_in_scene
# ===========================================================================


class TestReplaceTextInScene:
    def test_first_call_sets_flag(self, make_app):
        app = make_app()
        _add(app, text="hello")
        replace_text_in_scene(app)
        assert app._replace_buf == ""

    def test_replace_with_pattern(self, make_app):
        app = make_app()
        _add(app, text="hello world")
        _add(app, text="hello there")
        app._replace_buf = "hello|goodbye"
        replace_text_in_scene(app)
        assert _w(app, 0).text == "goodbye world"
        assert _w(app, 1).text == "goodbye there"
        assert app._replace_buf is None

    def test_invalid_pattern_cancels(self, make_app):
        app = make_app()
        _add(app, text="hello")
        app._replace_buf = "nopipe"
        replace_text_in_scene(app)
        assert _w(app, 0).text == "hello"  # unchanged

    def test_empty_find_cancels(self, make_app):
        app = make_app()
        _add(app, text="hello")
        app._replace_buf = "|replacement"
        replace_text_in_scene(app)
        assert _w(app, 0).text == "hello"


# ===========================================================================
# scene_overview
# ===========================================================================


class TestSceneOverview:
    def test_shows_scene_info(self, make_app):
        app = make_app()
        _add(app, text="w1")
        _add(app, text="w2")
        scene_overview(app)  # no crash, sets status


# ===========================================================================
# widget_type_summary
# ===========================================================================


class TestWidgetTypeSummary:
    def test_shows_type_counts(self, make_app):
        app = make_app()
        _add(app, type="label")
        _add(app, type="button")
        _add(app, type="label")
        widget_type_summary(app)  # no crash

    def test_empty_scene(self, make_app):
        app = make_app()
        widget_type_summary(app)  # no crash


# ===========================================================================
# toggle_focus_order_overlay
# ===========================================================================


class TestToggleFocusOrderOverlay:
    def test_toggles_on(self, make_app):
        app = make_app()
        app.show_focus_order = False
        toggle_focus_order_overlay(app)
        assert app.show_focus_order is True

    def test_toggles_off(self, make_app):
        app = make_app()
        app.show_focus_order = True
        toggle_focus_order_overlay(app)
        assert app.show_focus_order is False


# ===========================================================================
# fill_scene
# ===========================================================================


class TestFillScene:
    def test_fills_widget_to_scene(self, make_app):
        app = make_app()
        _add(app, x=10, y=10, width=40, height=20)
        _sel(app, 0)
        fill_scene(app)
        w = _w(app, 0)
        assert w.x == 0 and w.y == 0
        assert w.width == 256 and w.height == 128

    def test_empty_selection(self, make_app):
        app = make_app()
        _add(app, x=10, width=40)
        _sel(app)
        fill_scene(app)
        assert _w(app, 0).x == 10


# ===========================================================================
# auto_label_widgets
# ===========================================================================


class TestAutoLabelWidgets:
    def test_labels_widgets(self, make_app):
        app = make_app()
        _add(app, type="label", text="x")
        _add(app, type="button", text="y")
        _sel(app, 0, 1)
        auto_label_widgets(app)
        assert _w(app, 0).text == "Label 1"
        assert _w(app, 1).text == "Button 2"

    def test_empty_selection(self, make_app):
        app = make_app()
        _add(app)
        _sel(app)
        auto_label_widgets(app)


# ===========================================================================
# inset_widgets / outset_widgets
# ===========================================================================


class TestInsetWidgets:
    def test_shrinks_inward(self, make_app):
        app = make_app()
        _add(app, x=10, y=10, width=80, height=40)
        _sel(app, 0)
        inset_widgets(app, amount=4)
        w = _w(app, 0)
        assert w.x == 14 and w.y == 14
        assert w.width == 72 and w.height == 32

    def test_default_amount_is_grid(self, make_app):
        app = make_app()
        _add(app, x=0, y=0, width=80, height=40)
        _sel(app, 0)
        inset_widgets(app)
        w = _w(app, 0)
        assert w.x == GRID and w.y == GRID
        assert w.width == 80 - GRID * 2

    def test_too_small_skipped(self, make_app):
        app = make_app()
        _add(app, x=0, y=0, width=10, height=10)
        _sel(app, 0)
        inset_widgets(app, amount=8)
        assert _w(app, 0).width == 10  # too small, skipped

    def test_empty_selection(self, make_app):
        app = make_app()
        _add(app)
        _sel(app)
        inset_widgets(app)


class TestOutsetWidgets:
    def test_expands_outward(self, make_app):
        app = make_app()
        _add(app, x=20, y=20, width=40, height=20)
        _sel(app, 0)
        outset_widgets(app, amount=4)
        w = _w(app, 0)
        assert w.x == 16 and w.y == 16
        assert w.width == 48 and w.height == 28

    def test_clamps_at_zero(self, make_app):
        app = make_app()
        _add(app, x=2, y=2, width=40, height=20)
        _sel(app, 0)
        outset_widgets(app, amount=8)
        assert _w(app, 0).x == 0
        assert _w(app, 0).y == 0

    def test_empty_selection(self, make_app):
        app = make_app()
        _add(app)
        _sel(app)
        outset_widgets(app)


# ===========================================================================
# delete_hidden_widgets / delete_offscreen_widgets
# ===========================================================================


class TestDeleteHiddenWidgets:
    def test_removes_invisible(self, make_app):
        app = make_app()
        _add(app, text="visible")
        w = _add(app, text="hidden")
        w.visible = False
        _sel(app)
        delete_hidden_widgets(app)
        assert _count(app) == 1
        assert _w(app, 0).text == "visible"

    def test_no_hidden(self, make_app):
        app = make_app()
        _add(app)
        delete_hidden_widgets(app)
        assert _count(app) == 1


class TestDeleteOffscreenWidgets:
    def test_removes_offscreen(self, make_app):
        app = make_app()
        _add(app, x=10, y=10, width=40, height=16)  # inside
        _add(app, x=300, y=0, width=40, height=16)  # outside right
        _add(app, x=-100, y=0, width=40, height=16)  # outside left
        delete_offscreen_widgets(app)
        assert _count(app) == 1

    def test_no_offscreen(self, make_app):
        app = make_app()
        _add(app, x=10, y=10, width=40, height=16)
        delete_offscreen_widgets(app)
        assert _count(app) == 1


# ===========================================================================
# tile_fill_scene
# ===========================================================================


class TestTileFillScene:
    def test_tiles_single_widget(self, make_app):
        app = make_app()
        _add(app, x=10, y=10, width=64, height=32)
        _sel(app, 0)
        tile_fill_scene(app)
        # 256/64=4 cols, 128/32=4 rows → 16 tiles
        assert _count(app) >= 4  # at least some tiling happened

    def test_requires_single_selection(self, make_app):
        app = make_app()
        _add(app, width=64, height=32)
        _add(app, width=64, height=32)
        _sel(app, 0, 1)
        tile_fill_scene(app)  # noop, 2 selected
        assert _count(app) == 2

    def test_empty_selection(self, make_app):
        app = make_app()
        _add(app)
        _sel(app)
        tile_fill_scene(app)


# ===========================================================================
# match_first_width / match_first_height
# ===========================================================================


class TestMatchFirstWidth:
    def test_sets_to_first_width(self, make_app):
        app = make_app()
        _add(app, width=100)
        _add(app, width=50)
        _add(app, width=30)
        _sel(app, 0, 1, 2)
        match_first_width(app)
        assert _w(app, 1).width == 100
        assert _w(app, 2).width == 100
        assert _w(app, 0).width == 100  # first unchanged

    def test_less_than_two_noop(self, make_app):
        app = make_app()
        _add(app, width=80)
        _sel(app, 0)
        match_first_width(app)


class TestMatchFirstHeight:
    def test_sets_to_first_height(self, make_app):
        app = make_app()
        _add(app, height=40)
        _add(app, height=16)
        _add(app, height=20)
        _sel(app, 0, 1, 2)
        match_first_height(app)
        assert _w(app, 1).height == 40
        assert _w(app, 2).height == 40

    def test_less_than_two_noop(self, make_app):
        app = make_app()
        _add(app, height=40)
        _sel(app, 0)
        match_first_height(app)


# ===========================================================================
# scatter_random
# ===========================================================================


class TestScatterRandom:
    def test_moves_widgets(self, make_app):
        app = make_app()
        _add(app, x=0, y=0, width=20, height=16)
        _add(app, x=0, y=0, width=20, height=16)
        _sel(app, 0, 1)
        scatter_random(app)
        # After scatter, widgets should be within scene
        for i in range(2):
            w = _w(app, i)
            assert 0 <= w.x <= 256
            assert 0 <= w.y <= 128

    def test_empty_selection(self, make_app):
        app = make_app()
        _add(app, x=10, y=10)
        _sel(app)
        scatter_random(app)
        assert _w(app, 0).x == 10


# ===========================================================================
# toggle_all_checked
# ===========================================================================


class TestToggleAllChecked:
    def test_toggles_checkboxes(self, make_app):
        app = make_app()
        _add(app, type="checkbox", checked=False)
        _add(app, type="checkbox", checked=True)
        _sel(app, 0, 1)
        toggle_all_checked(app)
        assert _w(app, 0).checked is True
        assert _w(app, 1).checked is False

    def test_ignores_non_checkbox(self, make_app):
        app = make_app()
        _add(app, type="label")
        _sel(app, 0)
        toggle_all_checked(app)  # no crash, no change

    def test_empty_selection(self, make_app):
        app = make_app()
        _add(app, type="checkbox")
        _sel(app)
        toggle_all_checked(app)


# ===========================================================================
# reset_all_values
# ===========================================================================


class TestResetAllValues:
    def test_resets_to_min(self, make_app):
        app = make_app()
        _add(app, type="gauge", value=75, min_value=10, max_value=100)
        _add(app, type="slider", value=50, min_value=0, max_value=100)
        _sel(app, 0, 1)
        reset_all_values(app)
        assert _w(app, 0).value == 10
        assert _w(app, 1).value == 0

    def test_ignores_non_value_types(self, make_app):
        app = make_app()
        _add(app, type="label")
        _sel(app, 0)
        reset_all_values(app)  # no crash

    def test_empty_selection(self, make_app):
        app = make_app()
        _add(app, type="gauge", value=50)
        _sel(app)
        reset_all_values(app)


# ===========================================================================
# flatten_z_index
# ===========================================================================


class TestFlattenZIndex:
    def test_resets_z_to_zero(self, make_app):
        app = make_app()
        w1 = _add(app)
        w2 = _add(app)
        w1.z_index = 5
        w2.z_index = 10
        flatten_z_index(app)
        assert _w(app, 0).z_index == 0
        assert _w(app, 1).z_index == 0

    def test_already_zero(self, make_app):
        app = make_app()
        _add(app)
        flatten_z_index(app)  # no crash

    def test_empty_scene(self, make_app):
        app = make_app()
        flatten_z_index(app)  # no crash


# ===========================================================================
# number_widget_ids
# ===========================================================================


class TestNumberWidgetIds:
    def test_assigns_ids(self, make_app):
        app = make_app()
        _add(app, type="label")
        _add(app, type="button")
        _add(app, type="label")
        number_widget_ids(app)
        assert _w(app, 0)._widget_id == "label_0"
        assert _w(app, 1)._widget_id == "button_0"
        assert _w(app, 2)._widget_id == "label_1"

    def test_empty_scene(self, make_app):
        app = make_app()
        number_widget_ids(app)


# ===========================================================================
# z_by_position
# ===========================================================================


class TestZByPosition:
    def test_z_order_by_position(self, make_app):
        app = make_app()
        _add(app, x=100, y=100)  # last in position
        _add(app, x=0, y=0)  # first in position
        _add(app, x=50, y=50)  # middle
        z_by_position(app)
        assert _w(app, 1).z_index == 0  # (0,0) is first
        assert _w(app, 2).z_index == 1  # (50,50) second
        assert _w(app, 0).z_index == 2  # (100,100) third

    def test_empty_scene(self, make_app):
        app = make_app()
        z_by_position(app)


# ===========================================================================
# clone_to_grid
# ===========================================================================


class TestCloneToGrid:
    def test_clones_into_grid(self, make_app):
        app = make_app()
        _add(app, x=10, y=10, width=32, height=16, text="cell")
        _sel(app, 0)
        clone_to_grid(app)
        assert _count(app) > 1  # multiple copies created
        assert _w(app, 0).x == 0  # original repositioned to 0,0

    def test_requires_single_selection(self, make_app):
        app = make_app()
        _add(app, width=32, height=16)
        _add(app, width=32, height=16)
        _sel(app, 0, 1)
        clone_to_grid(app)  # noop
        assert _count(app) == 2

    def test_no_selection(self, make_app):
        app = make_app()
        _add(app)
        _sel(app)
        clone_to_grid(app)


# ===========================================================================
# sort_widgets_by_z
# ===========================================================================


class TestSortWidgetsByZ:
    def test_sorts_by_z_index(self, make_app):
        app = make_app()
        w1 = _add(app, text="A")
        w2 = _add(app, text="B")
        w3 = _add(app, text="C")
        w1.z_index = 3
        w2.z_index = 1
        w3.z_index = 2
        sort_widgets_by_z(app)
        assert _w(app, 0).text == "B"  # z=1
        assert _w(app, 1).text == "C"  # z=2
        assert _w(app, 2).text == "A"  # z=3

    def test_less_than_two_noop(self, make_app):
        app = make_app()
        _add(app)
        sort_widgets_by_z(app)


# ===========================================================================
# clamp_to_scene
# ===========================================================================


class TestClampToScene:
    def test_clamps_negative(self, make_app):
        app = make_app()
        _add(app, x=-20, y=-10, width=40, height=16)
        _sel(app, 0)
        clamp_to_scene(app)
        assert _w(app, 0).x == 0
        assert _w(app, 0).y == 0

    def test_clamps_overflow(self, make_app):
        app = make_app()
        _add(app, x=240, y=120, width=40, height=16)
        _sel(app, 0)
        clamp_to_scene(app)
        assert _w(app, 0).x == 256 - 40
        assert _w(app, 0).y == 128 - 16

    def test_already_inside(self, make_app):
        app = make_app()
        _add(app, x=10, y=10, width=40, height=16)
        _sel(app, 0)
        clamp_to_scene(app)
        assert _w(app, 0).x == 10
        assert _w(app, 0).y == 10

    def test_empty_selection(self, make_app):
        app = make_app()
        _add(app, x=-10)
        _sel(app)
        clamp_to_scene(app)
        assert _w(app, 0).x == -10


# ===========================================================================
# snap_all_to_grid
# ===========================================================================


class TestSnapAllToGrid:
    def test_snaps_all_dimensions(self, make_app):
        app = make_app()
        _add(app, x=5, y=13, width=33, height=19)
        _sel(app, 0)
        snap_all_to_grid(app)
        w = _w(app, 0)
        assert w.x % GRID == 0
        assert w.y % GRID == 0
        assert w.width % GRID == 0
        assert w.height % GRID == 0
        assert w.width >= GRID
        assert w.height >= GRID

    def test_empty_selection(self, make_app):
        app = make_app()
        _add(app, x=5, y=5)
        _sel(app)
        snap_all_to_grid(app)
        assert _w(app, 0).x == 5


# ===========================================================================
# size_to_text
# ===========================================================================


class TestSizeToText:
    def test_resizes_to_text_length(self, make_app):
        app = make_app()
        _add(app, text="Hello", width=200, padding_x=1)
        _sel(app, 0)
        size_to_text(app)
        # 5 chars * 6px + 1*2 padding = 32 → snap to grid
        w = _w(app, 0)
        assert w.width < 200  # should shrink
        assert w.width >= GRID

    def test_empty_text_skipped(self, make_app):
        app = make_app()
        _add(app, text="", width=80)
        _sel(app, 0)
        size_to_text(app)
        assert _w(app, 0).width == 80  # unchanged

    def test_empty_selection(self, make_app):
        app = make_app()
        _add(app, text="hi", width=80)
        _sel(app)
        size_to_text(app)
        assert _w(app, 0).width == 80


# ===========================================================================
# fill_parent
# ===========================================================================


class TestFillParent:
    def test_fills_enclosing_panel(self, make_app):
        app = make_app()
        _add(app, type="panel", x=0, y=0, width=100, height=60)
        _add(app, type="label", x=5, y=5, width=20, height=10)
        _sel(app, 1)
        fill_parent(app)
        w = _w(app, 1)
        assert w.x == GRID
        assert w.y == GRID
        assert w.width == 100 - GRID * 2
        assert w.height == 60 - GRID * 2

    def test_no_parent(self, make_app):
        app = make_app()
        _add(app, type="label", x=5, y=5, width=20, height=10)
        _sel(app, 0)
        fill_parent(app)
        assert _w(app, 0).width == 20  # unchanged

    def test_empty_selection(self, make_app):
        app = make_app()
        _add(app, type="panel", x=0, y=0, width=100, height=60)
        _sel(app)
        fill_parent(app)


# ===========================================================================
# clear_all_text
# ===========================================================================


class TestClearAllText:
    def test_clears_text(self, make_app):
        app = make_app()
        _add(app, text="Hello")
        _add(app, text="World")
        _sel(app, 0, 1)
        clear_all_text(app)
        assert _w(app, 0).text == ""
        assert _w(app, 1).text == ""

    def test_empty_selection(self, make_app):
        app = make_app()
        _add(app, text="Hi")
        _sel(app)
        clear_all_text(app)
        assert _w(app, 0).text == "Hi"


# ===========================================================================
# number_text
# ===========================================================================


class TestNumberText:
    def test_numbers_by_position(self, make_app):
        app = make_app()
        _add(app, x=100, y=100, text="x")  # position: last
        _add(app, x=0, y=0, text="y")  # position: first
        _add(app, x=50, y=50, text="z")  # position: middle
        _sel(app, 0, 1, 2)
        number_text(app)
        assert _w(app, 1).text == "1"  # (0,0)
        assert _w(app, 2).text == "2"  # (50,50)
        assert _w(app, 0).text == "3"  # (100,100)

    def test_empty_selection(self, make_app):
        app = make_app()
        _add(app, text="x")
        _sel(app)
        number_text(app)
        assert _w(app, 0).text == "x"


# ===========================================================================
# spread_values
# ===========================================================================


class TestSpreadValues:
    def test_linear_spread(self, make_app):
        app = make_app()
        _add(app, type="gauge", x=0, y=0, value=0, min_value=0, max_value=100)
        _add(app, type="gauge", x=0, y=10, value=0, min_value=0, max_value=100)
        _add(app, type="gauge", x=0, y=20, value=0, min_value=0, max_value=100)
        _sel(app, 0, 1, 2)
        spread_values(app)
        assert _w(app, 0).value == 0
        assert _w(app, 1).value == 50
        assert _w(app, 2).value == 100

    def test_less_than_two_noop(self, make_app):
        app = make_app()
        _add(app, type="gauge", value=50)
        _sel(app, 0)
        spread_values(app)

    def test_non_value_types_skipped(self, make_app):
        app = make_app()
        _add(app, type="label")
        _add(app, type="label")
        _sel(app, 0, 1)
        spread_values(app)  # not enough value widgets


# ===========================================================================
# reset_padding
# ===========================================================================


class TestResetPadding:
    def test_zeros_padding_and_margin(self, make_app):
        app = make_app()
        _add(app, padding_x=5, padding_y=3, margin_x=2, margin_y=4)
        _sel(app, 0)
        reset_padding(app)
        w = _w(app, 0)
        assert w.padding_x == 0
        assert w.padding_y == 0
        assert w.margin_x == 0
        assert w.margin_y == 0

    def test_already_zero(self, make_app):
        app = make_app()
        _add(app, padding_x=0, padding_y=0, margin_x=0, margin_y=0)
        _sel(app, 0)
        reset_padding(app)  # no change but no crash

    def test_empty_selection(self, make_app):
        app = make_app()
        _add(app, padding_x=5)
        _sel(app)
        reset_padding(app)
        assert _w(app, 0).padding_x == 5


# ===========================================================================
# reset_colors
# ===========================================================================


class TestResetColors:
    def test_resets_to_white_black(self, make_app):
        app = make_app()
        _add(app, color_fg="red", color_bg="blue")
        _sel(app, 0)
        reset_colors(app)
        assert _w(app, 0).color_fg == "white"
        assert _w(app, 0).color_bg == "black"

    def test_already_default(self, make_app):
        app = make_app()
        _add(app, color_fg="white", color_bg="black")
        _sel(app, 0)
        reset_colors(app)  # no change needed

    def test_empty_selection(self, make_app):
        app = make_app()
        _add(app, color_fg="red")
        _sel(app)
        reset_colors(app)
        assert _w(app, 0).color_fg == "red"
