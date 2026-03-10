"""Tests for _emit_widget in tools/ui_codegen.py — per-widget C code generation."""

from tools.ui_codegen import _emit_widget, build_string_pool, collect_widget_strings


def _pool_for(w: dict) -> object:
    """Build a StringPool containing all strings referenced by widget *w*."""
    strs = collect_widget_strings(w)
    return build_string_pool(strs, symbol_prefix="s_")


def _emit(w: dict, idx: int = 0) -> str:
    """Emit C code for widget *w* and return as a single string."""
    pool = _pool_for(w)
    return "\n".join(_emit_widget(w, idx, pool))


# ── Basic label ───────────────────────────────────────────────────────


class TestBasicLabel:
    def test_type(self):
        out = _emit({"type": "label", "x": 10, "y": 20, "width": 60, "height": 14, "text": "HI"})
        assert "UIW_LABEL" in out

    def test_geometry(self):
        out = _emit({"type": "label", "x": 5, "y": 7, "width": 42, "height": 11})
        assert ".x = 5" in out
        assert ".y = 7" in out
        assert ".width = 42" in out
        assert ".height = 11" in out

    def test_text_not_null(self):
        out = _emit({"type": "label", "x": 0, "y": 0, "width": 40, "height": 12, "text": "HELLO"})
        assert ".text = s_" in out  # has a pool reference
        assert "NULL" not in out or ".text = NULL" not in out

    def test_empty_text_null(self):
        out = _emit({"type": "label", "x": 0, "y": 0, "width": 40, "height": 12})
        assert ".text = NULL" in out

    def test_index_in_comment(self):
        out = _emit({"type": "box", "x": 0, "y": 0, "width": 20, "height": 10}, idx=3)
        assert "[3]" in out


# ── Widget types ──────────────────────────────────────────────────────


class TestWidgetTypes:
    def test_button(self):
        out = _emit({"type": "button", "x": 0, "y": 0, "width": 40, "height": 14})
        assert "UIW_BUTTON" in out

    def test_checkbox(self):
        out = _emit({"type": "checkbox", "x": 0, "y": 0, "width": 20, "height": 20})
        assert "UIW_CHECKBOX" in out

    def test_gauge(self):
        out = _emit({"type": "gauge", "x": 0, "y": 0, "width": 50, "height": 10})
        assert "UIW_GAUGE" in out

    def test_chart(self):
        out = _emit({"type": "chart", "x": 0, "y": 0, "width": 60, "height": 30})
        assert "UIW_CHART" in out

    def test_slider(self):
        out = _emit({"type": "slider", "x": 0, "y": 0, "width": 60, "height": 14})
        assert "UIW_SLIDER" in out

    def test_progressbar(self):
        out = _emit({"type": "progressbar", "x": 0, "y": 0, "width": 80, "height": 10})
        assert "UIW_PROGRESSBAR" in out

    def test_icon(self):
        out = _emit({"type": "icon", "x": 0, "y": 0, "width": 24, "height": 24})
        assert "UIW_ICON" in out

    def test_panel(self):
        out = _emit({"type": "panel", "x": 0, "y": 0, "width": 100, "height": 50})
        assert "UIW_PANEL" in out

    def test_unknown_defaults_label(self):
        out = _emit({"type": "unknown_xyz", "x": 0, "y": 0, "width": 20, "height": 10})
        assert "UIW_LABEL" in out


# ── Boolean fields ────────────────────────────────────────────────────


class TestBoolFields:
    def test_border_true(self):
        out = _emit({"type": "box", "x": 0, "y": 0, "width": 20, "height": 10, "border": True})
        assert ".border = 1" in out

    def test_border_false(self):
        out = _emit({"type": "box", "x": 0, "y": 0, "width": 20, "height": 10, "border": False})
        assert ".border = 0" in out

    def test_checked_true(self):
        out = _emit({"type": "checkbox", "x": 0, "y": 0, "width": 20, "height": 20, "checked": True})
        assert ".checked = 1" in out

    def test_visible_false(self):
        out = _emit({"type": "box", "x": 0, "y": 0, "width": 20, "height": 10, "visible": False})
        assert ".visible = 0" in out

    def test_enabled_false(self):
        out = _emit({"type": "box", "x": 0, "y": 0, "width": 20, "height": 10, "enabled": False})
        assert ".enabled = 0" in out


