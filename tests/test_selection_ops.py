"""Tests for cyberpunk_designer/selection_ops.py — core selection, copy/paste,
delete, reorder, toggle, cycle, and search operations."""

from __future__ import annotations

from types import SimpleNamespace
from typing import List, Optional
from unittest.mock import MagicMock

import pygame

from cyberpunk_designer.selection_ops import (
    adjust_value,
    apply_click_selection,
    arrange_in_column,
    arrange_in_row,
    copy_selection,
    copy_style,
    cut_selection,
    cycle_align,
    cycle_border_style,
    cycle_color_preset,
    cycle_style,
    cycle_text_overflow,
    cycle_valign,
    cycle_widget_type,
    delete_selected,
    duplicate_selection,
    mirror_selection,
    move_selection,
    paste_style,
    reorder_selection,
    resize_selection_to,
    search_widgets,
    select_all,
    selection_bounds,
    set_selection,
    swap_fg_bg,
    toggle_border,
    toggle_enabled,
    toggle_visibility,
)
from cyberpunk_designer.state import EditorState
from ui_designer import UIDesigner, WidgetConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _w(**kw) -> WidgetConfig:
    defaults = dict(type="label", x=0, y=0, width=20, height=10, text="w")
    defaults.update(kw)
    return WidgetConfig(**defaults)


def _app(widgets: Optional[List[WidgetConfig]] = None, *, snap: bool = False):
    designer = UIDesigner(256, 128)
    designer.create_scene("main")
    sc = designer.scenes["main"]
    for w in (widgets or []):
        sc.widgets.append(w)
    layout = MagicMock()
    layout.canvas_rect = pygame.Rect(0, 0, 256, 128)
    state = EditorState(designer, layout)
    app = SimpleNamespace(
        designer=designer,
        state=state,
        snap_enabled=snap,
        clipboard=[],
        pointer_pos=(0, 0),
        scene_rect=pygame.Rect(0, 0, 256, 128),
        layout=layout,
        _dirty=False,
        _set_status=MagicMock(),
        _mark_dirty=lambda: setattr(app, "_dirty", True),
        _primary_group_for_index=lambda idx: None,
        _group_members=lambda name: [],
        _selection_bounds=lambda indices: selection_bounds(app, indices),
        _move_selection=MagicMock(),
        _set_selection=lambda indices, anchor_idx=None: set_selection(app, indices, anchor_idx),
    )
    app._mark_dirty = lambda: setattr(app, "_dirty", True)
    return app


# ---------------------------------------------------------------------------
# set_selection
# ---------------------------------------------------------------------------


class TestSetSelection:
    def test_basic(self):
        app = _app([_w(), _w(), _w()])
        set_selection(app, [0, 2])
        assert app.state.selected == [0, 2]
        assert app.state.selected_idx == 0

    def test_with_anchor(self):
        app = _app([_w(), _w(), _w()])
        set_selection(app, [0, 1, 2], anchor_idx=2)
        assert app.state.selected_idx == 2

    def test_deduplicates_and_sorts(self):
        app = _app([_w(), _w(), _w()])
        set_selection(app, [2, 0, 2, 1])
        assert app.state.selected == [0, 1, 2]

    def test_invalid_indices_filtered(self):
        app = _app([_w()])
        set_selection(app, [0, 5, -1])
        assert app.state.selected == [0]

    def test_empty_clears(self):
        app = _app([_w()])
        set_selection(app, [0])
        set_selection(app, [])
        assert app.state.selected == []
        assert app.state.selected_idx is None


# ---------------------------------------------------------------------------
# selection_bounds
# ---------------------------------------------------------------------------


class TestSelectionBounds:
    def test_single_widget(self):
        app = _app([_w(x=10, y=20, width=30, height=15)])
        r = selection_bounds(app, [0])
        assert r.x == 10
        assert r.y == 20
        assert r.width == 30
        assert r.height == 15

    def test_multiple_widgets(self):
        app = _app([_w(x=0, y=0, width=10, height=10),
                     _w(x=50, y=60, width=20, height=20)])
        r = selection_bounds(app, [0, 1])
        assert r.x == 0
        assert r.y == 0
        assert r.right == 70
        assert r.bottom == 80

    def test_no_widgets_returns_none(self):
        app = _app([])
        assert selection_bounds(app, []) is None

    def test_invalid_index_filtered(self):
        app = _app([_w(x=5, y=5, width=10, height=10)])
        r = selection_bounds(app, [0, 99])
        assert r is not None
        assert r.x == 5


