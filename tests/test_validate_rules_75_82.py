"""Tests for validation rules 75-82 in tools/validate_design.py."""

from tools.validate_design import validate_data

FL = "test"


def _make(widgets, *, scene_w=128, scene_h=64, scene_name="main"):
    return {
        "scenes": {
            scene_name: {
                "width": scene_w,
                "height": scene_h,
                "widgets": widgets,
            }
        }
    }


def _issues(data, **kw):
    return validate_data(data, file_label=FL, warnings_as_errors=False, **kw)


def _errors(data, **kw):
    return [i for i in _issues(data, **kw) if i.level == "ERROR"]


def _warns(data, **kw):
    return [i for i in _issues(data, **kw) if i.level == "WARN"]


# ── Rule 75: chart minimum size ───────────────────────────────────────


def test_r75_chart_ok_size():
    d = _make(
        [
            {
                "type": "chart",
                "x": 0,
                "y": 0,
                "width": 40,
                "height": 30,
                "data_points": [1, 2, 3],
                "style": "bar",
            }
        ]
    )
    ws = [w for w in _warns(d) if "chart" in w.message and "too small" in w.message]
    assert ws == []


def test_r75_chart_too_narrow():
    d = _make(
        [
            {
                "type": "chart",
                "x": 0,
                "y": 0,
                "width": 10,
                "height": 30,
                "data_points": [1, 2, 3],
                "style": "bar",
            }
        ]
    )
    ws = [w for w in _warns(d) if "chart" in w.message and "too small" in w.message]
    assert len(ws) == 1


def test_r75_chart_too_short():
    d = _make(
        [
            {
                "type": "chart",
                "x": 0,
                "y": 0,
                "width": 40,
                "height": 10,
                "data_points": [1, 2, 3],
                "style": "bar",
            }
        ]
    )
    ws = [w for w in _warns(d) if "chart" in w.message and "too small" in w.message]
    assert len(ws) == 1


def test_r75_non_chart_small_ok():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 10, "height": 10}])
    ws = [w for w in _warns(d) if "chart" in w.message and "too small" in w.message]
    assert ws == []


# ── Rule 76: border_width > 0 but border=false ──────────────────────


def test_r76_border_width_with_border_true():
    d = _make(
        [
            {
                "type": "box",
                "x": 0,
                "y": 0,
                "width": 40,
                "height": 20,
                "border": True,
                "border_style": "single",
                "border_width": 2,
            }
        ]
    )
    ws = [w for w in _warns(d) if "border_width" in w.message and "border=false" in w.message]
    assert ws == []


def test_r76_border_width_no_border():
    d = _make(
        [
            {
                "type": "box",
                "x": 0,
                "y": 0,
                "width": 40,
                "height": 20,
                "border": False,
                "border_width": 2,
            }
        ]
    )
    ws = [w for w in _warns(d) if "border_width" in w.message and "border=false" in w.message]
    assert len(ws) == 1


def test_r76_no_border_width_ok():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 40, "height": 20, "border": False}])
    ws = [w for w in _warns(d) if "border_width" in w.message and "border=false" in w.message]
    assert ws == []


def test_r76_border_width_zero_ok():
    d = _make(
        [
            {
                "type": "box",
                "x": 0,
                "y": 0,
                "width": 40,
                "height": 20,
                "border": False,
                "border_width": 0,
            }
        ]
    )
    ws = [w for w in _warns(d) if "border_width" in w.message and "border=false" in w.message]
    assert ws == []


# ── Rule 77: text_overflow on non-text widget ────────────────────────


def test_r77_text_overflow_on_label_ok():
    d = _make(
        [{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "text_overflow": "wrap"}]
    )
    ws = [w for w in _warns(d) if "text_overflow" in w.message and "non-text" in w.message]
    assert ws == []