# ── Value fields ──────────────────────────────────────────────────────


class TestValueFields:
    def test_value_min_max(self):
        out = _emit({"type": "gauge", "x": 0, "y": 0, "width": 50, "height": 10,
                      "value": 42, "min_value": -10, "max_value": 200})
        assert ".value = 42" in out
        assert ".min_value = -10" in out
        assert ".max_value = 200" in out

    def test_defaults(self):
        out = _emit({"type": "gauge", "x": 0, "y": 0, "width": 50, "height": 10})
        assert ".value = 0" in out
        assert ".min_value = 0" in out
        assert ".max_value = 100" in out


# ── Color fields ──────────────────────────────────────────────────────


class TestColorFields:
    def test_white_fg(self):
        out = _emit({"type": "label", "x": 0, "y": 0, "width": 40, "height": 12,
                      "color_fg": "#ffffff"})
        assert ".fg = 15" in out

    def test_black_bg(self):
        out = _emit({"type": "label", "x": 0, "y": 0, "width": 40, "height": 12,
                      "color_bg": "#000000"})
        assert ".bg = 0" in out


# ── String fields (id, constraints, animations) ──────────────────────


class TestStringFields:
    def test_widget_id_ref(self):
        out = _emit({"type": "label", "x": 0, "y": 0, "width": 40, "height": 12,
                      "_widget_id": "status_lbl"})
        assert ".id = s_" in out

    def test_no_id_null(self):
        out = _emit({"type": "label", "x": 0, "y": 0, "width": 40, "height": 12})
        assert ".id = NULL" in out

    def test_runtime_becomes_constraints(self):
        out = _emit({"type": "label", "x": 0, "y": 0, "width": 40, "height": 12,
                      "runtime": "text=sensor.temp"})
        assert ".constraints_json = s_" in out

    def test_animations_list(self):
        out = _emit({"type": "box", "x": 0, "y": 0, "width": 20, "height": 10,
                      "animations": ["fade", "slide"]})
        assert ".animations_csv = s_" in out

    def test_no_constraints_null(self):
        out = _emit({"type": "box", "x": 0, "y": 0, "width": 20, "height": 10})
        assert ".constraints_json = NULL" in out

    def test_no_animations_null(self):
        out = _emit({"type": "box", "x": 0, "y": 0, "width": 20, "height": 10})
        assert ".animations_csv = NULL" in out


# ── Style/align/overflow enums ────────────────────────────────────────


class TestEnumFields:
    def test_max_lines(self):
        out = _emit({"type": "label", "x": 0, "y": 0, "width": 40, "height": 30,
                      "max_lines": 3})
        assert ".max_lines = 3" in out

    def test_negative_max_lines_clamped(self):
        out = _emit({"type": "label", "x": 0, "y": 0, "width": 40, "height": 30,
                      "max_lines": -1})
        assert ".max_lines = 0" in out


# ── Output structure ──────────────────────────────────────────────────


class TestOutputStructure:
    def test_opens_with_brace(self):
        lines = _emit_widget(
            {"type": "box", "x": 0, "y": 0, "width": 20, "height": 10}, 0, _pool_for({}))
        assert lines[0].strip().startswith("{")

    def test_closes_with_comma(self):
        lines = _emit_widget(
            {"type": "box", "x": 0, "y": 0, "width": 20, "height": 10}, 0, _pool_for({}))
        assert lines[-1].strip() == "},"

    def test_returns_list(self):
        result = _emit_widget(
            {"type": "box", "x": 0, "y": 0, "width": 20, "height": 10}, 0, _pool_for({}))
        assert isinstance(result, list)
        assert all(isinstance(line, str) for line in result)
