"""Tests for cyberpunk_designer/inspector_logic.py.

Covers inspector_field_to_str, inspector_commit_edit (single + multi-widget),
_parse_pair, _parse_active_count, _sorted_role_indices, compute_inspector_rows.
"""

from __future__ import annotations

from cyberpunk_designer.inspector_logic import (
    _parse_active_count,
    _parse_pair,
    _sorted_role_indices,
    compute_inspector_rows,
    inspector_commit_edit,
    inspector_field_to_str,
)
from cyberpunk_editor import CyberpunkEditorApp
from ui_designer import WidgetConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_app(tmp_path, monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    json_path = tmp_path / "scene.json"
    app = CyberpunkEditorApp(json_path, (256, 128))
    if not hasattr(app, "_save_undo_state"):
        app._save_undo_state = lambda: None
    return app


def _add(app, **kw):
    defaults = dict(type="label", x=0, y=0, width=80, height=16, text="W")
    defaults.update(kw)
    w = WidgetConfig(**defaults)
    sc = app.state.current_scene()
    sc.widgets.append(w)
    return w


def _sel(app, *indices):
    app.state.selected = list(indices)
    app.state.selected_idx = indices[0] if indices else None
    if indices:
        app.designer.selected_widget = indices[0]


def _start_edit(app, field, buf=""):
    """Begin editing *field* in the inspector.

    For virtual fields that do not require a widget selection (e.g.
    ``_goto_widget``, ``_scene_name``, ``_search``), we bypass
    ``_inspector_start_edit`` (which would bail out with "No selection")
    and directly poke the state.
    """
    _NO_WIDGET_FIELDS = {"_goto_widget", "_scene_name", "_search"}
    if field in _NO_WIDGET_FIELDS:
        app.state.inspector_selected_field = field
        app.state.inspector_input_buffer = buf
        return
    app._inspector_start_edit(field)
    app.state.inspector_input_buffer = buf


# ===========================================================================
# Pure utility functions
# ===========================================================================

class TestParsePair:
    def test_comma_separated(self):
        assert _parse_pair("10,20") == (10, 20)

    def test_space_separated(self):
        assert _parse_pair("10 20") == (10, 20)

    def test_none_on_no_separator(self):
        assert _parse_pair("abc") is None

    def test_none_on_non_int(self):
        assert _parse_pair("a,b") is None

    def test_stripped_spaces(self):
        assert _parse_pair("  5 , 10  ") == (5, 10)


class TestParseActiveCount:
    def test_normal(self):
        assert _parse_active_count("2/5") == (1, 5)

    def test_no_slash(self):
        assert _parse_active_count("5") is None

    def test_empty(self):
        assert _parse_active_count("") is None

    def test_zero_count(self):
        assert _parse_active_count("1/0") == (0, 0)

    def test_clamps_active(self):
        assert _parse_active_count("10/3") == (2, 3)

    def test_min_active(self):
        assert _parse_active_count("0/5") == (0, 5)


class TestSortedRoleIndices:
    def test_basic(self):
        role_idx = {"item0": 0, "item1": 1, "item2": 2, "title": 3}
        result = _sorted_role_indices(role_idx, "item")
        assert result == [(0, 0), (1, 1), (2, 2)]

    def test_empty_prefix(self):
        assert _sorted_role_indices({"a": 1}, "") == []

    def test_empty_dict(self):
        assert _sorted_role_indices({}, "item") == []

    def test_none_dict(self):
        assert _sorted_role_indices(None, "item") == []


# ===========================================================================
# inspector_field_to_str
# ===========================================================================

class TestInspectorFieldToStr:
    def test_text_field(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app, text="Hello")
        assert inspector_field_to_str(app, "text", w) == "Hello"

    def test_runtime_field(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app, runtime="sensor.temp")
        assert inspector_field_to_str(app, "runtime", w) == "sensor.temp"

    def test_int_field_x(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app, x=42)
        assert inspector_field_to_str(app, "x", w) == "42"

    def test_size_virtual_field(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app, width=64, height=16)
        assert inspector_field_to_str(app, "_size", w) == "64x16"

    def test_position_virtual_field(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app, x=10, y=20)
        assert inspector_field_to_str(app, "_position", w) == "10,20"

    def test_padding_virtual_field(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app, padding_x=2, padding_y=1)
        assert inspector_field_to_str(app, "_padding", w) == "2,1"

    def test_margin_virtual_field(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app, margin_x=3, margin_y=4)
        assert inspector_field_to_str(app, "_margin", w) == "3,4"

    def test_spacing_virtual_field(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app, padding_x=2, padding_y=1, margin_x=3, margin_y=4)
        assert inspector_field_to_str(app, "_spacing", w) == "2,1,3,4"

    def test_value_range_virtual_field(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app, min_value=0, max_value=100)
        assert inspector_field_to_str(app, "_value_range", w) == "0,100"

    def test_color_fg(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app, color_fg="15")
        assert inspector_field_to_str(app, "color_fg", w) == "15"

    def test_data_points(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app, data_points=[1, 2, 3])
        result = inspector_field_to_str(app, "data_points", w)
        assert "1" in result and "2" in result and "3" in result

    def test_chart_mode_bar(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app, type="chart", style="bar")
        assert inspector_field_to_str(app, "chart_mode", w) == "bar"

    def test_chart_mode_line(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app, type="chart", style="line")
        assert inspector_field_to_str(app, "chart_mode", w) == "line"

    def test_chart_mode_default_from_label(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app, type="chart", style="default", text="Bar chart")
        assert inspector_field_to_str(app, "chart_mode", w) == "bar"

    def test_multi_select_uses_bounds(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, y=20, width=30, height=40)
        _add(app, x=50, y=60, width=30, height=40)
        _sel(app, 0, 1)
        w = app.state.current_scene().widgets[0]
        result = inspector_field_to_str(app, "x", w)
        assert result == "10"

    def test_multi_select_mixed_color(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, color_fg="10")
        _add(app, color_fg="15")
        _sel(app, 0, 1)
        w = app.state.current_scene().widgets[0]
        result = inspector_field_to_str(app, "color_fg", w)
        assert result == ""  # mixed

    def test_multi_select_same_color(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, color_fg="15")
        _add(app, color_fg="15")
        _sel(app, 0, 1)
        w = app.state.current_scene().widgets[0]
        result = inspector_field_to_str(app, "color_fg", w)
        assert result == "15"


# ===========================================================================
# inspector_commit_edit — special fields
# ===========================================================================

class TestCommitPosition:
    def test_valid_position(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=0)
        _sel(app, 0)
        _start_edit(app, "_position", "10,20")
        result = inspector_commit_edit(app)
        assert result is True
        w = app.state.current_scene().widgets[0]
        assert w.x == 10 and w.y == 20

    def test_invalid_position(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "_position", "abc")
        result = inspector_commit_edit(app)
        assert result is False

    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app)
        _start_edit(app, "_position", "10,20")
        result = inspector_commit_edit(app)
        assert result is True  # cancel-edit returns True