# ---------------------------------------------------------------------------
# select_all
# ---------------------------------------------------------------------------


class TestSelectAll:
    def test_selects_all(self):
        app = _app([_w(), _w(), _w()])
        select_all(app)
        assert app.state.selected == [0, 1, 2]

    def test_empty_scene(self):
        app = _app([])
        select_all(app)
        assert app.state.selected == []


# ---------------------------------------------------------------------------
# move_selection
# ---------------------------------------------------------------------------


class TestMoveSelection:
    def test_basic_move(self):
        app = _app([_w(x=10, y=10, width=20, height=10)])
        set_selection(app, [0])
        move_selection(app, 5, 5)
        assert app.state.current_scene().widgets[0].x == 15
        assert app.state.current_scene().widgets[0].y == 15

    def test_clamps_to_scene(self):
        app = _app([_w(x=240, y=120, width=20, height=10)])
        set_selection(app, [0])
        move_selection(app, 100, 100)
        w = app.state.current_scene().widgets[0]
        assert w.x + w.width <= 256
        assert w.y + w.height <= 128

    def test_no_selection_noop(self):
        app = _app([_w(x=10, y=10)])
        move_selection(app, 5, 5)
        assert app.state.current_scene().widgets[0].x == 10

    def test_locked_widget_blocked(self):
        app = _app([_w(x=10, y=10, locked=True)])
        set_selection(app, [0])
        move_selection(app, 5, 5)
        assert app.state.current_scene().widgets[0].x == 10


# ---------------------------------------------------------------------------
# delete_selected
# ---------------------------------------------------------------------------


class TestDeleteSelected:
    def test_deletes_widget(self):
        app = _app([_w(), _w()])
        set_selection(app, [0])
        delete_selected(app)
        assert len(app.state.current_scene().widgets) == 1

    def test_no_selection_noop(self):
        app = _app([_w()])
        delete_selected(app)
        assert len(app.state.current_scene().widgets) == 1

    def test_locked_widget_skipped(self):
        app = _app([_w(locked=True), _w()])
        set_selection(app, [0, 1])
        delete_selected(app)
        # locked one survives
        assert len(app.state.current_scene().widgets) == 1


# ---------------------------------------------------------------------------
# copy / duplicate
# ---------------------------------------------------------------------------


class TestCopySelection:
    def test_copies_to_clipboard(self):
        app = _app([_w(text="a"), _w(text="b")])
        set_selection(app, [0, 1])
        copy_selection(app)
        assert len(app.clipboard) == 2
        assert app.clipboard[0].text == "a"

    def test_no_selection(self):
        app = _app([_w()])
        copy_selection(app)
        assert app.clipboard == []


class TestDuplicateSelection:
    def test_duplicates(self):
        app = _app([_w(text="orig")])
        set_selection(app, [0])
        duplicate_selection(app)
        sc = app.state.current_scene()
        assert len(sc.widgets) == 2
        assert sc.widgets[1].text == "orig"

    def test_no_selection_noop(self):
        app = _app([_w()])
        duplicate_selection(app)
        assert len(app.state.current_scene().widgets) == 1


class TestCutSelection:
    def test_cut_removes_and_copies(self):
        app = _app([_w(text="x"), _w(text="y")])
        set_selection(app, [0])
        cut_selection(app)
        assert len(app.state.current_scene().widgets) == 1
        assert len(app.clipboard) == 1
        assert app.clipboard[0].text == "x"


# ---------------------------------------------------------------------------
# reorder_selection
# ---------------------------------------------------------------------------


class TestReorderSelection:
    def test_move_up(self):
        app = _app([_w(text="a"), _w(text="b"), _w(text="c")])
        set_selection(app, [2])
        reorder_selection(app, -1)
        texts = [w.text for w in app.state.current_scene().widgets]
        assert texts == ["a", "c", "b"]

    def test_move_down(self):
        app = _app([_w(text="a"), _w(text="b"), _w(text="c")])
        set_selection(app, [0])
        reorder_selection(app, 1)
        texts = [w.text for w in app.state.current_scene().widgets]
        assert texts == ["b", "a", "c"]

    def test_already_at_top(self):
        app = _app([_w(text="a"), _w(text="b")])
        set_selection(app, [0])
        reorder_selection(app, -1)  # can't go further up
        texts = [w.text for w in app.state.current_scene().widgets]
        assert texts == ["a", "b"]  # unchanged


# ---------------------------------------------------------------------------
# toggle / cycle
# ---------------------------------------------------------------------------


