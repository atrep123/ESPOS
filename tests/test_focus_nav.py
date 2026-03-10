"""Tests for cyberpunk_designer/focus_nav.py — focus navigation, widget
focusability, sim runtime, list model helpers, and directional movement."""

from __future__ import annotations

from types import SimpleNamespace
from typing import List, Optional
from unittest.mock import MagicMock

import pygame

from cyberpunk_designer.focus_nav import (
    _count_item_slots,
    _find_by_widget_id,
    _listmodel_clamp,
    _listmodel_item_text,
    _listmodel_move_active,
    _parse_scroll_text,
    _sim_snapshot_widget,
    _SimListModel,
    _SimWidgetSnapshot,
    activate_focused,
    adjust_focused_value,
    ensure_focus,
    focus_cycle,
    focus_move_direction,
    focusable_indices,
    is_widget_focusable,
    set_focus,
    sim_runtime_reset,
    sim_runtime_restore,
)
from cyberpunk_designer.state import EditorState
from ui_designer import UIDesigner, WidgetConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _w(wtype="label", **kw) -> WidgetConfig:
    defaults = dict(type=wtype, x=0, y=0, width=20, height=10, text="w")
    defaults.update(kw)
    return WidgetConfig(**defaults)


def _scene(widgets=None, width=256, height=128):
    """Return a SimpleNamespace scene with a widget list."""
    return SimpleNamespace(
        widgets=list(widgets or []),
        width=width,
        height=height,
    )


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
        focus_idx=None,
        focus_edit_value=False,
        sim_input_mode=False,
        pointer_pos=(0, 0),
        scene_rect=pygame.Rect(0, 0, 256, 128),
        layout=layout,
        _dirty=False,
        _set_status=MagicMock(),
        _mark_dirty=lambda: setattr(app, "_dirty", True),
        _set_selection=lambda indices, anchor_idx=None: _do_set_selection(
            app, indices, anchor_idx
        ),
    )
    app._mark_dirty = lambda: setattr(app, "_dirty", True)
    return app


def _do_set_selection(app, indices, anchor_idx=None):
    app.state.selected = list(indices)
    if anchor_idx is not None:
        app.state.selected_idx = anchor_idx
    elif indices:
        app.state.selected_idx = indices[0]
    else:
        app.state.selected_idx = None


# ---------------------------------------------------------------------------
# _parse_scroll_text
# ---------------------------------------------------------------------------


class TestParseScrollText:
    def test_basic(self):
        assert _parse_scroll_text("3/10") == (2, 10)

    def test_none_input(self):
        assert _parse_scroll_text(None) is None

    def test_empty(self):
        assert _parse_scroll_text("") is None

    def test_no_slash(self):
        assert _parse_scroll_text("42") is None

    def test_non_numeric(self):
        assert _parse_scroll_text("abc/def") is None

    def test_zero_total(self):
        assert _parse_scroll_text("1/0") is None

    def test_clamp_high(self):
        # active > total → clamped to total
        assert _parse_scroll_text("20/5") == (4, 5)

    def test_clamp_low(self):
        # active < 1 → clamped to 0 (1-based to 0-based)
        assert _parse_scroll_text("0/5") == (0, 5)

    def test_whitespace(self):
        assert _parse_scroll_text(" 2 / 8 ") == (1, 8)


# ---------------------------------------------------------------------------
# _listmodel_clamp
# ---------------------------------------------------------------------------


class TestListmodelClamp:
    def test_basic(self):
        m = _SimListModel(count=10, active=3, offset=0)
        _listmodel_clamp(m, 4)
        assert m.active == 3
        assert m.offset == 0

    def test_active_past_end(self):
        m = _SimListModel(count=5, active=10, offset=0)
        _listmodel_clamp(m, 3)
        assert m.active == 4

    def test_offset_scrolls_to_active(self):
        m = _SimListModel(count=10, active=8, offset=0)
        _listmodel_clamp(m, 3)
        assert m.offset == 6  # active 8 visible at slot 2

    def test_offset_clamp_max(self):
        m = _SimListModel(count=10, active=0, offset=99)
        _listmodel_clamp(m, 4)
        assert m.offset == 0  # active=0, so offset clamps to 0

    def test_zero_count(self):
        m = _SimListModel(count=0, active=5, offset=5)
        _listmodel_clamp(m, 4)
        assert m.active == 0
        assert m.offset == 0

    def test_zero_visible(self):
        m = _SimListModel(count=10, active=3, offset=0)
        _listmodel_clamp(m, 0)
        assert m.active == 0
        assert m.offset == 0