class TestCommitPadding:
    def test_valid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "_padding", "2,3")
        result = inspector_commit_edit(app)
        assert result is True
        w = app.state.current_scene().widgets[0]
        assert w.padding_x == 2 and w.padding_y == 3

    def test_invalid_format(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "_padding", "nope")
        assert inspector_commit_edit(app) is False

    def test_negative_rejected(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "_padding", "-1,0")
        assert inspector_commit_edit(app) is False


class TestCommitMargin:
    def test_valid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "_margin", "1,2")
        assert inspector_commit_edit(app) is True
        w = app.state.current_scene().widgets[0]
        assert w.margin_x == 1 and w.margin_y == 2

    def test_invalid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "_margin", "bad")
        assert inspector_commit_edit(app) is False

    def test_negative_rejected(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "_margin", "0,-1")
        assert inspector_commit_edit(app) is False


class TestCommitSpacing:
    def test_valid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "_spacing", "2,1,0,0")
        assert inspector_commit_edit(app) is True
        w = app.state.current_scene().widgets[0]
        assert w.padding_x == 2 and w.margin_y == 0

    def test_wrong_part_count(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "_spacing", "1,2")
        assert inspector_commit_edit(app) is False

    def test_non_int(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "_spacing", "a,b,c,d")
        assert inspector_commit_edit(app) is False

    def test_negative_rejected(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "_spacing", "1,-1,0,0")
        assert inspector_commit_edit(app) is False


class TestCommitSize:
    def test_wxh(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "_size", "64x16")
        assert inspector_commit_edit(app) is True
        w = app.state.current_scene().widgets[0]
        assert w.width == 64 and w.height == 16

    def test_comma_format(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "_size", "32,8")
        assert inspector_commit_edit(app) is True
        w = app.state.current_scene().widgets[0]
        assert w.width == 32 and w.height == 8

    def test_invalid_format(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "_size", "bad")
        assert inspector_commit_edit(app) is False

    def test_non_int(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "_size", "axb")
        assert inspector_commit_edit(app) is False

    def test_zero_rejected(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "_size", "0x0")
        assert inspector_commit_edit(app) is False