def test_r77_text_overflow_on_box():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 40, "height": 20, "text_overflow": "wrap"}])
    ws = [w for w in _warns(d) if "text_overflow" in w.message and "non-text" in w.message]
    assert len(ws) == 1


def test_r77_ellipsis_on_non_text_ok():
    d = _make(
        [{"type": "box", "x": 0, "y": 0, "width": 40, "height": 20, "text_overflow": "ellipsis"}]
    )
    ws = [w for w in _warns(d) if "text_overflow" in w.message and "non-text" in w.message]
    assert ws == []


def test_r77_empty_overflow_on_non_text_ok():
    d = _make(
        [
            {
                "type": "gauge",
                "x": 0,
                "y": 0,
                "width": 40,
                "height": 40,
                "text_overflow": "",
                "value": 0,
                "min_value": 0,
                "max_value": 100,
            }
        ]
    )
    ws = [w for w in _warns(d) if "text_overflow" in w.message and "non-text" in w.message]
    assert ws == []


# ── Rule 78: align on non-text widget ────────────────────────────────


def test_r78_align_on_label_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "align": "center"}])
    ws = [w for w in _warns(d) if "align=" in w.message and "non-text" in w.message]
    assert ws == []


def test_r78_align_on_gauge():
    d = _make(
        [
            {
                "type": "gauge",
                "x": 0,
                "y": 0,
                "width": 40,
                "height": 40,
                "align": "center",
                "value": 0,
                "min_value": 0,
                "max_value": 100,
            }
        ]
    )
    ws = [w for w in _warns(d) if "align=" in w.message and "non-text" in w.message]
    assert len(ws) == 1


def test_r78_left_align_on_gauge_ok():
    d = _make(
        [
            {
                "type": "gauge",
                "x": 0,
                "y": 0,
                "width": 40,
                "height": 40,
                "align": "left",
                "value": 0,
                "min_value": 0,
                "max_value": 100,
            }
        ]
    )
    ws = [w for w in _warns(d) if "align=" in w.message and "non-text" in w.message]
    assert ws == []


def test_r78_empty_align_on_gauge_ok():
    d = _make(
        [
            {
                "type": "gauge",
                "x": 0,
                "y": 0,
                "width": 40,
                "height": 40,
                "align": "",
                "value": 0,
                "min_value": 0,
                "max_value": 100,
            }
        ]
    )
    ws = [w for w in _warns(d) if "align=" in w.message and "non-text" in w.message]
    assert ws == []


# ── Rule 79: widget larger than scene ────────────────────────────────


def test_r79_widget_fits_scene():
    d = _make(
        [{"type": "box", "x": 0, "y": 0, "width": 128, "height": 64}], scene_w=128, scene_h=64
    )
    ws = [w for w in _warns(d) if "scene width" in w.message or "scene height" in w.message]
    assert ws == []


def test_r79_widget_wider_than_scene():
    d = _make(
        [{"type": "box", "x": 0, "y": 0, "width": 200, "height": 30}], scene_w=128, scene_h=64
    )
    ws = [w for w in _warns(d) if "scene width" in w.message]
    assert len(ws) == 1


def test_r79_widget_taller_than_scene():
    d = _make(
        [{"type": "box", "x": 0, "y": 0, "width": 40, "height": 100}], scene_w=128, scene_h=64
    )
    ws = [w for w in _warns(d) if "scene height" in w.message]
    assert len(ws) == 1


# ── Rule 80: margin pushes widget offscreen ──────────────────────────


def test_r80_margin_ok():
    d = _make(
        [{"type": "box", "x": 10, "y": 10, "width": 20, "height": 20, "margin_x": 5, "margin_y": 5}]
    )
    ws = [w for w in _warns(d) if "margin" in w.message and "past scene" in w.message]
    assert ws == []