# ---------------------------------------------------------------------------
# _listmodel_move_active
# ---------------------------------------------------------------------------


class TestListmodelMoveActive:
    def test_move_down(self):
        m = _SimListModel(count=10, active=2, offset=0)
        assert _listmodel_move_active(m, 1, 4)
        assert m.active == 3

    def test_move_up(self):
        m = _SimListModel(count=10, active=3, offset=0)
        assert _listmodel_move_active(m, -1, 4)
        assert m.active == 2

    def test_no_move_at_boundary(self):
        m = _SimListModel(count=3, active=2, offset=0)
        assert not _listmodel_move_active(m, 1, 3)

    def test_zero_delta(self):
        m = _SimListModel(count=5, active=2, offset=0)
        assert not _listmodel_move_active(m, 0, 3)

    def test_empty_model(self):
        m = _SimListModel(count=0, active=0, offset=0)
        assert not _listmodel_move_active(m, 1, 3)


# ---------------------------------------------------------------------------
# _listmodel_item_text
# ---------------------------------------------------------------------------


class TestListmodelItemText:
    def test_seed_labels(self):
        m = _SimListModel(count=3, seed_labels=["A", "B", "C"], seed_values=["1", "2", "3"])
        assert _listmodel_item_text(m, 0) == ("A", "1")
        assert _listmodel_item_text(m, 2) == ("C", "3")

    def test_fallback_label(self):
        m = _SimListModel(count=5, seed_labels=["X"], seed_values=[])
        label, value = _listmodel_item_text(m, 3)
        assert label == "Item 4"
        assert value == ""

    def test_out_of_range(self):
        m = _SimListModel(count=3, seed_labels=["A"])
        assert _listmodel_item_text(m, -1) == ("", "")
        assert _listmodel_item_text(m, 5) == ("", "")


# ---------------------------------------------------------------------------
# _find_by_widget_id / _count_item_slots
# ---------------------------------------------------------------------------


class TestFindByWidgetId:
    def test_found(self):
        w1 = _w(_widget_id="root.item0")
        w2 = _w(_widget_id="root.item1")
        sc = _scene([w1, w2])
        assert _find_by_widget_id(sc, "root.item0") == 0
        assert _find_by_widget_id(sc, "root.item1") == 1

    def test_not_found(self):
        sc = _scene([_w(_widget_id="abc")])
        assert _find_by_widget_id(sc, "xyz") is None

    def test_empty_scene(self):
        sc = _scene([])
        assert _find_by_widget_id(sc, "anything") is None


class TestCountItemSlots:
    def test_basic(self):
        widgets = [
            _w(_widget_id="menu.item0"),
            _w(_widget_id="menu.item1"),
            _w(_widget_id="menu.item2"),
        ]
        sc = _scene(widgets)
        assert _count_item_slots(sc, "menu") == 3

    def test_gap_stops(self):
        widgets = [
            _w(_widget_id="list.item0"),
            _w(_widget_id="list.item2"),  # item1 missing → stops at 1
        ]
        sc = _scene(widgets)
        assert _count_item_slots(sc, "list") == 1

    def test_no_items(self):
        sc = _scene([_w(_widget_id="other")])
        assert _count_item_slots(sc, "menu") == 0


# ---------------------------------------------------------------------------
# is_widget_focusable / focusable_indices
# ---------------------------------------------------------------------------


class TestIsWidgetFocusable:
    def test_button(self):
        assert is_widget_focusable(_w("button"))

    def test_checkbox(self):
        assert is_widget_focusable(_w("checkbox"))

    def test_slider(self):
        assert is_widget_focusable(_w("slider"))

    def test_radiobutton(self):
        assert is_widget_focusable(_w("radiobutton"))

    def test_textbox(self):
        assert is_widget_focusable(_w("textbox"))

    def test_label_not_focusable(self):
        assert not is_widget_focusable(_w("label"))

    def test_box_not_focusable(self):
        assert not is_widget_focusable(_w("box"))

    def test_invisible(self):
        assert not is_widget_focusable(_w("button", visible=False))

    def test_disabled(self):
        assert not is_widget_focusable(_w("button", enabled=False))


