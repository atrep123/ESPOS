"""Tests for property_cycles.py — uncovered functions and guard branches.

Covers: outline_mode, outline_only, set_inverse_style, set_bold_style,
set_default_style, plus guard branches for cycle_*, toggle_*, smart_edit,
adjust_value, toggle_checked, cycle_gray_fg, cycle_gray_bg.
"""

from __future__ import annotations

from cyberpunk_designer.selection_ops.property_cycles import (
    adjust_value,
    cycle_align,
    cycle_border_style,
    cycle_color_preset,
    cycle_gray_bg,
    cycle_gray_fg,
    cycle_style,
    cycle_text_overflow,
    cycle_valign,
    cycle_widget_type,
    outline_mode,
    outline_only,
    set_bold_style,
    set_default_style,
    set_inverse_style,
    smart_edit,
    toggle_border,
    toggle_checked,
    toggle_enabled,
    toggle_visibility,
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
    defaults = dict(type="label", x=0, y=0, width=20, height=10, text="W")
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


# ===========================================================================
# outline_mode
# ===========================================================================

class TestOutlineMode:
    def test_basic(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, color_bg="white", border=False)
        _sel(app, 0)
        outline_mode(app)
        w = app.state.current_scene().widgets[0]
        assert w.border is True
        assert w.color_bg == "#000000"

    def test_multiple(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, color_bg="white")
        _add(app, color_bg="red")
        _sel(app, 0, 1)
        outline_mode(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].color_bg == "#000000"
        assert sc.widgets[1].color_bg == "#000000"

    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app)
        outline_mode(app)  # no crash


# ===========================================================================
# outline_only
# ===========================================================================

class TestOutlineOnly:
    def test_basic(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, color_bg="white", border=False)
        _sel(app, 0)
        outline_only(app)
        w = app.state.current_scene().widgets[0]
        assert w.border is True
        assert w.color_bg == "black"

    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app)
        outline_only(app)  # no crash

    def test_invalid_index(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        app.state.selected = [99]
        outline_only(app)  # skipped


# ===========================================================================
# set_inverse_style
# ===========================================================================

class TestSetInverseStyle:
    def test_basic(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, style="default")
        _sel(app, 0)
        set_inverse_style(app)
        assert app.state.current_scene().widgets[0].style == "inverse"

    def test_already_inverse(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, style="inverse")
        _sel(app, 0)
        set_inverse_style(app)
        assert app.state.current_scene().widgets[0].style == "inverse"

    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app)
        set_inverse_style(app)  # no crash


# ===========================================================================
# set_bold_style
# ===========================================================================

class TestSetBoldStyle:
    def test_basic(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, style="default")
        _sel(app, 0)
        set_bold_style(app)
        assert app.state.current_scene().widgets[0].style == "bold"

    def test_already_bold(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, style="bold")
        _sel(app, 0)
        set_bold_style(app)
        assert app.state.current_scene().widgets[0].style == "bold"

    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app)
        set_bold_style(app)  # no crash


# ===========================================================================
# set_default_style
# ===========================================================================

class TestSetDefaultStyle:
    def test_basic(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, style="bold")
        _sel(app, 0)
        set_default_style(app)
        assert app.state.current_scene().widgets[0].style == "default"

    def test_already_default(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, style="default")
        _sel(app, 0)
        set_default_style(app)
        assert app.state.current_scene().widgets[0].style == "default"

    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app)
        set_default_style(app)  # no crash


# ===========================================================================
# Guard branches for cycle functions
# ===========================================================================

class TestCycleStyleGuards:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        cycle_style(app)  # no crash

    def test_cycle_default_to_bold(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, style="default")
        _sel(app, 0)
        cycle_style(app)
        assert app.state.current_scene().widgets[0].style == "bold"

    def test_cycle_unknown_style(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, style="unknown_style")
        _sel(app, 0)
        cycle_style(app)
        assert app.state.current_scene().widgets[0].style == "default"


class TestToggleVisibilityGuards:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        toggle_visibility(app)  # no crash

    def test_toggle(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, visible=True)
        _sel(app, 0)
        toggle_visibility(app)
        assert app.state.current_scene().widgets[0].visible is False


