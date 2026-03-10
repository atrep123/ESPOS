"""Tests for validation rules 107-114 in tools/validate_design.py."""

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


# ── Rule 107: text_overflow=wrap with max_lines=1 ────────────────────


def test_r107_wrap_maxlines1_warns():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 30,
                "text": "hi", "text_overflow": "wrap", "max_lines": 1}])
    ws = [w for w in _warns(d) if "wrap" in w.message and "max_lines=1" in w.message]
    assert len(ws) == 1


def test_r107_wrap_maxlines2_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 30,
                "text": "hi", "text_overflow": "wrap", "max_lines": 2}])
    ws = [w for w in _warns(d) if "wrap" in w.message and "max_lines=" in w.message and "second line" in w.message]
    assert len(ws) == 0


def test_r107_ellipsis_maxlines1_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 20,
                "text": "hi", "text_overflow": "ellipsis", "max_lines": 1}])
    ws = [w for w in _warns(d) if "wrap" in w.message and "max_lines=1" in w.message]
    assert len(ws) == 0


def test_r107_wrap_no_maxlines_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 30,
                "text": "hi", "text_overflow": "wrap"}])
    ws = [w for w in _warns(d) if "wrap" in w.message and "max_lines=1" in w.message]
    assert len(ws) == 0


# ── Rule 108: slider with height > width ──────────────────────────────


def test_r108_slider_tall_warns():
    d = _make([{"type": "slider", "x": 0, "y": 0, "width": 20, "height": 40,
                "value": 50, "min_value": 0, "max_value": 100}])
    ws = [w for w in _warns(d) if "slider" in w.message and "height" in w.message and "width" in w.message]
    assert len(ws) == 1


def test_r108_slider_wide_ok():
    d = _make([{"type": "slider", "x": 0, "y": 0, "width": 60, "height": 14,
                "value": 50, "min_value": 0, "max_value": 100}])
    ws = [w for w in _warns(d) if "slider" in w.message and "horizontal" in w.message]
    assert len(ws) == 0


def test_r108_slider_square_ok():
    d = _make([{"type": "slider", "x": 0, "y": 0, "width": 30, "height": 30,
                "value": 50, "min_value": 0, "max_value": 100}])
    ws = [w for w in _warns(d) if "slider" in w.message and "horizontal" in w.message]
    assert len(ws) == 0


def test_r108_non_slider_tall_no_warn():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 10, "height": 40}])
    ws = [w for w in _warns(d) if "horizontal track" in w.message]
    assert len(ws) == 0


# ── Rule 109: disabled+checked toggle without runtime ────────────────


def test_r109_disabled_checked_no_runtime_warns():
    d = _make([{"type": "checkbox", "x": 0, "y": 0, "width": 20, "height": 20,
                "enabled": False, "checked": True}])
    ws = [w for w in _warns(d) if "stuck" in w.message]
    assert len(ws) == 1


def test_r109_disabled_checked_with_runtime_ok():
    d = _make([{"type": "checkbox", "x": 0, "y": 0, "width": 20, "height": 20,
                "enabled": False, "checked": True, "runtime": "checked=sensor.flag"}])
    ws = [w for w in _warns(d) if "stuck" in w.message]
    assert len(ws) == 0


def test_r109_disabled_unchecked_ok():
    d = _make([{"type": "checkbox", "x": 0, "y": 0, "width": 20, "height": 20,
                "enabled": False, "checked": False}])
    ws = [w for w in _warns(d) if "stuck" in w.message]
    assert len(ws) == 0


def test_r109_enabled_checked_ok():
    d = _make([{"type": "checkbox", "x": 0, "y": 0, "width": 20, "height": 20,
                "enabled": True, "checked": True}])
    ws = [w for w in _warns(d) if "stuck" in w.message]
    assert len(ws) == 0


def test_r109_radiobutton_stuck_warns():
    d = _make([{"type": "radiobutton", "x": 0, "y": 0, "width": 20, "height": 20,
                "enabled": False, "checked": True}])
    ws = [w for w in _warns(d) if "stuck" in w.message]
    assert len(ws) == 1


# ── Rule 110: widget ID structural issues ─────────────────────────────


def test_r110_double_dot_errors():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 40, "height": 12,
                "text": "hi", "_widget_id": "menu..label"}])
    es = [e for e in _errors(d) if "structural issue" in e.message]
    assert len(es) == 1


def test_r110_trailing_dot_errors():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 40, "height": 12,
                "text": "hi", "_widget_id": "menu.label."}])
    es = [e for e in _errors(d) if "structural issue" in e.message]
    assert len(es) == 1


def test_r110_trailing_hyphen_errors():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 40, "height": 12,
                "text": "hi", "_widget_id": "header-"}])
    es = [e for e in _errors(d) if "structural issue" in e.message]
    assert len(es) == 1