class TestFocusableIndices:
    def test_basic(self):
        widgets = [_w("label"), _w("button", y=10), _w("checkbox", y=20)]
        sc = _scene(widgets)
        assert focusable_indices(sc) == [1, 2]

    def test_sorted_by_y_then_x(self):
        widgets = [
            _w("button", x=50, y=20),
            _w("button", x=10, y=10),
            _w("button", x=30, y=10),
        ]
        sc = _scene(widgets)
        # y=10 first (x=10 before x=30), then y=20
        assert focusable_indices(sc) == [1, 2, 0]

    def test_empty(self):
        sc = _scene([_w("label")])
        assert focusable_indices(sc) == []


# ---------------------------------------------------------------------------
# set_focus / ensure_focus / focus_cycle
# ---------------------------------------------------------------------------


class TestSetFocus:
    def test_basic(self):
        app = _app([_w("label"), _w("button"), _w("button")])
        set_focus(app, 1)
        assert app.focus_idx == 1
        assert app.focus_edit_value is False

    def test_none(self):
        app = _app([_w("button")])
        set_focus(app, None)
        assert app.focus_idx is None

    def test_out_of_range(self):
        app = _app([_w("button")])
        set_focus(app, 99)
        assert app.focus_idx is None

    def test_unfocusable_ignored(self):
        app = _app([_w("label")])
        app.focus_idx = None
        set_focus(app, 0)
        assert app.focus_idx is None

    def test_sync_selection(self):
        app = _app([_w("button"), _w("button")])
        set_focus(app, 1, sync_selection=True)
        assert 1 in app.state.selected


class TestEnsureFocus:
    def test_already_focused(self):
        app = _app([_w("button"), _w("button")])
        set_focus(app, 0)
        ensure_focus(app)
        assert app.focus_idx == 0

    def test_from_none(self):
        app = _app([_w("label"), _w("button", y=10)])
        app.focus_idx = None
        ensure_focus(app)
        assert app.focus_idx == 1

    def test_no_focusables(self):
        app = _app([_w("label")])
        app.focus_idx = None
        ensure_focus(app)
        assert app.focus_idx is None


class TestFocusCycle:
    def test_cycle_forward(self):
        app = _app([_w("button", y=0), _w("button", y=10), _w("button", y=20)])
        set_focus(app, 0)
        focus_cycle(app, 1)
        assert app.focus_idx == 1

    def test_cycle_backward(self):
        app = _app([_w("button", y=0), _w("button", y=10), _w("button", y=20)])
        set_focus(app, 1)
        focus_cycle(app, -1)
        assert app.focus_idx == 0

    def test_wrap_forward(self):
        app = _app([_w("button", y=0), _w("button", y=10)])
        set_focus(app, 1)
        focus_cycle(app, 1)
        assert app.focus_idx == 0

    def test_wrap_backward(self):
        app = _app([_w("button", y=0), _w("button", y=10)])
        set_focus(app, 0)
        focus_cycle(app, -1)
        assert app.focus_idx == 1

    def test_no_focusables(self):
        app = _app([_w("label")])
        app.focus_idx = 99
        focus_cycle(app, 1)
        assert app.focus_idx is None


# ---------------------------------------------------------------------------
# focus_move_direction
# ---------------------------------------------------------------------------


class TestFocusMoveDirection:
    def test_move_down(self):
        app = _app([
            _w("button", x=10, y=10, width=20, height=10),
            _w("button", x=10, y=30, width=20, height=10),
        ])
        set_focus(app, 0)
        focus_move_direction(app, "down")
        assert app.focus_idx == 1

    def test_move_up(self):
        app = _app([
            _w("button", x=10, y=10, width=20, height=10),
            _w("button", x=10, y=30, width=20, height=10),
        ])
        set_focus(app, 1)
        focus_move_direction(app, "up")
        assert app.focus_idx == 0

    def test_move_right(self):
        app = _app([
            _w("button", x=10, y=10, width=20, height=10),
            _w("button", x=50, y=10, width=20, height=10),
        ])
        set_focus(app, 0)
        focus_move_direction(app, "right")
        assert app.focus_idx == 1

    def test_move_left(self):
        app = _app([
            _w("button", x=10, y=10, width=20, height=10),
            _w("button", x=50, y=10, width=20, height=10),
        ])
        set_focus(app, 1)
        focus_move_direction(app, "left")
        assert app.focus_idx == 0

    def test_no_candidate_wraps(self):
        # Only one focusable → wraps via focus_cycle
        app = _app([_w("button", x=10, y=10, width=20, height=10)])
        set_focus(app, 0)
        focus_move_direction(app, "down")
        assert app.focus_idx == 0  # still 0 (wrapped)