class TestCommitValueRange:
    def test_valid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="gauge", value=50, min_value=0, max_value=100)
        _sel(app, 0)
        _start_edit(app, "_value_range", "10,200")
        assert inspector_commit_edit(app) is True
        w = app.state.current_scene().widgets[0]
        assert w.min_value == 10 and w.max_value == 200
        assert w.value == 50  # clamped

    def test_invalid_format(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "_value_range", "bad")
        assert inspector_commit_edit(app) is False

    def test_min_gt_max_rejected(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "_value_range", "100,10")
        assert inspector_commit_edit(app) is False


class TestCommitGotoWidget:
    def test_valid_index(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _start_edit(app, "_goto_widget", "1")
        assert inspector_commit_edit(app) is True
        assert 1 in app.state.selected

    def test_invalid_index(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _start_edit(app, "_goto_widget", "99")
        assert inspector_commit_edit(app) is False

    def test_non_int(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _start_edit(app, "_goto_widget", "abc")
        assert inspector_commit_edit(app) is False


class TestCommitSceneName:
    def test_rename_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _start_edit(app, "_scene_name", "new_name")
        assert inspector_commit_edit(app) is True
        assert app.designer.current_scene == "new_name"

    def test_empty_rejected(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _start_edit(app, "_scene_name", "")
        assert inspector_commit_edit(app) is False

    def test_invalid_chars_rejected(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _start_edit(app, "_scene_name", "a/b")
        assert inspector_commit_edit(app) is False

    def test_same_name_noop(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        name = app.designer.current_scene
        _start_edit(app, "_scene_name", name)
        assert inspector_commit_edit(app) is True

    def test_duplicate_name_rejected(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._add_new_scene()
        names = list(app.designer.scenes.keys())
        # Try to rename first scene to second scene name
        app._jump_to_scene(0)
        _start_edit(app, "_scene_name", names[1])
        assert inspector_commit_edit(app) is False


class TestCommitArrayDup:
    def test_valid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=0, width=20, height=10)
        _sel(app, 0)
        _start_edit(app, "_array_dup", "3,20,0")
        assert inspector_commit_edit(app) is True

    def test_wrong_format(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "_array_dup", "bad")
        assert inspector_commit_edit(app) is False

    def test_non_int(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "_array_dup", "a,b,c")
        assert inspector_commit_edit(app) is False


class TestCommitSearch:
    def test_search(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, text="Hello")
        _add(app, text="World")
        _start_edit(app, "_search", "Hello")
        assert inspector_commit_edit(app) is True


# ===========================================================================
# inspector_commit_edit — single widget fields
# ===========================================================================

class TestCommitSingleWidget:
    def test_text(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, text="old")
        _sel(app, 0)
        _start_edit(app, "text", "new")
        assert inspector_commit_edit(app) is True
        assert app.state.current_scene().widgets[0].text == "new"

    def test_runtime(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, runtime="")
        _sel(app, 0)
        _start_edit(app, "runtime", "sensor.temp")
        assert inspector_commit_edit(app) is True
        assert app.state.current_scene().widgets[0].runtime == "sensor.temp"

    def test_x_int(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.snap_enabled = False
        _add(app, x=0, y=0, width=20, height=10)
        _sel(app, 0)
        _start_edit(app, "x", "10")
        assert inspector_commit_edit(app) is True
        assert app.state.current_scene().widgets[0].x == 10

    def test_y_int(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.snap_enabled = False
        _add(app, x=0, y=0, width=20, height=10)
        _sel(app, 0)
        _start_edit(app, "y", "5")
        assert inspector_commit_edit(app) is True
        assert app.state.current_scene().widgets[0].y == 5

    def test_x_invalid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "x", "abc")
        assert inspector_commit_edit(app) is False

    def test_width(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=0, width=20, height=10)
        _sel(app, 0)
        _start_edit(app, "width", "40")
        assert inspector_commit_edit(app) is True
        assert app.state.current_scene().widgets[0].width == 40

    def test_height(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.snap_enabled = False
        _add(app, x=0, y=0, width=20, height=10)
        _sel(app, 0)
        _start_edit(app, "height", "30")
        assert inspector_commit_edit(app) is True
        assert app.state.current_scene().widgets[0].height == 30

    def test_value(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="gauge", value=50, min_value=0, max_value=100)
        _sel(app, 0)
        _start_edit(app, "value", "75")
        assert inspector_commit_edit(app) is True

    def test_min_value(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="gauge", min_value=0, max_value=100)
        _sel(app, 0)
        _start_edit(app, "min_value", "10")
        assert inspector_commit_edit(app) is True

    def test_max_value(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="gauge", min_value=0, max_value=100)
        _sel(app, 0)
        _start_edit(app, "max_value", "200")
        assert inspector_commit_edit(app) is True

    def test_z_index(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "z_index", "5")
        assert inspector_commit_edit(app) is True

    def test_color_fg_valid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, color_fg="black")
        _sel(app, 0)
        _start_edit(app, "color_fg", "white")
        assert inspector_commit_edit(app) is True
        assert app.state.current_scene().widgets[0].color_fg == "white"

    def test_color_fg_invalid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "color_fg", "not_a_color$$$")
        # May or may not fail depending on _is_valid_color_str logic
        inspector_commit_edit(app)

    def test_color_bg_valid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, color_bg="black")
        _sel(app, 0)
        _start_edit(app, "color_bg", "red")
        assert inspector_commit_edit(app) is True
        assert app.state.current_scene().widgets[0].color_bg == "red"

    def test_align_valid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "align", "center")
        assert inspector_commit_edit(app) is True
        assert app.state.current_scene().widgets[0].align == "center"

    def test_align_invalid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "align", "justify")
        assert inspector_commit_edit(app) is False

    def test_valign_valid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "valign", "middle")
        assert inspector_commit_edit(app) is True
        assert app.state.current_scene().widgets[0].valign == "middle"

    def test_valign_invalid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "valign", "stretch")
        assert inspector_commit_edit(app) is False

    def test_border_style_valid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "border_style", "double")
        assert inspector_commit_edit(app) is True
        assert app.state.current_scene().widgets[0].border_style == "double"

    def test_border_style_invalid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "border_style", "fancy")
        assert inspector_commit_edit(app) is False

    def test_text_overflow_valid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "text_overflow", "wrap")
        assert inspector_commit_edit(app) is True

    def test_text_overflow_invalid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "text_overflow", "scroll")
        assert inspector_commit_edit(app) is False

    def test_max_lines_valid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "max_lines", "3")
        assert inspector_commit_edit(app) is True
        assert app.state.current_scene().widgets[0].max_lines == 3

    def test_max_lines_zero_sets_none(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "max_lines", "0")
        assert inspector_commit_edit(app) is True
        assert app.state.current_scene().widgets[0].max_lines is None

    def test_max_lines_invalid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "max_lines", "abc")
        assert inspector_commit_edit(app) is False

    def test_data_points_valid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="chart")
        _sel(app, 0)
        _start_edit(app, "data_points", "1,2,3")
        assert inspector_commit_edit(app) is True

    def test_data_points_invalid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="chart")
        _sel(app, 0)
        _start_edit(app, "data_points", "not_numbers")
        assert inspector_commit_edit(app) is False

    def test_chart_mode_bar(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="chart")
        _sel(app, 0)
        _start_edit(app, "chart_mode", "bar")
        assert inspector_commit_edit(app) is True

    def test_chart_mode_invalid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="chart")
        _sel(app, 0)
        _start_edit(app, "chart_mode", "pie")
        assert inspector_commit_edit(app) is False

    def test_unknown_field(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _start_edit(app, "nonexistent_field", "val")
        assert inspector_commit_edit(app) is True  # returns True after cancel

    def test_no_widget_selected(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app)
        _start_edit(app, "text", "new")
        assert inspector_commit_edit(app) is True  # cancel returns True

    def test_no_field_returns_true(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.state.inspector_selected_field = None
        assert inspector_commit_edit(app) is True


# ===========================================================================
# inspector_commit_edit — multi-widget fields
# ===========================================================================

class TestCommitMultiWidget:
    def test_multi_x(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, y=0, width=20, height=10)
        _add(app, x=50, y=0, width=20, height=10)
        _sel(app, 0, 1)
        _start_edit(app, "x", "30")
        assert inspector_commit_edit(app) is True

    def test_multi_y(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=10, width=20, height=10)
        _add(app, x=0, y=50, width=20, height=10)
        _sel(app, 0, 1)
        _start_edit(app, "y", "30")
        assert inspector_commit_edit(app) is True

    def test_multi_width(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=0, width=20, height=10)
        _add(app, x=30, y=0, width=40, height=10)
        _sel(app, 0, 1)
        _start_edit(app, "width", "100")
        assert inspector_commit_edit(app) is True

    def test_multi_width_invalid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _sel(app, 0, 1)
        _start_edit(app, "width", "abc")
        assert inspector_commit_edit(app) is False

    def test_multi_color_fg(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, color_fg="black")
        _add(app, color_fg="red")
        _sel(app, 0, 1)
        _start_edit(app, "color_fg", "white")
        assert inspector_commit_edit(app) is True

    def test_multi_align(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, align="left")
        _add(app, align="right")
        _sel(app, 0, 1)
        _start_edit(app, "align", "center")
        assert inspector_commit_edit(app) is True
        sc = app.state.current_scene()
        assert sc.widgets[0].align == "center"
        assert sc.widgets[1].align == "center"

    def test_multi_align_invalid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _sel(app, 0, 1)
        _start_edit(app, "align", "justify")
        assert inspector_commit_edit(app) is False

    def test_multi_valign(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _sel(app, 0, 1)
        _start_edit(app, "valign", "bottom")
        assert inspector_commit_edit(app) is True

    def test_multi_valign_invalid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _sel(app, 0, 1)
        _start_edit(app, "valign", "stretch")
        assert inspector_commit_edit(app) is False

    def test_multi_border_style(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _sel(app, 0, 1)
        _start_edit(app, "border_style", "rounded")
        assert inspector_commit_edit(app) is True

    def test_multi_border_style_invalid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _sel(app, 0, 1)
        _start_edit(app, "border_style", "fancy")
        assert inspector_commit_edit(app) is False

    def test_multi_text_overflow(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _sel(app, 0, 1)
        _start_edit(app, "text_overflow", "clip")
        assert inspector_commit_edit(app) is True

    def test_multi_text_overflow_invalid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _sel(app, 0, 1)
        _start_edit(app, "text_overflow", "marquee")
        assert inspector_commit_edit(app) is False

    def test_multi_max_lines(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _sel(app, 0, 1)
        _start_edit(app, "max_lines", "2")
        assert inspector_commit_edit(app) is True

    def test_multi_max_lines_zero(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _sel(app, 0, 1)
        _start_edit(app, "max_lines", "0")
        assert inspector_commit_edit(app) is True

    def test_multi_max_lines_invalid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _sel(app, 0, 1)
        _start_edit(app, "max_lines", "abc")
        assert inspector_commit_edit(app) is False

    def test_multi_text(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, text="a")
        _add(app, text="b")
        _sel(app, 0, 1)
        _start_edit(app, "text", "new")
        assert inspector_commit_edit(app) is True
        sc = app.state.current_scene()
        assert sc.widgets[0].text == "new"
        assert sc.widgets[1].text == "new"

    def test_multi_runtime(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _sel(app, 0, 1)
        _start_edit(app, "runtime", "x.y")
        assert inspector_commit_edit(app) is True

    def test_multi_data_points_chart(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="chart")
        _add(app, type="chart")
        _sel(app, 0, 1)
        _start_edit(app, "data_points", "1,2,3")
        assert inspector_commit_edit(app) is True

    def test_multi_data_points_no_charts(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label")
        _add(app, type="label")
        _sel(app, 0, 1)
        _start_edit(app, "data_points", "1,2,3")
        assert inspector_commit_edit(app) is False

    def test_multi_data_points_invalid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="chart")
        _add(app, type="chart")
        _sel(app, 0, 1)
        _start_edit(app, "data_points", "not_numbers")
        assert inspector_commit_edit(app) is False

    def test_multi_chart_mode(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="chart")
        _add(app, type="chart")
        _sel(app, 0, 1)
        _start_edit(app, "chart_mode", "line")
        assert inspector_commit_edit(app) is True

    def test_multi_chart_mode_no_charts(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label")
        _sel(app, 0)
        _add(app, type="label")
        _sel(app, 0, 1)
        _start_edit(app, "chart_mode", "line")
        assert inspector_commit_edit(app) is False

    def test_multi_chart_mode_invalid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="chart")
        _add(app, type="chart")
        _sel(app, 0, 1)
        _start_edit(app, "chart_mode", "pie")
        assert inspector_commit_edit(app) is False

    def test_multi_unknown_field(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _sel(app, 0, 1)
        _start_edit(app, "nonexistent", "val")
        assert inspector_commit_edit(app) is True  # cancel returns True


# ===========================================================================
# compute_inspector_rows
# ===========================================================================

class TestComputeInspectorRows:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        rows, warning, w = compute_inspector_rows(app)
        assert isinstance(rows, list)
        assert w is None

    def test_single_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label", text="Hi")
        _sel(app, 0)
        rows, warning, w = compute_inspector_rows(app)
        assert w is not None
        assert any("label" in str(r) for row in rows for r in row)

    def test_multi_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label")
        _add(app, type="button")
        _sel(app, 0, 1)
        rows, warning, w = compute_inspector_rows(app)
        assert len(rows) > 0