def test_r80_margin_x_pushes_offscreen():
    d = _make(
        [{"type": "box", "x": 100, "y": 10, "width": 20, "height": 20, "margin_x": 30}],
        scene_w=128,
        scene_h=64,
    )
    ws = [w for w in _warns(d) if "margin_x" in w.message and "past scene" in w.message]
    assert len(ws) == 1


def test_r80_margin_y_pushes_offscreen():
    d = _make(
        [{"type": "box", "x": 10, "y": 50, "width": 20, "height": 20, "margin_y": 20}],
        scene_w=128,
        scene_h=64,
    )
    ws = [w for w in _warns(d) if "margin_y" in w.message and "past scene" in w.message]
    assert len(ws) == 1


def test_r80_no_margin_no_warn():
    d = _make([{"type": "box", "x": 10, "y": 10, "width": 20, "height": 20}])
    ws = [w for w in _warns(d) if "margin" in w.message and "past scene" in w.message]
    assert ws == []


# ── Rule 81: progressbar with text ───────────────────────────────────


def test_r81_progressbar_no_text_ok():
    d = _make(
        [
            {
                "type": "progressbar",
                "x": 0,
                "y": 0,
                "width": 60,
                "height": 14,
                "value": 50,
                "min_value": 0,
                "max_value": 100,
            }
        ]
    )
    ws = [w for w in _warns(d) if "progressbar" in w.message and "not rendered" in w.message]
    assert ws == []


def test_r81_progressbar_with_text():
    d = _make(
        [
            {
                "type": "progressbar",
                "x": 0,
                "y": 0,
                "width": 60,
                "height": 14,
                "text": "LOADING",
                "value": 50,
                "min_value": 0,
                "max_value": 100,
            }
        ]
    )
    ws = [w for w in _warns(d) if "progressbar" in w.message and "not rendered" in w.message]
    assert len(ws) == 1


def test_r81_progressbar_whitespace_ok():
    d = _make(
        [
            {
                "type": "progressbar",
                "x": 0,
                "y": 0,
                "width": 60,
                "height": 14,
                "text": "  ",
                "value": 50,
                "min_value": 0,
                "max_value": 100,
            }
        ]
    )
    ws = [w for w in _warns(d) if "progressbar" in w.message and "not rendered" in w.message]
    assert ws == []


# ── Rule 82: value fields on checkbox/radiobutton ────────────────────


def test_r82_checkbox_no_value_ok():
    d = _make([{"type": "checkbox", "x": 0, "y": 0, "width": 14, "height": 14}])
    ws = [w for w in _warns(d) if "not a value widget" in w.message]
    assert ws == []


def test_r82_checkbox_value_zero_ok():
    d = _make(
        [
            {
                "type": "checkbox",
                "x": 0,
                "y": 0,
                "width": 14,
                "height": 14,
                "value": 0,
                "min_value": 0,
                "max_value": 0,
            }
        ]
    )
    ws = [w for w in _warns(d) if "not a value widget" in w.message]
    assert ws == []


def test_r82_checkbox_value_nonzero():
    d = _make(
        [
            {
                "type": "checkbox",
                "x": 0,
                "y": 0,
                "width": 14,
                "height": 14,
                "value": 50,
                "min_value": 0,
                "max_value": 100,
            }
        ]
    )
    ws = [w for w in _warns(d) if "not a value widget" in w.message]
    assert len(ws) == 1


def test_r82_radiobutton_max_value():
    d = _make(
        [{"type": "radiobutton", "x": 0, "y": 0, "width": 14, "height": 14, "max_value": 100}]
    )
    ws = [w for w in _warns(d) if "not a value widget" in w.message]
    assert len(ws) == 1


def test_r82_slider_value_ok():
    d = _make(
        [
            {
                "type": "slider",
                "x": 0,
                "y": 0,
                "width": 60,
                "height": 16,
                "value": 50,
                "min_value": 0,
                "max_value": 100,
            }
        ]
    )
    ws = [w for w in _warns(d) if "not a value widget" in w.message]
    assert ws == []