# ---------------------------------------------------------------------------
# adjust_focused_value
# ---------------------------------------------------------------------------


class TestAdjustFocusedValue:
    def test_slider_increment(self):
        app = _app([_w("slider", value=50, min_value=0, max_value=100)])
        set_focus(app, 0)
        adjust_focused_value(app, 5)
        assert app.state.current_scene().widgets[0].value == 55

    def test_slider_clamp_max(self):
        app = _app([_w("slider", value=98, min_value=0, max_value=100)])
        set_focus(app, 0)
        adjust_focused_value(app, 10)
        assert app.state.current_scene().widgets[0].value == 100

    def test_slider_clamp_min(self):
        app = _app([_w("slider", value=2, min_value=0, max_value=100)])
        set_focus(app, 0)
        adjust_focused_value(app, -10)
        assert app.state.current_scene().widgets[0].value == 0

    def test_non_slider_noop(self):
        app = _app([_w("button", value=50)])
        set_focus(app, 0)
        adjust_focused_value(app, 5)
        assert app.state.current_scene().widgets[0].value == 50

    def test_no_focusables(self):
        # Only non-focusable widgets → ensure_focus leaves focus_idx None
        app = _app([_w("label", value=50)])
        app.focus_idx = None
        adjust_focused_value(app, 5)
        assert app.focus_idx is None


# ---------------------------------------------------------------------------
# activate_focused
# ---------------------------------------------------------------------------


class TestActivateFocused:
    def test_checkbox_toggle(self):
        app = _app([_w("checkbox", checked=False)])
        set_focus(app, 0)
        activate_focused(app)
        assert app.state.current_scene().widgets[0].checked is True
        activate_focused(app)
        assert app.state.current_scene().widgets[0].checked is False

    def test_slider_edit_toggle(self):
        app = _app([_w("slider")])
        set_focus(app, 0)
        assert app.focus_edit_value is False
        activate_focused(app)
        assert app.focus_edit_value is True
        activate_focused(app)
        assert app.focus_edit_value is False

    def test_button_press(self):
        app = _app([_w("button", text="OK")])
        set_focus(app, 0)
        activate_focused(app)
        # Just verifies no crash + status set
        app._set_status.assert_called()

    def test_no_focus(self):
        app = _app([_w("button")])
        app.focus_idx = None
        activate_focused(app)  # no crash


# ---------------------------------------------------------------------------
# sim_runtime_reset / sim_runtime_restore
# ---------------------------------------------------------------------------


class TestSimRuntimeReset:
    def test_reset_clears(self):
        app = _app([_w("button")])
        app._sim_listmodels = {"x": 1}
        app._sim_runtime_snapshot = {"y": 2}
        sim_runtime_reset(app)
        assert app._sim_listmodels == {}
        assert app._sim_runtime_snapshot == {}


class TestSimRuntimeRestore:
    def test_restore_empty(self):
        app = _app([_w("button")])
        sim_runtime_restore(app)
        assert app._sim_listmodels == {}
        assert app._sim_runtime_snapshot == {}

    def test_restore_with_snapshot(self):
        w = _w("button", text="original", value=0)
        app = _app([w])
        sc = app.state.current_scene()
        sc.widgets[0]._widget_id = "btn1"
        sc.widgets[0].text = "modified"

        snap = _SimWidgetSnapshot(text="original", value=0, enabled=True, visible=True)
        app._sim_runtime_snapshot = {"btn1": snap}
        app._sim_listmodels = {}
        sim_runtime_restore(app)
        assert sc.widgets[0].text == "original"


# ---------------------------------------------------------------------------
# _sim_snapshot_widget
# ---------------------------------------------------------------------------


class TestSimSnapshotWidget:
    def test_basic(self):
        app = _app([])
        app._sim_runtime_snapshot = None
        w = _w("button", text="Hello", value=42)
        w._widget_id = "btn1"
        _sim_snapshot_widget(app, w)
        assert "btn1" in app._sim_runtime_snapshot
        s = app._sim_runtime_snapshot["btn1"]
        assert s.text == "Hello"
        assert s.value == 42

    def test_no_widget_id(self):
        app = _app([])
        app._sim_runtime_snapshot = {}
        w = _w("button")
        w._widget_id = None
        _sim_snapshot_widget(app, w)
        assert app._sim_runtime_snapshot == {}

    def test_already_snapped(self):
        app = _app([])
        snap = _SimWidgetSnapshot(text="old", value=0, enabled=True, visible=True)
        app._sim_runtime_snapshot = {"btn1": snap}
        w = _w("button", text="new")
        w._widget_id = "btn1"
        _sim_snapshot_widget(app, w)
        # Should keep old snap, not overwrite
        assert app._sim_runtime_snapshot["btn1"].text == "old"


