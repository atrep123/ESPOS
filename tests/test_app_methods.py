"""Tests for CyberpunkEditorApp private methods.

Covers: _is_valid_color_str, _apply_color_preset, _apply_color_preset_index,
_cycle_profile, _on_text_input, _inspector_cancel_edit, _toggle_overflow_warnings,
_intelligent_auto_arrange, _find_best_position, _component_info_from_group,
_format_group_label, _tri_state, _build_template_actions.
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


# ===================================================================
# _is_valid_color_str
# ===================================================================


class TestIsValidColorStr:
    def test_empty_string(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert app._is_valid_color_str("") is True

    def test_named_color(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert app._is_valid_color_str("red") is True
        assert app._is_valid_color_str("blue") is True
        assert app._is_valid_color_str("white") is True

    def test_hex_color(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert app._is_valid_color_str("#ff0000") is True
        assert app._is_valid_color_str("#000000") is True
        assert app._is_valid_color_str("#AABBCC") is True

    def test_0x_color(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert app._is_valid_color_str("0xff0000") is True
        assert app._is_valid_color_str("0x000000") is True

    def test_invalid_color(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert app._is_valid_color_str("not_a_color") is False
        assert app._is_valid_color_str("#xyz") is False
        assert app._is_valid_color_str("#12345") is False

    def test_case_insensitive(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert app._is_valid_color_str("RED") is True
        assert app._is_valid_color_str("Blue") is True


# ===================================================================
# _apply_color_preset / _apply_color_preset_index
# ===================================================================


class TestApplyColorPreset:
    def test_applies_fg_bg(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label")
        _sel(app, 0)
        app._apply_color_preset("#f5f5f5", "#000000")
        w = app.state.current_scene().widgets[0]
        assert w.color_fg == "#f5f5f5"
        assert w.color_bg == "#000000"

    def test_applies_to_multiple(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label")
        _add(app, type="button")
        _sel(app, 0, 1)
        app._apply_color_preset("white", "black")
        sc = app.state.current_scene()
        for w in sc.widgets:
            assert w.color_fg == "white"
            assert w.color_bg == "black"

    def test_no_selection_no_crash(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        app._apply_color_preset("white", "black")


class TestApplyColorPresetIndex:
    def test_index_0(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label")
        _sel(app, 0)
        app._apply_color_preset_index(0)
        w = app.state.current_scene().widgets[0]
        assert w.color_fg == "#f5f5f5"
        assert w.color_bg == "#000000"

    def test_index_4_inverted(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label")
        _sel(app, 0)
        app._apply_color_preset_index(4)
        w = app.state.current_scene().widgets[0]
        assert w.color_fg == "#000000"
        assert w.color_bg == "#f5f5f5"

    def test_out_of_range_no_crash(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label")
        _sel(app, 0)
        app._apply_color_preset_index(99)  # should not crash


# ===================================================================
# _cycle_profile
# ===================================================================


class TestCycleProfile:
    def test_cycles_from_default(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._set_profile("esp32os_256x128_gray4")
        before = app.hardware_profile
        app._cycle_profile()
        after = app.hardware_profile
        assert after != before

    def test_cycles_wraps_around(self, tmp_path, monkeypatch):
        from cyberpunk_designer.constants import PROFILE_ORDER

        app = _make_app(tmp_path, monkeypatch)
        # Set to last profile
        app._set_profile(PROFILE_ORDER[-1])
        app._cycle_profile()
        assert app.hardware_profile == PROFILE_ORDER[0]

    def test_unknown_profile_goes_to_first(self, tmp_path, monkeypatch):
        from cyberpunk_designer.constants import PROFILE_ORDER

        app = _make_app(tmp_path, monkeypatch)
        app.hardware_profile = "nonexistent_profile"
        app._cycle_profile()
        assert app.hardware_profile == PROFILE_ORDER[0]


# ===================================================================
# _on_text_input
# ===================================================================


class TestOnTextInput:
    def test_appends_to_buffer(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label", text="Hi")
        _sel(app, 0)
        app._inspector_start_edit("text")
        app.state.inspector_input_buffer = "ab"
        app._on_text_input("c")
        assert app.state.inspector_input_buffer == "abc"

    def test_no_field_ignores_input(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.state.inspector_selected_field = None
        app._on_text_input("x")  # should not crash

    def test_empty_text_ignored(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label")
        _sel(app, 0)
        app._inspector_start_edit("text")
        buf_before = app.state.inspector_input_buffer
        app._on_text_input("")
        assert app.state.inspector_input_buffer == buf_before


# ===================================================================
# _inspector_cancel_edit
# ===================================================================


class TestInspectorCancelEdit:
    def test_clears_field_and_buffer(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label")
        _sel(app, 0)
        app._inspector_start_edit("text")
        assert app.state.inspector_selected_field == "text"
        app._inspector_cancel_edit()
        assert app.state.inspector_selected_field is None
        assert app.state.inspector_input_buffer == ""


# ===================================================================
# _toggle_overflow_warnings
# ===================================================================


class TestToggleOverflowWarnings:
    def test_toggles_on(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.show_overflow_warnings = False
        app._toggle_overflow_warnings()
        assert app.show_overflow_warnings is True

    def test_toggles_off(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.show_overflow_warnings = True
        app._toggle_overflow_warnings()
        assert app.show_overflow_warnings is False

    def test_updates_status(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.show_overflow_warnings = False
        app._toggle_overflow_warnings()
        assert "ON" in app.dialog_message


# ===================================================================
# _intelligent_auto_arrange
# ===================================================================


class TestIntelligentAutoArrange:
    def test_arranges_widgets_no_overlap(self, tmp_path, monkeypatch):
        import pygame

        app = _make_app(tmp_path, monkeypatch)
        # Place 3 widgets at same position (overlapping)
        for _ in range(3):
            _add(app, x=0, y=0, width=40, height=16)
        app._intelligent_auto_arrange()
        sc = app.state.current_scene()
        rects = [
            pygame.Rect(int(w.x), int(w.y), int(w.width), int(w.height))
            for w in sc.widgets
        ]
        # Check no pair overlaps
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                assert not rects[i].colliderect(rects[j]), f"Widgets {i} and {j} overlap"

    def test_empty_scene_no_crash(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._intelligent_auto_arrange()

    def test_single_widget(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, y=10, width=40, height=16)
        app._intelligent_auto_arrange()
        # Should still have 1 widget, possibly repositioned
        assert len(app.state.current_scene().widgets) == 1


# ===================================================================
# _find_best_position
# ===================================================================


class TestFindBestPosition:
    def test_finds_non_overlapping_pos(self, tmp_path, monkeypatch):
        import pygame

        app = _make_app(tmp_path, monkeypatch)
        # Place one widget at 0,0
        _add(app, x=0, y=0, width=40, height=16)
        sc = app.state.current_scene()
        new_w = WidgetConfig(type="label", x=0, y=0, width=40, height=16)
        sc.widgets.append(new_w)
        x, y = app._find_best_position(new_w, sc)
        # Should not overlap existing widget
        new_rect = pygame.Rect(x, y, 40, 16)
        existing = pygame.Rect(0, 0, 40, 16)
        assert not new_rect.colliderect(existing)

    def test_empty_scene_returns_valid_pos(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        w = WidgetConfig(type="label", x=0, y=0, width=40, height=16)
        sc.widgets.append(w)
        x, y = app._find_best_position(w, sc)
        assert x >= 0
        assert y >= 0


# ===================================================================
# _component_info_from_group
# ===================================================================


class TestComponentInfoFromGroup:
    def test_new_scheme(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        result = app._component_info_from_group("comp:button:btn1:3")
        assert result == ("button", "btn1")

    def test_legacy_scheme(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        result = app._component_info_from_group("comp:gauge:2")
        assert result == ("gauge", "gauge")

    def test_non_component_group(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        result = app._component_info_from_group("mygroup")
        assert result is None

    def test_empty_string(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        result = app._component_info_from_group("")
        assert result is None


# ===================================================================
# _format_group_label
# ===================================================================


class TestFormatGroupLabel:
    def test_component_group(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        result = app._format_group_label("comp:button:btn1:3", [0, 1, 2])
        assert "component" in result
        assert "button" in result
        assert "3" in result

    def test_plain_group(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        result = app._format_group_label("headers", [0, 1])
        assert "group" in result
        assert "headers" in result
        assert "2" in result

    def test_same_type_root(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        result = app._format_group_label("comp:gauge:2", [0])
        assert "component" in result
        assert "gauge" in result


# ===================================================================
# _tri_state
# ===================================================================


class TestTriState:
    def test_all_true(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert app._tri_state([True, True, True]) == "on"

    def test_all_false(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert app._tri_state([False, False]) == "off"

    def test_mixed(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert app._tri_state([True, False]) == "mixed"

    def test_empty(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert app._tri_state([]) == "off"


# ===================================================================
# _build_template_actions
# ===================================================================


class TestBuildTemplateActions:
    def test_empty_template_library(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.template_library.templates = []
        result = app._build_template_actions()
        assert result == []

    def test_with_templates(self, tmp_path, monkeypatch):
        from types import SimpleNamespace

        app = _make_app(tmp_path, monkeypatch)
        tpl = SimpleNamespace(
            metadata=SimpleNamespace(name="TestTpl"),
            scene=SimpleNamespace(_raw_data={"widgets": []}),
        )
        app.template_library.templates = [tpl]
        result = app._build_template_actions()
        # Should have header + 1 template
        assert len(result) >= 2
        assert "Templates" in result[0][0]
        assert "TestTpl" in result[1][0]
