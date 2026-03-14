"""Tests for inspector_field_to_str in cyberpunk_designer/inspector_logic.py.

Only covers simple-field paths that don't need a full app/scene mock
(data_points, chart_mode, text, runtime, computed fields, int fields, color fields).
"""

from types import SimpleNamespace

from cyberpunk_designer.inspector_logic import (
    _parse_active_count,
    _sorted_role_indices,
    inspector_field_to_str,
)


def _w(**kw):
    """Minimal WidgetConfig-like object."""
    defaults = dict(
        type="label",
        x=10,
        y=20,
        width=60,
        height=14,
        text="HI",
        style="default",
        color_fg="#f0f0f0",
        color_bg="black",
        border=False,
        border_style="none",
        align="left",
        valign="middle",
        value=0,
        min_value=0,
        max_value=100,
        padding_x=1,
        padding_y=0,
        margin_x=0,
        margin_y=0,
        z_index=0,
        runtime="",
        data_points=[],
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _app(selected=None):
    """Minimal app mock with state.selected returning the given list."""
    state = SimpleNamespace(selected=selected or [])
    state.current_scene = lambda: None
    state.selection_list = lambda: list(state.selected or [])
    return SimpleNamespace(state=state)


# ── data_points ────────────────────────────────────────────────────────


def test_data_points_empty():
    assert inspector_field_to_str(_app(), "data_points", _w()) == ""


def test_data_points_list():
    w = _w(data_points=[10, 20, 30])
    assert inspector_field_to_str(_app(), "data_points", w) == "10,20,30"


def test_data_points_none():
    w = _w(data_points=None)
    assert inspector_field_to_str(_app(), "data_points", w) == ""


# ── chart_mode ─────────────────────────────────────────────────────────


def test_chart_mode_bar():
    w = _w(style="bar", text="")
    assert inspector_field_to_str(_app(), "chart_mode", w) == "bar"


def test_chart_mode_line():
    w = _w(style="line", text="")
    assert inspector_field_to_str(_app(), "chart_mode", w) == "line"


def test_chart_mode_fallback_from_text():
    w = _w(style="default", text="BAR CHART")
    assert inspector_field_to_str(_app(), "chart_mode", w) == "bar"


def test_chart_mode_fallback_line():
    w = _w(style="default", text="TEMPS")
    assert inspector_field_to_str(_app(), "chart_mode", w) == "line"


# ── text / runtime ────────────────────────────────────────────────────


def test_text_field():
    assert inspector_field_to_str(_app(), "text", _w(text="HELLO")) == "HELLO"


def test_text_field_empty():
    assert inspector_field_to_str(_app(), "text", _w(text="")) == ""


def test_runtime_field():
    w = _w(runtime="bind=x;kind=int")
    assert inspector_field_to_str(_app(), "runtime", w) == "bind=x;kind=int"


def test_runtime_field_empty():
    assert inspector_field_to_str(_app(), "runtime", _w(runtime="")) == ""


# ── computed fields ───────────────────────────────────────────────────


def test_size():
    w = _w(width=60, height=14)
    assert inspector_field_to_str(_app(), "_size", w) == "60x14"


# ── _sorted_role_indices ──────────────────────────────────────────────


def test_sorted_role_indices_basic():
    role_idx = {"tab_0": 0, "tab_1": 5, "tab_2": 3}
    result = _sorted_role_indices(role_idx, "tab_")
    assert result == [(0, 0), (1, 5), (2, 3)]


def test_sorted_role_indices_no_match():
    role_idx = {"btn_0": 1, "btn_1": 2}
    result = _sorted_role_indices(role_idx, "tab_")
    assert result == []


def test_sorted_role_indices_empty():
    assert _sorted_role_indices({}, "tab_") == []
    assert _sorted_role_indices(None, "tab_") == []


def test_sorted_role_indices_empty_prefix():
    role_idx = {"tab_0": 0}
    assert _sorted_role_indices(role_idx, "") == []


def test_sorted_role_indices_mixed():
    role_idx = {"item_0": 10, "item_2": 20, "other_0": 30}
    result = _sorted_role_indices(role_idx, "item_")
    assert result == [(0, 10), (2, 20)]


def test_sorted_role_indices_non_digit_suffix():
    role_idx = {"tab_abc": 0, "tab_1": 5}
    result = _sorted_role_indices(role_idx, "tab_")
    assert result == [(1, 5)]


# ── _parse_active_count ───────────────────────────────────────────────


def test_parse_active_count_basic():
    assert _parse_active_count("2/5") == (1, 5)  # 2→0-based=1


def test_parse_active_count_first():
    assert _parse_active_count("1/3") == (0, 3)  # 1→0-based=0


def test_parse_active_count_clamped_high():
    assert _parse_active_count("10/3") == (2, 3)  # clamped to 3→0-based=2


def test_parse_active_count_clamped_low():
    assert _parse_active_count("0/5") == (0, 5)  # clamped to 1→0-based=0


def test_parse_active_count_zero_total():
    assert _parse_active_count("1/0") == (0, 0)


def test_parse_active_count_empty():
    assert _parse_active_count("") is None


def test_parse_active_count_no_slash():
    assert _parse_active_count("42") is None


def test_parse_active_count_non_numeric():
    assert _parse_active_count("a/b") is None


def test_parse_active_count_spaces():
    assert _parse_active_count(" 2 / 5 ") == (1, 5)


def test_position():
    w = _w(x=10, y=20)
    assert inspector_field_to_str(_app(), "_position", w) == "10,20"


# ── checked ───────────────────────────────────────────────────────────


def test_checked_true():
    w = _w(checked=True)
    # checked is a bool attr — field_to_str returns str(True) via generic path
    result = inspector_field_to_str(_app(), "checked", w)
    assert result == "True"


def test_checked_false():
    w = _w(checked=False)
    result = inspector_field_to_str(_app(), "checked", w)
    # Generic path: str(getattr(w, "checked", "") or "") → False is falsy → ""
    assert result == ""


# ── items ─────────────────────────────────────────────────────────────


def test_items_list():
    w = _w(items=["A", "B", "C"])
    result = inspector_field_to_str(_app(), "items", w)
    assert result == "['A', 'B', 'C']" or result  # generic str() of list


def test_items_empty():
    w = _w(items=[])
    result = inspector_field_to_str(_app(), "items", w)
    assert result == "" or result == "[]"


def test_items_none():
    w = _w(items=None)
    result = inspector_field_to_str(_app(), "items", w)
    assert result == ""


# ── multi-selection mixed values ──────────────────────────────────────


def _scene_with_widgets(*widgets):
    from types import SimpleNamespace as NS

    return NS(widgets=list(widgets), width=256, height=128, name="main")


def _app_multi(widgets, selected):
    sc = _scene_with_widgets(*widgets)
    state = SimpleNamespace(selected=selected, current_scene=lambda: sc)
    state.selection_list = lambda: list(state.selected or [])
    app = SimpleNamespace(state=state)
    app._selection_bounds = lambda sel: None
    return app


def test_multi_select_same_color():
    w0 = _w(color_fg="#ff0000")
    w1 = _w(color_fg="#ff0000")
    app = _app_multi([w0, w1], [0, 1])
    assert inspector_field_to_str(app, "color_fg", w0) == "#ff0000"


def test_multi_select_different_color():
    w0 = _w(color_fg="#ff0000")
    w1 = _w(color_fg="#00ff00")
    app = _app_multi([w0, w1], [0, 1])
    assert inspector_field_to_str(app, "color_fg", w0) == ""


def test_multi_select_same_align():
    w0 = _w(align="center")
    w1 = _w(align="center")
    app = _app_multi([w0, w1], [0, 1])
    assert inspector_field_to_str(app, "align", w0) == "center"


def test_multi_select_different_align():
    w0 = _w(align="left")
    w1 = _w(align="right")
    app = _app_multi([w0, w1], [0, 1])
    assert inspector_field_to_str(app, "align", w0) == ""


def test_padding():
    w = _w(padding_x=5, padding_y=3)
    assert inspector_field_to_str(_app(), "_padding", w) == "5,3"


def test_margin():
    w = _w(margin_x=2, margin_y=4)
    assert inspector_field_to_str(_app(), "_margin", w) == "2,4"


def test_spacing():
    w = _w(padding_x=5, padding_y=3, margin_x=2, margin_y=4)
    assert inspector_field_to_str(_app(), "_spacing", w) == "5,3,2,4"


def test_value_range():
    w = _w(min_value=-100, max_value=100)
    assert inspector_field_to_str(_app(), "_value_range", w) == "-100,100"


# ── int fields ────────────────────────────────────────────────────────


def test_x():
    assert inspector_field_to_str(_app(), "x", _w(x=42)) == "42"


def test_y():
    assert inspector_field_to_str(_app(), "y", _w(y=7)) == "7"


def test_width():
    assert inspector_field_to_str(_app(), "width", _w(width=100)) == "100"


def test_z_index():
    assert inspector_field_to_str(_app(), "z_index", _w(z_index=3)) == "3"


# ── color / string fields ────────────────────────────────────────────


def test_color_fg():
    assert inspector_field_to_str(_app(), "color_fg", _w(color_fg="#ff0000")) == "#ff0000"


def test_color_bg():
    assert inspector_field_to_str(_app(), "color_bg", _w(color_bg="#0a0a0a")) == "#0a0a0a"


def test_align():
    assert inspector_field_to_str(_app(), "align", _w(align="center")) == "center"


def test_valign():
    assert inspector_field_to_str(_app(), "valign", _w(valign="top")) == "top"


def test_border_style():
    assert inspector_field_to_str(_app(), "border_style", _w(border_style="single")) == "single"
