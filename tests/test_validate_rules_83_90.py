"""Tests for validation rules 83-90 in tools/validate_design.py."""

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


# ── Rule 83: checked on non-checkbox/radiobutton ──────────────────────


def test_r83_checked_on_label_warns():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi", "checked": True}])
    ws = [w for w in _warns(d) if "checked=true" in w.message and "non-checkbox" in w.message]
    assert len(ws) == 1


def test_r83_checked_on_button_warns():
    d = _make([{"type": "button", "x": 0, "y": 0, "width": 50, "height": 14,
                "text": "ok", "checked": True}])
    ws = [w for w in _warns(d) if "checked=true" in w.message]
    assert len(ws) == 1


def test_r83_checked_on_checkbox_ok():
    d = _make([{"type": "checkbox", "x": 0, "y": 0, "width": 14, "height": 14,
                "text": "x", "checked": True}])
    ws = [w for w in _warns(d) if "checked=true" in w.message and "non-checkbox" in w.message]
    assert ws == []


def test_r83_checked_on_radiobutton_ok():
    d = _make([{"type": "radiobutton", "x": 0, "y": 0, "width": 14, "height": 14,
                "text": "r", "checked": True}])
    ws = [w for w in _warns(d) if "checked=true" in w.message and "non-checkbox" in w.message]
    assert ws == []


def test_r83_checked_false_no_warn():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi", "checked": False}])
    ws = [w for w in _warns(d) if "checked=true" in w.message]
    assert ws == []


# ── Rule 84: icon_char on non-icon widget ─────────────────────────────


def test_r84_icon_char_on_label_warns():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi", "icon_char": "A"}])
    ws = [w for w in _warns(d) if "icon_char" in w.message and "non-icon" in w.message]
    assert len(ws) == 1


def test_r84_icon_char_on_icon_ok():
    d = _make([{"type": "icon", "x": 0, "y": 0, "width": 16, "height": 16,
                "icon_char": "A"}])
    ws = [w for w in _warns(d) if "icon_char" in w.message and "non-icon" in w.message]
    assert ws == []


def test_r84_empty_icon_char_no_warn():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi", "icon_char": ""}])
    ws = [w for w in _warns(d) if "icon_char" in w.message and "non-icon" in w.message]
    assert ws == []


def test_r84_no_icon_char_no_warn():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi"}])
    ws = [w for w in _warns(d) if "icon_char" in w.message and "non-icon" in w.message]
    assert ws == []


# ── Rule 85: max_lines on non-text widget ─────────────────────────────


def test_r85_max_lines_on_gauge_warns():
    d = _make([{"type": "gauge", "x": 0, "y": 0, "width": 40, "height": 20,
                "value": 50, "max_lines": 3}])
    ws = [w for w in _warns(d) if "max_lines" in w.message and "non-text" in w.message]
    assert len(ws) == 1


def test_r85_max_lines_on_box_warns():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 40, "height": 20,
                "max_lines": 2}])
    ws = [w for w in _warns(d) if "max_lines" in w.message and "non-text" in w.message]
    assert len(ws) == 1


def test_r85_max_lines_on_label_no_warn():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi", "max_lines": 2}])
    ws = [w for w in _warns(d) if "max_lines" in w.message and "non-text" in w.message]
    assert ws == []


def test_r85_max_lines_zero_on_gauge_no_warn():
    """max_lines=0 on non-text widget is not flagged (it has no effect anyway)."""
    d = _make([{"type": "gauge", "x": 0, "y": 0, "width": 40, "height": 20,
                "value": 50, "max_lines": 0}])
    ws = [w for w in _warns(d) if "non-text" in w.message and "max_lines" in w.message]
    assert ws == []


# ── Rule 86: max_lines firmware uint8 overflow ────────────────────────


def test_r86_max_lines_256_errors():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 60,
                "text": "hi", "max_lines": 256}])
    es = [e for e in _errors(d) if "max_lines" in e.message and "uint8" in e.message]
    assert len(es) == 1


def test_r86_max_lines_1000_errors():
    d = _make([{"type": "button", "x": 0, "y": 0, "width": 50, "height": 60,
                "text": "ok", "max_lines": 1000}])
    es = [e for e in _errors(d) if "max_lines" in e.message and "uint8" in e.message]
    assert len(es) == 1


def test_r86_max_lines_255_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 60,
                "text": "hi", "max_lines": 255}])
    es = [e for e in _errors(d) if "max_lines" in e.message and "uint8" in e.message]
    assert es == []


def test_r86_max_lines_10_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 60,
                "text": "hi", "max_lines": 10}])
    es = [e for e in _errors(d) if "max_lines" in e.message and "uint8" in e.message]
    assert es == []


# ── Rule 87: padding/margin must be int ───────────────────────────────


def test_r87_padding_string_errors():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi", "padding_x": "4"}])
    es = [e for e in _errors(d) if "padding_x" in e.message and "must be int" in e.message]
    assert len(es) == 1


def test_r87_margin_float_errors():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi", "margin_y": 2.5}])
    es = [e for e in _errors(d) if "margin_y" in e.message and "must be int" in e.message]
    assert len(es) == 1