class TestToggleVisibility:
    def test_hides_visible(self):
        app = _app([_w(visible=True)])
        set_selection(app, [0])
        toggle_visibility(app)
        assert app.state.current_scene().widgets[0].visible is False

    def test_shows_hidden(self):
        app = _app([_w(visible=False)])
        set_selection(app, [0])
        toggle_visibility(app)
        assert app.state.current_scene().widgets[0].visible is True


class TestCycleStyle:
    def test_cycles(self):
        app = _app([_w(style="default")])
        set_selection(app, [0])
        cycle_style(app)
        assert app.state.current_scene().widgets[0].style == "bold"

    def test_wraps(self):
        app = _app([_w(style="highlight")])
        set_selection(app, [0])
        cycle_style(app)
        assert app.state.current_scene().widgets[0].style == "default"


class TestCycleWidgetType:
    def test_cycles(self):
        app = _app([_w(type="label")])
        set_selection(app, [0])
        cycle_widget_type(app)
        assert app.state.current_scene().widgets[0].type == "button"


class TestCycleBorderStyle:
    def test_cycles(self):
        app = _app([_w(border_style="single")])
        set_selection(app, [0])
        cycle_border_style(app)
        assert app.state.current_scene().widgets[0].border_style == "double"


# ---------------------------------------------------------------------------
# swap_fg_bg
# ---------------------------------------------------------------------------


class TestSwapFgBg:
    def test_swaps_colors(self):
        app = _app([_w(color_fg="white", color_bg="black")])
        set_selection(app, [0])
        swap_fg_bg(app)
        w = app.state.current_scene().widgets[0]
        assert w.color_fg == "black"
        assert w.color_bg == "white"


# ---------------------------------------------------------------------------
# resize_selection_to
# ---------------------------------------------------------------------------


class TestResizeSelectionTo:
    def test_resize(self):
        app = _app([_w(x=0, y=0, width=20, height=10)])
        set_selection(app, [0])
        ok = resize_selection_to(app, 40, 20)
        assert ok is True
        w = app.state.current_scene().widgets[0]
        assert w.width == 40
        assert w.height == 20

    def test_no_selection_returns_false(self):
        app = _app([_w()])
        assert resize_selection_to(app, 40, 20) is False


# ---------------------------------------------------------------------------
# search_widgets
# ---------------------------------------------------------------------------


class TestSearchWidgets:
    def test_finds_by_text(self):
        app = _app([_w(text="hello"), _w(text="world"), _w(text="hello2")])
        search_widgets(app, "hello")
        assert 0 in app.state.selected
        assert 2 in app.state.selected
        assert 1 not in app.state.selected

    def test_finds_by_type(self):
        app = _app([_w(type="button"), _w(type="label")])
        search_widgets(app, "button")
        assert app.state.selected == [0]

    def test_empty_query(self):
        app = _app([_w()])
        search_widgets(app, "")
        assert app.state.selected == []


# ---------------------------------------------------------------------------
# apply_click_selection
# ---------------------------------------------------------------------------


class TestApplyClickSelection:
    def test_plain_click(self):
        app = _app([_w(), _w(), _w()])
        apply_click_selection(app, 1, 0)
        assert app.state.selected == [1]

    def test_ctrl_click_adds(self):
        app = _app([_w(), _w(), _w()])
        set_selection(app, [0])
        apply_click_selection(app, 2, pygame.KMOD_CTRL)
        assert 0 in app.state.selected
        assert 2 in app.state.selected

    def test_ctrl_click_removes(self):
        app = _app([_w(), _w(), _w()])
        set_selection(app, [0, 1])
        apply_click_selection(app, 0, pygame.KMOD_CTRL)
        assert app.state.selected == [1]

    def test_shift_click_range(self):
        app = _app([_w(), _w(), _w(), _w()])
        set_selection(app, [1])
        apply_click_selection(app, 3, pygame.KMOD_SHIFT)
        assert app.state.selected == [1, 2, 3]


# ---------------------------------------------------------------------------
# arrange_in_row / arrange_in_column
# ---------------------------------------------------------------------------


class TestArrangeInRow:
    def test_basic_row(self):
        w0 = _w(x=10, y=20, width=20, height=10)
        w1 = _w(x=100, y=50, width=30, height=10)
        app = _app([w0, w1])
        set_selection(app, [0, 1])
        arrange_in_row(app)
        sc = app.designer.scenes["main"]
        # Both at same y
        assert sc.widgets[0].y == 20
        assert sc.widgets[1].y == 20
        # Second starts after first + GRID spacing
        assert sc.widgets[1].x > sc.widgets[0].x

    def test_row_needs_two(self):
        app = _app([_w()])
        set_selection(app, [0])
        arrange_in_row(app)
        # status message about 2+ widgets
        app._set_status.assert_called()