class TestCycleWidgetTypeGuards:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        cycle_widget_type(app)  # no crash

    def test_cycle_label_to_button(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label")
        _sel(app, 0)
        cycle_widget_type(app)
        assert app.state.current_scene().widgets[0].type == "button"

    def test_cycle_unknown_type(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="custom_unknown")
        _sel(app, 0)
        cycle_widget_type(app)
        assert app.state.current_scene().widgets[0].type == "label"


class TestCycleBorderStyleGuards:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        cycle_border_style(app)  # no crash

    def test_cycle(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, border_style="none")
        _sel(app, 0)
        cycle_border_style(app)
        assert app.state.current_scene().widgets[0].border_style == "single"

    def test_cycle_unknown(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, border_style="weird")
        _sel(app, 0)
        cycle_border_style(app)
        assert app.state.current_scene().widgets[0].border_style == "single"


class TestCycleColorPresetGuards:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        cycle_color_preset(app)  # no crash

    def test_cycle(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, color_fg="#f5f5f5", color_bg="#000000")
        _sel(app, 0)
        cycle_color_preset(app)
        w = app.state.current_scene().widgets[0]
        assert w.color_fg == "#f5f5f5" and w.color_bg == "#101010"


class TestToggleBorderGuards:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        toggle_border(app)  # no crash

    def test_toggle(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, border=True)
        _sel(app, 0)
        toggle_border(app)
        assert app.state.current_scene().widgets[0].border is False


class TestCycleTextOverflowGuards:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        cycle_text_overflow(app)  # no crash

    def test_cycle(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, text_overflow="ellipsis")
        _sel(app, 0)
        cycle_text_overflow(app)
        assert app.state.current_scene().widgets[0].text_overflow == "wrap"

    def test_cycle_unknown(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app, text_overflow="ellipsis")
        w.text_overflow = "weird"  # force invalid value post-construction
        _sel(app, 0)
        cycle_text_overflow(app)
        # ValueError in index() → falls back to "ellipsis"
        assert app.state.current_scene().widgets[0].text_overflow == "ellipsis"


class TestCycleAlignGuards:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        cycle_align(app)  # no crash

    def test_cycle(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, align="left")
        _sel(app, 0)
        cycle_align(app)
        assert app.state.current_scene().widgets[0].align == "center"

    def test_cycle_unknown(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, align="justify")
        _sel(app, 0)
        cycle_align(app)
        assert app.state.current_scene().widgets[0].align == "left"


class TestCycleValignGuards:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        cycle_valign(app)  # no crash

    def test_cycle(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, valign="top")
        _sel(app, 0)
        cycle_valign(app)
        assert app.state.current_scene().widgets[0].valign == "middle"

    def test_cycle_unknown(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, valign="stretch")
        _sel(app, 0)
        cycle_valign(app)
        assert app.state.current_scene().widgets[0].valign == "middle"


# ===========================================================================
# smart_edit
# ===========================================================================

class TestSmartEdit:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        smart_edit(app)  # no crash

    def test_gauge_starts_value_edit(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="gauge", value=50)
        _sel(app, 0)
        smart_edit(app)
        assert app.state.inspector_selected_field == "value"

    def test_chart_starts_data_edit(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="chart")
        _sel(app, 0)
        smart_edit(app)
        assert app.state.inspector_selected_field == "data_points"

    def test_icon_starts_icon_edit(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="icon")
        _sel(app, 0)
        smart_edit(app)
        assert app.state.inspector_selected_field == "icon_char"

    def test_checkbox_toggles_checked(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="checkbox", checked=False)
        _sel(app, 0)
        smart_edit(app)
        assert app.state.current_scene().widgets[0].checked is True

    def test_label_starts_text_edit(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label")
        _sel(app, 0)
        smart_edit(app)
        assert app.state.inspector_selected_field == "text"

    def test_slider_starts_value_edit(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="slider", value=25)
        _sel(app, 0)
        smart_edit(app)
        assert app.state.inspector_selected_field == "value"


# ===========================================================================
# adjust_value
# ===========================================================================

class TestAdjustValue:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        adjust_value(app, 1)  # no crash

    def test_increment(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="gauge", value=50, min_value=0, max_value=100)
        _sel(app, 0)
        adjust_value(app, 10)
        assert app.state.current_scene().widgets[0].value == 60

    def test_decrement(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="gauge", value=50, min_value=0, max_value=100)
        _sel(app, 0)
        adjust_value(app, -10)
        assert app.state.current_scene().widgets[0].value == 40

    def test_clamps_to_max(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="gauge", value=95, min_value=0, max_value=100)
        _sel(app, 0)
        adjust_value(app, 20)
        assert app.state.current_scene().widgets[0].value == 100

    def test_clamps_to_min(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="gauge", value=5, min_value=0, max_value=100)
        _sel(app, 0)
        adjust_value(app, -20)
        assert app.state.current_scene().widgets[0].value == 0

    def test_non_value_type(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label")
        _sel(app, 0)
        adjust_value(app, 1)  # label isn't a value type — noop


# ===========================================================================
# toggle_enabled
# ===========================================================================

class TestToggleEnabled:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        toggle_enabled(app)  # no crash

    def test_toggle(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, enabled=True)
        _sel(app, 0)
        toggle_enabled(app)
        assert app.state.current_scene().widgets[0].enabled is False


# ===========================================================================
# toggle_checked
# ===========================================================================

class TestToggleChecked:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        toggle_checked(app)  # no crash

    def test_checkbox(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="checkbox", checked=False)
        _sel(app, 0)
        toggle_checked(app)
        assert app.state.current_scene().widgets[0].checked is True

    def test_non_checkbox(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label")
        _sel(app, 0)
        toggle_checked(app)  # not applicable

    def test_locked(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="checkbox", checked=False, locked=True)
        _sel(app, 0)
        toggle_checked(app)
        assert app.state.current_scene().widgets[0].checked is False  # locked


# ===========================================================================
# cycle_gray_fg / cycle_gray_bg
# ===========================================================================

class TestCycleGrayFg:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        cycle_gray_fg(app)  # no crash

    def test_cycle(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, color_fg="#000000")
        _sel(app, 0)
        cycle_gray_fg(app)
        w = app.state.current_scene().widgets[0]
        assert w.color_fg == "#111111"

    def test_no_match_goes_to_first(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, color_fg="white")
        _sel(app, 0)
        cycle_gray_fg(app)
        w = app.state.current_scene().widgets[0]
        assert w.color_fg == "#000000"


class TestCycleGrayBg:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        cycle_gray_bg(app)  # no crash

    def test_cycle(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, color_bg="#000000")
        _sel(app, 0)
        cycle_gray_bg(app)
        w = app.state.current_scene().widgets[0]
        assert w.color_bg == "#111111"

    def test_no_match_goes_to_first(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, color_bg="red")
        _sel(app, 0)
        cycle_gray_bg(app)
        w = app.state.current_scene().widgets[0]
        assert w.color_bg == "#000000"