def test_r87_padding_int_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 20,
                "text": "hi", "padding_x": 4, "padding_y": 2}])
    es = [e for e in _errors(d) if "must be int" in e.message and "padding" in e.message]
    assert es == []


def test_r87_margin_none_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi"}])
    es = [e for e in _errors(d) if "must be int" in e.message and "margin" in e.message]
    assert es == []


def test_r87_all_four_fields():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 50, "height": 20,
                "padding_x": "a", "padding_y": "b", "margin_x": 1.5, "margin_y": 2.5}])
    es = [e for e in _errors(d) if "must be int" in e.message]
    assert len(es) == 4


# ── Rule 88: max_lines with non-wrap text_overflow ────────────────────


def test_r88_max_lines_with_ellipsis_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 80, "height": 40,
                "text": "hello", "max_lines": 3, "text_overflow": "ellipsis"}])
    ws = [w for w in _warns(d) if "max_lines" in w.message and "text_overflow" in w.message]
    assert ws == []


def test_r88_max_lines_with_clip_warns():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 80, "height": 40,
                "text": "hello", "max_lines": 3, "text_overflow": "clip"}])
    ws = [w for w in _warns(d) if "max_lines" in w.message and "text_overflow" in w.message]
    assert len(ws) == 1


def test_r88_max_lines_with_wrap_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 80, "height": 40,
                "text": "hello", "max_lines": 3, "text_overflow": "wrap"}])
    ws = [w for w in _warns(d) if "max_lines" in w.message and "text_overflow" in w.message and "ignored" in w.message]
    assert ws == []


def test_r88_no_max_lines_no_warn():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 80, "height": 40,
                "text": "hello", "text_overflow": "ellipsis"}])
    ws = [w for w in _warns(d) if "max_lines" in w.message and "text_overflow" in w.message]
    assert ws == []


def test_r88_non_text_type_no_warn():
    d = _make([{"type": "gauge", "x": 0, "y": 0, "width": 40, "height": 20,
                "value": 50, "max_lines": 3, "text_overflow": "ellipsis"}])
    ws = [w for w in _warns(d) if "text_overflow" in w.message and "max_lines" in w.message and "ignored" in w.message]
    assert ws == []


# ── Rule 89: responsive_rules entries structure ───────────────────────


def test_r89_entry_not_dict_errors():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi", "responsive_rules": ["not_a_dict"]}])
    es = [e for e in _errors(d) if "responsive_rules[0]" in e.message and "must be a dict" in e.message]
    assert len(es) == 1


def test_r89_entry_missing_condition_errors():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi", "responsive_rules": [{"width": 100}]}])
    es = [e for e in _errors(d) if "responsive_rules[0]" in e.message and "missing 'condition'" in e.message]
    assert len(es) == 1


def test_r89_valid_entry_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi", "responsive_rules": [{"condition": "w>100", "width": 80}]}])
    es = [e for e in _errors(d) if "responsive_rules" in e.message]
    assert es == []


def test_r89_multiple_bad_entries():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi", "responsive_rules": [42, {"bad": True}]}])
    es = [e for e in _errors(d) if "responsive_rules" in e.message]
    assert len(es) == 2


def test_r89_not_list_handled_by_rule52():
    """Rule 52 already catches non-list, rule 89 should not fire."""
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi", "responsive_rules": "bad"}])
    es = [e for e in _errors(d) if "responsive_rules" in e.message]
    # Rule 52 fires for non-list
    assert any("must be a list" in e.message for e in es)


# ── Rule 90: chart data_points int16 overflow ─────────────────────────


def test_r90_data_points_overflow_positive():
    d = _make([{"type": "chart", "x": 0, "y": 0, "width": 40, "height": 30,
                "data_points": [100, 32768], "style": "bar"}])
    es = [e for e in _errors(d) if "data_points" in e.message and "int16" in e.message]
    assert len(es) == 1


def test_r90_data_points_overflow_negative():
    d = _make([{"type": "chart", "x": 0, "y": 0, "width": 40, "height": 30,
                "data_points": [-32769, 10], "style": "bar"}])
    es = [e for e in _errors(d) if "data_points" in e.message and "int16" in e.message]
    assert len(es) == 1


def test_r90_data_points_in_range_ok():
    d = _make([{"type": "chart", "x": 0, "y": 0, "width": 40, "height": 30,
                "data_points": [-32768, 0, 32767], "style": "bar"}])
    es = [e for e in _errors(d) if "data_points" in e.message and "int16" in e.message]
    assert es == []


def test_r90_non_chart_not_checked():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi"}])
    es = [e for e in _errors(d) if "data_points" in e.message and "int16" in e.message]
    assert es == []


def test_r90_data_points_multiple_overflow():
    d = _make([{"type": "chart", "x": 0, "y": 0, "width": 40, "height": 30,
                "data_points": [40000, -50000, 32768], "style": "bar"}])
    es = [e for e in _errors(d) if "data_points" in e.message and "int16" in e.message]
    assert len(es) == 1  # single error with up to 3 values listed