class TestArrangeInColumn:
    def test_basic_column(self):
        w0 = _w(x=10, y=5, width=20, height=12)
        w1 = _w(x=50, y=80, width=30, height=12)
        app = _app([w0, w1])
        set_selection(app, [0, 1])
        arrange_in_column(app)
        sc = app.designer.scenes["main"]
        # Both at same x
        assert sc.widgets[0].x == 10
        assert sc.widgets[1].x == 10
        # Second starts below first + GRID spacing
        assert sc.widgets[1].y > sc.widgets[0].y

    def test_column_needs_two(self):
        app = _app([_w()])
        set_selection(app, [0])
        arrange_in_column(app)
        app._set_status.assert_called()


# ---------------------------------------------------------------------------
# toggle_border
# ---------------------------------------------------------------------------


class TestToggleBorder:
    def test_toggle_on(self):
        app = _app([_w(border=False)])
        set_selection(app, [0])
        toggle_border(app)
        assert app.designer.scenes["main"].widgets[0].border is True

    def test_toggle_off(self):
        app = _app([_w(border=True)])
        set_selection(app, [0])
        toggle_border(app)
        assert app.designer.scenes["main"].widgets[0].border is False

    def test_empty_selection(self):
        app = _app([_w()])
        toggle_border(app)
        app._set_status.assert_called()


# ---------------------------------------------------------------------------
# toggle_enabled
# ---------------------------------------------------------------------------


class TestToggleEnabled:
    def test_toggle_off(self):
        app = _app([_w(enabled=True)])
        set_selection(app, [0])
        toggle_enabled(app)
        assert app.designer.scenes["main"].widgets[0].enabled is False

    def test_toggle_on(self):
        app = _app([_w(enabled=False)])
        set_selection(app, [0])
        toggle_enabled(app)
        assert app.designer.scenes["main"].widgets[0].enabled is True

    def test_multi_widget(self):
        app = _app([_w(enabled=True), _w(enabled=True)])
        set_selection(app, [0, 1])
        toggle_enabled(app)
        sc = app.designer.scenes["main"]
        assert sc.widgets[0].enabled is False
        assert sc.widgets[1].enabled is False


# ---------------------------------------------------------------------------
# cycle_text_overflow
# ---------------------------------------------------------------------------


class TestCycleTextOverflow:
    def test_cycle_from_ellipsis(self):
        app = _app([_w(text_overflow="ellipsis")])
        set_selection(app, [0])
        cycle_text_overflow(app)
        assert app.designer.scenes["main"].widgets[0].text_overflow == "wrap"

    def test_cycle_from_wrap(self):
        app = _app([_w(text_overflow="wrap")])
        set_selection(app, [0])
        cycle_text_overflow(app)
        assert app.designer.scenes["main"].widgets[0].text_overflow == "clip"

    def test_cycle_wraps_around(self):
        app = _app([_w(text_overflow="auto")])
        set_selection(app, [0])
        cycle_text_overflow(app)
        assert app.designer.scenes["main"].widgets[0].text_overflow == "ellipsis"

    def test_empty_selection(self):
        app = _app([_w()])
        cycle_text_overflow(app)
        app._set_status.assert_called()


# ---------------------------------------------------------------------------
# cycle_align
# ---------------------------------------------------------------------------


class TestCycleAlign:
    def test_cycle_from_left(self):
        app = _app([_w(align="left")])
        set_selection(app, [0])
        cycle_align(app)
        assert app.designer.scenes["main"].widgets[0].align == "center"

    def test_cycle_wraps(self):
        app = _app([_w(align="right")])
        set_selection(app, [0])
        cycle_align(app)
        assert app.designer.scenes["main"].widgets[0].align == "left"


# ---------------------------------------------------------------------------
# cycle_valign
# ---------------------------------------------------------------------------


class TestCycleValign:
    def test_cycle_from_top(self):
        app = _app([_w(valign="top")])
        set_selection(app, [0])
        cycle_valign(app)
        assert app.designer.scenes["main"].widgets[0].valign == "middle"

    def test_cycle_wraps(self):
        app = _app([_w(valign="bottom")])
        set_selection(app, [0])
        cycle_valign(app)
        assert app.designer.scenes["main"].widgets[0].valign == "top"


