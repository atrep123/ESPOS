"""Tests for inspector_commit_edit field branches.

Covers: _position, _padding, _margin, _spacing, _size, _value_range,
_goto_widget, _scene_name, _search, _array_dup, _template_name.
"""

from __future__ import annotations

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
    return CyberpunkEditorApp(json_path, (256, 128))


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


def _commit(app, field, buf):
    """Set up inspector field/buffer and call _inspector_commit_edit."""
    app.state.inspector_selected_field = field
    app.state.inspector_input_buffer = buf
    return app._inspector_commit_edit()


# ===================================================================
# _position field
# ===================================================================


class TestCommitPosition:
    def test_valid_xy(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app, x=0, y=0)
        _sel(app, 0)
        result = _commit(app, "_position", "10,20")
        assert result is True
        assert w.x == 10
        assert w.y == 20

    def test_space_separator(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app, x=0, y=0)
        _sel(app, 0)
        result = _commit(app, "_position", "30 40")
        assert result is True
        assert w.x == 30
        assert w.y == 40

    def test_invalid_format_returns_false(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        result = _commit(app, "_position", "just_one")
        assert result is False

    def test_non_integer_returns_false(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        result = _commit(app, "_position", "abc,def")
        assert result is False

    def test_no_selection_returns_true(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        result = _commit(app, "_position", "10,20")
        assert result is True

    def test_multiple_widgets(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w0 = _add(app)
        w1 = _add(app)
        _sel(app, 0, 1)
        _commit(app, "_position", "5,5")
        assert w0.x == 5 and w0.y == 5
        assert w1.x == 5 and w1.y == 5

    def test_clears_field_on_success(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        _commit(app, "_position", "1,2")
        assert app.state.inspector_selected_field is None
        assert app.state.inspector_input_buffer == ""


# ===================================================================
# _padding field
# ===================================================================


class TestCommitPadding:
    def test_valid_padding(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app)
        _sel(app, 0)
        result = _commit(app, "_padding", "3,2")
        assert result is True
        assert w.padding_x == 3
        assert w.padding_y == 2

    def test_invalid_format(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        assert _commit(app, "_padding", "just_one") is False

    def test_negative_rejected(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        assert _commit(app, "_padding", "-1,2") is False

    def test_non_integer(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        assert _commit(app, "_padding", "a,b") is False

    def test_space_separator(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app)
        _sel(app, 0)
        _commit(app, "_padding", "5 3")
        assert w.padding_x == 5
        assert w.padding_y == 3

    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert _commit(app, "_padding", "1,1") is True


# ===================================================================
# _margin field
# ===================================================================


class TestCommitMargin:
    def test_valid_margin(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app)
        _sel(app, 0)
        result = _commit(app, "_margin", "4,6")
        assert result is True
        assert w.margin_x == 4
        assert w.margin_y == 6

    def test_negative_rejected(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        assert _commit(app, "_margin", "2,-3") is False

    def test_invalid_format(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        assert _commit(app, "_margin", "single") is False

    def test_non_integer(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        assert _commit(app, "_margin", "x,y") is False


# ===================================================================
# _spacing field
# ===================================================================


class TestCommitSpacing:
    def test_valid_spacing(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app)
        _sel(app, 0)
        result = _commit(app, "_spacing", "2,1,3,4")
        assert result is True
        assert w.padding_x == 2
        assert w.padding_y == 1
        assert w.margin_x == 3
        assert w.margin_y == 4

    def test_wrong_count(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        assert _commit(app, "_spacing", "1,2") is False

    def test_negative_rejected(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        assert _commit(app, "_spacing", "1,2,-1,0") is False

    def test_non_integer(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        assert _commit(app, "_spacing", "a,b,c,d") is False

    def test_space_mixed_separators(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app)
        _sel(app, 0)
        result = _commit(app, "_spacing", "1 2 3 4")
        assert result is True
        assert w.padding_x == 1

    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert _commit(app, "_spacing", "1,2,3,4") is True


# ===================================================================
# _size field
# ===================================================================


class TestCommitSize:
    def test_valid_wxh(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app)
        _sel(app, 0)
        result = _commit(app, "_size", "64x16")
        assert result is True
        assert w.width == 64
        assert w.height == 16

    def test_comma_separator(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app)
        _sel(app, 0)
        _commit(app, "_size", "100,50")
        assert w.width == 100
        assert w.height == 50

    def test_uppercase_x(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app)
        _sel(app, 0)
        _commit(app, "_size", "32X24")
        assert w.width == 32
        assert w.height == 24

    def test_zero_rejected(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        assert _commit(app, "_size", "0x10") is False

    def test_negative_rejected(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        assert _commit(app, "_size", "-5x10") is False

    def test_invalid_format(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        assert _commit(app, "_size", "just_one") is False

    def test_non_integer(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        assert _commit(app, "_size", "axb") is False

    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert _commit(app, "_size", "10x10") is True


# ===================================================================
# _value_range field
# ===================================================================


class TestCommitValueRange:
    def test_valid_range(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app, type="slider")
        w.value = 50
        _sel(app, 0)
        result = _commit(app, "_value_range", "0,200")
        assert result is True
        assert w.min_value == 0
        assert w.max_value == 200
        assert w.value == 50  # within range, unchanged

    def test_clamps_value(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app, type="slider")
        w.value = 90
        w.min_value = 0
        w.max_value = 100
        _sel(app, 0)
        _commit(app, "_value_range", "0,50")
        assert w.value == 50  # clamped to new max

    def test_min_greater_than_max_rejected(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        assert _commit(app, "_value_range", "100,50") is False

    def test_invalid_format(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        assert _commit(app, "_value_range", "just_one") is False

    def test_non_integer(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        assert _commit(app, "_value_range", "a,b") is False

    def test_space_separator(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app)
        w.value = 10
        _sel(app, 0)
        _commit(app, "_value_range", "0 100")
        assert w.min_value == 0
        assert w.max_value == 100


# ===================================================================
# _goto_widget field
# ===================================================================


class TestCommitGotoWidget:
    def test_valid_index(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, text="target")
        result = _commit(app, "_goto_widget", "0")
        assert result is True
        assert 0 in app.state.selected

    def test_out_of_range(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        assert _commit(app, "_goto_widget", "99") is False

    def test_negative_index(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        assert _commit(app, "_goto_widget", "-1") is False

    def test_non_integer(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        assert _commit(app, "_goto_widget", "abc") is False

    def test_selects_correct_widget(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, text="first")
        _add(app, text="second")
        _commit(app, "_goto_widget", "1")
        assert app.state.selected_idx == 1

    def test_clears_field(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _commit(app, "_goto_widget", "0")
        assert app.state.inspector_selected_field is None


# ===================================================================
# _scene_name field
# ===================================================================


class TestCommitSceneName:
    def test_valid_rename(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        old_name = app.designer.current_scene
        result = _commit(app, "_scene_name", "new_name")
        assert result is True
        assert app.designer.current_scene == "new_name"
        assert old_name not in app.designer.scenes
        assert "new_name" in app.designer.scenes

    def test_empty_name_rejected(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert _commit(app, "_scene_name", "") is False

    def test_invalid_chars_rejected(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert _commit(app, "_scene_name", "bad/name") is False

    def test_duplicate_name_rejected(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        from ui_models import SceneConfig

        app.designer.scenes["other"] = SceneConfig(name="other", width=256, height=128, widgets=[])
        assert _commit(app, "_scene_name", "other") is False

    def test_same_name_is_noop(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        name = app.designer.current_scene
        result = _commit(app, "_scene_name", name)
        assert result is True
        assert app.designer.current_scene == name

    def test_transfers_dirty_state(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        old_name = app.designer.current_scene
        app._dirty_scenes = {old_name}
        _commit(app, "_scene_name", "renamed")
        assert "renamed" in app._dirty_scenes
        assert old_name not in app._dirty_scenes

    def test_name_with_spaces(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        result = _commit(app, "_scene_name", "my scene")
        assert result is True
        assert app.designer.current_scene == "my scene"

    def test_name_with_hyphens(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        result = _commit(app, "_scene_name", "my-scene")
        assert result is True
        assert app.designer.current_scene == "my-scene"


# ===================================================================
# _search field
# ===================================================================


class TestCommitSearch:
    def test_search_dispatches(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, text="findme")
        _add(app, text="other")
        result = _commit(app, "_search", "findme")
        assert result is True
        # Should clear field after search
        assert app.state.inspector_selected_field is None

    def test_search_empty_string(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        result = _commit(app, "_search", "")
        assert result is True


# ===================================================================
# _array_dup field
# ===================================================================


class TestCommitArrayDup:
    def test_valid_array_dup(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, y=10, width=20, height=10)
        _sel(app, 0)
        sc = app.state.current_scene()
        before = len(sc.widgets)
        result = _commit(app, "_array_dup", "3,16,0")
        assert result is True
        assert len(sc.widgets) > before

    def test_wrong_count_format(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        assert _commit(app, "_array_dup", "1,2") is False

    def test_non_integer(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        assert _commit(app, "_array_dup", "a,b,c") is False


# ===================================================================
# _template_name field
# ===================================================================


class TestCommitTemplateName:
    def test_empty_name_rejected(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert _commit(app, "_template_name", "") is False

    def test_no_pending_widgets(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._pending_template_widgets = None
        assert _commit(app, "_template_name", "MyTemplate") is False

    def test_saves_template(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._pending_template_widgets = [
            {"type": "label", "x": 0, "y": 0, "width": 80, "height": 16, "text": "T"},
        ]
        result = _commit(app, "_template_name", "TestTpl")
        assert result is True
        assert (
            "saved" in (app.dialog_message or "").lower()
            or "template" in (app.dialog_message or "").lower()
        )


# ===================================================================
# inspector_field_to_str
# ===================================================================


class TestInspectorFieldToStr:
    def test_position_field(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app, x=10, y=20)
        _sel(app, 0)
        from cyberpunk_designer.inspector_logic import inspector_field_to_str

        result = inspector_field_to_str(app, "_position", w)
        assert result == "10,20"

    def test_padding_field(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app)
        w.padding_x = 3
        w.padding_y = 2
        _sel(app, 0)
        from cyberpunk_designer.inspector_logic import inspector_field_to_str

        result = inspector_field_to_str(app, "_padding", w)
        assert result == "3,2"

    def test_margin_field(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app)
        w.margin_x = 5
        w.margin_y = 7
        _sel(app, 0)
        from cyberpunk_designer.inspector_logic import inspector_field_to_str

        result = inspector_field_to_str(app, "_margin", w)
        assert result == "5,7"

    def test_spacing_field(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app)
        w.padding_x = 1
        w.padding_y = 2
        w.margin_x = 3
        w.margin_y = 4
        _sel(app, 0)
        from cyberpunk_designer.inspector_logic import inspector_field_to_str

        result = inspector_field_to_str(app, "_spacing", w)
        assert result == "1,2,3,4"

    def test_value_range_field(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app)
        w.min_value = 10
        w.max_value = 90
        _sel(app, 0)
        from cyberpunk_designer.inspector_logic import inspector_field_to_str

        result = inspector_field_to_str(app, "_value_range", w)
        assert result == "10,90"

    def test_numeric_field(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app, x=42)
        _sel(app, 0)
        from cyberpunk_designer.inspector_logic import inspector_field_to_str

        result = inspector_field_to_str(app, "x", w)
        assert result == "42"

    def test_string_field(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app)
        w.color_fg = "#aabbcc"
        _sel(app, 0)
        from cyberpunk_designer.inspector_logic import inspector_field_to_str

        result = inspector_field_to_str(app, "color_fg", w)
        assert result == "#aabbcc"