def test_r110_valid_dotted_id_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 40, "height": 12,
                "text": "hi", "_widget_id": "menu.item0.label"}])
    es = [e for e in _errors(d) if "structural issue" in e.message]
    assert len(es) == 0


def test_r110_valid_hyphen_id_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 40, "height": 12,
                "text": "hi", "_widget_id": "btn-ok"}])
    es = [e for e in _errors(d) if "structural issue" in e.message]
    assert len(es) == 0


# ── Rule 111: border=false but border_style not none/empty ────────────


def test_r111_border_false_style_double_warns():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 30, "height": 20,
                "border": False, "border_style": "double"}])
    ws = [w for w in _warns(d) if "border=false" in w.message and "border_style=" in w.message]
    assert len(ws) == 1


def test_r111_border_false_style_none_ok():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 30, "height": 20,
                "border": False, "border_style": "none"}])
    ws = [w for w in _warns(d) if "border=false" in w.message and "style is ignored" in w.message]
    assert len(ws) == 0


def test_r111_border_true_style_double_ok():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 30, "height": 20,
                "border": True, "border_style": "double"}])
    ws = [w for w in _warns(d) if "style is ignored" in w.message]
    assert len(ws) == 0


def test_r111_border_false_no_style_ok():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 30, "height": 20,
                "border": False}])
    ws = [w for w in _warns(d) if "style is ignored" in w.message]
    assert len(ws) == 0


# ── Rule 112: both visible=false and enabled=false ────────────────────


def test_r112_both_false_warns():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 30, "height": 20,
                "visible": False, "enabled": False}])
    ws = [w for w in _warns(d) if "visible=false" in w.message and "enabled=false" in w.message]
    assert len(ws) == 1


def test_r112_visible_true_enabled_false_ok():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 30, "height": 20,
                "visible": True, "enabled": False}])
    ws = [w for w in _warns(d) if "both" in w.message and "redundant" in w.message]
    assert len(ws) == 0


def test_r112_visible_false_enabled_true_ok():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 30, "height": 20,
                "visible": False, "enabled": True}])
    ws = [w for w in _warns(d) if "both" in w.message and "redundant" in w.message]
    assert len(ws) == 0


# ── Rule 113: text_overflow=wrap but too short for 2 lines ────────────


def test_r113_wrap_short_warns():
    # need height < RENDER_PAD*2 + CHAR_H*2 = 4 + 16 = 20
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 19,
                "text": "hi", "text_overflow": "wrap"}])
    ws = [w for w in _warns(d) if "wrap" in w.message and "too short for 2 lines" in w.message]
    assert len(ws) == 1


def test_r113_wrap_exact_min_ok():
    # exactly 20 = RENDER_PAD*2 + CHAR_H*2
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 20,
                "text": "hi", "text_overflow": "wrap"}])
    ws = [w for w in _warns(d) if "too short for 2 lines" in w.message]
    assert len(ws) == 0


def test_r113_clip_short_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 12,
                "text": "hi", "text_overflow": "clip"}])
    ws = [w for w in _warns(d) if "too short for 2 lines" in w.message]
    assert len(ws) == 0


def test_r113_wrap_tall_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 40,
                "text": "hi", "text_overflow": "wrap"}])
    ws = [w for w in _warns(d) if "too short for 2 lines" in w.message]
    assert len(ws) == 0


# ── Rule 114: align center/right on checkbox/radiobutton ──────────────


def test_r114_checkbox_center_warns():
    d = _make([{"type": "checkbox", "x": 0, "y": 0, "width": 40, "height": 12,
                "text": "OK", "align": "center"}])
    ws = [w for w in _warns(d) if "align=" in w.message and "fixed left-edge" in w.message]
    assert len(ws) == 1


def test_r114_checkbox_right_warns():
    d = _make([{"type": "checkbox", "x": 0, "y": 0, "width": 40, "height": 12,
                "text": "OK", "align": "right"}])
    ws = [w for w in _warns(d) if "fixed left-edge" in w.message]
    assert len(ws) == 1


def test_r114_checkbox_left_ok():
    d = _make([{"type": "checkbox", "x": 0, "y": 0, "width": 40, "height": 12,
                "text": "OK", "align": "left"}])
    ws = [w for w in _warns(d) if "fixed left-edge" in w.message]
    assert len(ws) == 0


def test_r114_radiobutton_center_warns():
    d = _make([{"type": "radiobutton", "x": 0, "y": 0, "width": 40, "height": 12,
                "text": "A", "align": "center"}])
    ws = [w for w in _warns(d) if "fixed left-edge" in w.message]
    assert len(ws) == 1


def test_r114_label_center_ok():
    """Label is not checkbox/radiobutton — no Rule 114 warn."""
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 40, "height": 12,
                "text": "OK", "align": "center"}])
    ws = [w for w in _warns(d) if "fixed left-edge" in w.message]
    assert len(ws) == 0