# ---------------------------------------------------------------------------
# cycle_color_preset
# ---------------------------------------------------------------------------


class TestCycleColorPreset:
    def test_cycle_first(self):
        app = _app([_w(color_fg="#f5f5f5", color_bg="#000000")])
        set_selection(app, [0])
        cycle_color_preset(app)
        w = app.designer.scenes["main"].widgets[0]
        # Should advance to next preset
        assert w.color_fg == "#f5f5f5"
        assert w.color_bg == "#101010"

    def test_cycle_no_selection(self):
        app = _app([_w()])
        cycle_color_preset(app)
        app._set_status.assert_called()

    def test_cycle_unknown_preset(self):
        """Unknown colors → pick first preset."""
        app = _app([_w(color_fg="#abcdef", color_bg="#123456")])
        set_selection(app, [0])
        cycle_color_preset(app)
        w = app.designer.scenes["main"].widgets[0]
        assert w.color_fg == "#f5f5f5"
        assert w.color_bg == "#000000"


# ---------------------------------------------------------------------------
# mirror_selection
# ---------------------------------------------------------------------------


class TestMirrorSelection:
    def test_horizontal_mirror(self):
        w0 = _w(x=10, y=0, width=20, height=10)
        w1 = _w(x=40, y=0, width=20, height=10)
        app = _app([w0, w1])
        set_selection(app, [0, 1])
        mirror_selection(app, "h")
        sc = app.designer.scenes["main"]
        # After horizontal mirror, positions should flip
        assert sc.widgets[0].x == 40
        assert sc.widgets[1].x == 10

    def test_vertical_mirror(self):
        w0 = _w(x=0, y=10, width=20, height=10)
        w1 = _w(x=0, y=40, width=20, height=10)
        app = _app([w0, w1])
        set_selection(app, [0, 1])
        mirror_selection(app, "v")
        sc = app.designer.scenes["main"]
        assert sc.widgets[0].y == 40
        assert sc.widgets[1].y == 10

    def test_empty_selection(self):
        app = _app([_w()])
        mirror_selection(app, "h")
        app._set_status.assert_called()


# ---------------------------------------------------------------------------
# adjust_value
# ---------------------------------------------------------------------------


class TestAdjustValue:
    def test_increase(self):
        app = _app([_w(type="gauge", value=50, min_value=0, max_value=100)])
        set_selection(app, [0])
        adjust_value(app, 10)
        assert app.designer.scenes["main"].widgets[0].value == 60

    def test_decrease(self):
        app = _app([_w(type="slider", value=30, min_value=0, max_value=100)])
        set_selection(app, [0])
        adjust_value(app, -10)
        assert app.designer.scenes["main"].widgets[0].value == 20

    def test_clamps_at_max(self):
        app = _app([_w(type="gauge", value=95, min_value=0, max_value=100)])
        set_selection(app, [0])
        adjust_value(app, 10)
        assert app.designer.scenes["main"].widgets[0].value == 100

    def test_clamps_at_min(self):
        app = _app([_w(type="progressbar", value=5, min_value=0, max_value=100)])
        set_selection(app, [0])
        adjust_value(app, -20)
        assert app.designer.scenes["main"].widgets[0].value == 0

    def test_non_value_type_ignored(self):
        app = _app([_w(type="label", value=50)])
        set_selection(app, [0])
        adjust_value(app, 10)
        # Label is not gauge/slider/progressbar — value unchanged
        assert app.designer.scenes["main"].widgets[0].value == 50


# ---------------------------------------------------------------------------
# copy_style / paste_style
# ---------------------------------------------------------------------------


class TestCopyPasteStyle:
    def test_roundtrip(self):
        w0 = _w(style="rounded", color_fg="#aaa", color_bg="#bbb",
                border=True, border_style="double", align="center", valign="top")
        w1 = _w()
        app = _app([w0, w1])
        set_selection(app, [0])
        copy_style(app)
        set_selection(app, [1])
        paste_style(app)
        t = app.designer.scenes["main"].widgets[1]
        assert t.style == "rounded"
        assert t.color_fg == "#aaa"
        assert t.color_bg == "#bbb"
        assert t.border is True
        assert t.border_style == "double"
        assert t.align == "center"
        assert t.valign == "top"

    def test_paste_without_copy(self):
        app = _app([_w()])
        set_selection(app, [0])
        paste_style(app)
        app._set_status.assert_called()

    def test_copy_no_selection(self):
        app = _app([_w()])
        copy_style(app)
        app._set_status.assert_called()