# ---------------------------------------------------------------------------
# Extended edge-case coverage
# ---------------------------------------------------------------------------


class TestParseScrollTextExtended:
    def test_clamped_above_max(self):
        result = _parse_scroll_text("10/5")
        assert result == (4, 5)  # clamped: a = min(10,5) - 1 = 4

    def test_negative_count(self):
        assert _parse_scroll_text("1/-3") is None

    def test_zero_count(self):
        assert _parse_scroll_text("1/0") is None

    def test_whitespace_around(self):
        result = _parse_scroll_text("  3 / 10 ")
        assert result == (2, 10)

    def test_non_numeric_left(self):
        assert _parse_scroll_text("abc/10") is None


class TestListmodelClampExtended:
    def test_zero_count_resets(self):
        m = _SimListModel(count=0, active=5, offset=3)
        _listmodel_clamp(m, 4)
        assert m.active == 0
        assert m.offset == 0

    def test_zero_visible_slots(self):
        m = _SimListModel(count=10, active=5, offset=0)
        _listmodel_clamp(m, 0)
        assert m.active == 0
        assert m.offset == 0

    def test_active_beyond_end(self):
        m = _SimListModel(count=5, active=99, offset=0)
        _listmodel_clamp(m, 3)
        assert m.active == 4
        assert m.offset <= 2  # count - visible = 2

    def test_offset_follows_active_up(self):
        m = _SimListModel(count=10, active=0, offset=5)
        _listmodel_clamp(m, 3)
        assert m.offset == 0  # active < offset → offset = active


class TestListmodelMoveActiveExtended:
    def test_zero_count_returns_false(self):
        m = _SimListModel(count=0, active=0, offset=0)
        assert _listmodel_move_active(m, 1, 3) is False

    def test_zero_delta_returns_false(self):
        m = _SimListModel(count=5, active=2, offset=0)
        assert _listmodel_move_active(m, 0, 3) is False

    def test_clamp_at_bottom(self):
        m = _SimListModel(count=5, active=4, offset=2)
        moved = _listmodel_move_active(m, 1, 3)
        assert m.active == 4  # already at end
        assert moved is False


class TestListmodelItemTextExtended:
    def test_negative_index(self):
        m = _SimListModel(count=3, seed_labels=["A", "B", "C"])
        assert _listmodel_item_text(m, -1) == ("", "")

    def test_beyond_count(self):
        m = _SimListModel(count=3, seed_labels=["A", "B", "C"])
        assert _listmodel_item_text(m, 5) == ("", "")

    def test_with_values(self):
        m = _SimListModel(count=2, seed_labels=["X", "Y"], seed_values=["1", "2"], has_value_cols=True)
        label, value = _listmodel_item_text(m, 0)
        assert label == "X"
        assert value == "1"

    def test_fallback_label(self):
        m = _SimListModel(count=3, seed_labels=[])
        label, value = _listmodel_item_text(m, 0)
        assert label == "Item 1"
        assert value == ""


class TestIsWidgetFocusableExtended:
    def test_label_not_focusable(self):
        w = _w("label")
        assert is_widget_focusable(w) is False

    def test_box_not_focusable(self):
        w = _w("box")
        assert is_widget_focusable(w) is False

    def test_panel_not_focusable(self):
        w = _w("panel")
        assert is_widget_focusable(w) is False

    def test_gauge_not_focusable(self):
        w = _w("gauge")
        assert is_widget_focusable(w) is False

    def test_disabled_button(self):
        w = _w("button", enabled=False)
        assert is_widget_focusable(w) is False

    def test_hidden_slider(self):
        w = _w("slider", visible=False)
        assert is_widget_focusable(w) is False


class TestFocusableIndicesExtended:
    def test_empty_scene(self):
        sc = _scene([])
        assert focusable_indices(sc) == []

    def test_mixed_types(self):
        ws = [
            _w("label"),      # not focusable
            _w("button"),     # focusable
            _w("box"),        # not focusable
            _w("slider"),     # focusable
            _w("checkbox"),   # focusable
        ]
        sc = _scene(ws)
        result = focusable_indices(sc)
        assert 1 in result
        assert 3 in result
        assert 4 in result
        assert 0 not in result
        assert 2 not in result

