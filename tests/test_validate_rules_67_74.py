"""Tests for validation rules 67-74 in tools/validate_design.py."""

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


# ── Rule 67: theme_fg_role / theme_bg_role must be string ──────────────


def test_r67_theme_fg_role_string_ok():
    d = _make(
        [{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "theme_fg_role": "primary"}]
    )
    errs = [e for e in _errors(d) if "theme_fg_role" in e.message]
    assert errs == []


def test_r67_theme_fg_role_none_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "theme_fg_role": None}])
    errs = [e for e in _errors(d) if "theme_fg_role" in e.message]
    assert errs == []


def test_r67_theme_fg_role_int():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "theme_fg_role": 42}])
    errs = [e for e in _errors(d) if "theme_fg_role" in e.message]
    assert len(errs) == 1


def test_r67_theme_fg_role_bool():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "theme_fg_role": True}])
    errs = [e for e in _errors(d) if "theme_fg_role" in e.message]
    assert len(errs) == 1


def test_r67_theme_bg_role_string_ok():
    d = _make(
        [{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "theme_bg_role": "surface"}]
    )
    errs = [e for e in _errors(d) if "theme_bg_role" in e.message]
    assert errs == []


def test_r67_theme_bg_role_list():
    d = _make(
        [{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "theme_bg_role": ["bg"]}]
    )
    errs = [e for e in _errors(d) if "theme_bg_role" in e.message]
    assert len(errs) == 1


# ── Rule 68: state field must be a string ──────────────────────────────


def test_r68_state_string_ok():
    d = _make([{"type": "button", "x": 0, "y": 0, "width": 60, "height": 14, "state": "pressed"}])
    errs = [e for e in _errors(d) if "state=" in e.message]
    assert errs == []


def test_r68_state_none_ok():
    d = _make([{"type": "button", "x": 0, "y": 0, "width": 60, "height": 14, "state": None}])
    errs = [e for e in _errors(d) if "state=" in e.message]
    assert errs == []


def test_r68_state_int():
    d = _make([{"type": "button", "x": 0, "y": 0, "width": 60, "height": 14, "state": 1}])
    errs = [e for e in _errors(d) if "state=" in e.message]
    assert len(errs) == 1


def test_r68_state_list():
    d = _make([{"type": "button", "x": 0, "y": 0, "width": 60, "height": 14, "state": ["default"]}])
    errs = [e for e in _errors(d) if "state=" in e.message]
    assert len(errs) == 1


# ── Rule 69: max_lines=0 warning ──────────────────────────────────────


def test_r69_max_lines_positive_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "max_lines": 3}])
    ws = [w for w in _warns(d) if "max_lines" in w.message]
    assert ws == []


def test_r69_max_lines_zero_warn():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "max_lines": 0}])
    ws = [w for w in _warns(d) if "max_lines" in w.message]
    assert len(ws) == 1


def test_r69_max_lines_none_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "max_lines": None}])
    ws = [w for w in _warns(d) if "max_lines" in w.message]
    assert ws == []


# ── Rule 70: text_color / bg_color / color must be parseable ──────────


def test_r70_text_color_valid_hex():
    d = _make(
        [{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "text_color": "#ff0000"}]
    )
    errs = [e for e in _errors(d) if "text_color" in e.message]
    assert errs == []


def test_r70_text_color_invalid():
    d = _make(
        [{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "text_color": "banana"}]
    )
    errs = [e for e in _errors(d) if "text_color" in e.message]
    assert len(errs) == 1


def test_r70_bg_color_valid():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "bg_color": "black"}])
    errs = [e for e in _errors(d) if "bg_color" in e.message]
    assert errs == []


def test_r70_bg_color_invalid():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "bg_color": "neon"}])
    errs = [e for e in _errors(d) if "bg_color" in e.message]
    assert len(errs) == 1


def test_r70_color_alias_valid():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "color": "#aabbcc"}])
    errs = [e for e in _errors(d) if "color=" in e.message]
    assert errs == []


def test_r70_color_alias_invalid():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "color": "rainbow"}])
    errs = [e for e in _errors(d) if "color=" in e.message]
    assert len(errs) == 1


def test_r70_none_color_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "text_color": None}])
    errs = [e for e in _errors(d) if "text_color" in e.message]
    assert errs == []


def test_r70_empty_string_color_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "bg_color": ""}])
    errs = [e for e in _errors(d) if "bg_color" in e.message]
    assert errs == []


# ── Rule 71: max_lines excessively large ──────────────────────────────


def test_r71_max_lines_normal():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "max_lines": 5}])
    ws = [w for w in _warns(d) if "max_lines" in w.message and "excessive" in w.message]
    assert ws == []


def test_r71_max_lines_100_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "max_lines": 100}])
    ws = [w for w in _warns(d) if "max_lines" in w.message and "excessive" in w.message]
    assert ws == []


def test_r71_max_lines_101_warn():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "max_lines": 101}])
    ws = [w for w in _warns(d) if "max_lines" in w.message and "excessive" in w.message]
    assert len(ws) == 1


def test_r71_max_lines_9999_warn():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "max_lines": 9999}])
    ws = [w for w in _warns(d) if "max_lines" in w.message and "excessive" in w.message]
    assert len(ws) == 1


# ── Rule 72: text + runtime conflict ─────────────────────────────────


def test_r72_text_only_no_warn():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "text": "HI"}])
    ws = [w for w in _warns(d) if "runtime may override" in w.message]
    assert ws == []


def test_r72_runtime_only_no_warn():
    d = _make(
        [{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "runtime": "bind=x;kind=str"}]
    )
    ws = [w for w in _warns(d) if "runtime may override" in w.message]
    assert ws == []


def test_r72_text_and_runtime_warn():
    d = _make(
        [
            {
                "type": "label",
                "x": 0,
                "y": 0,
                "width": 60,
                "height": 14,
                "text": "HELLO",
                "runtime": "bind=x;kind=str",
            }
        ]
    )
    ws = [w for w in _warns(d) if "runtime may override" in w.message]
    assert len(ws) == 1


def test_r72_non_text_type_no_warn():
    d = _make(
        [
            {
                "type": "gauge",
                "x": 0,
                "y": 0,
                "width": 40,
                "height": 40,
                "text": "X",
                "runtime": "bind=v;kind=int;min=0;max=100",
                "value": 0,
                "min_value": 0,
                "max_value": 100,
            }
        ]
    )
    ws = [w for w in _warns(d) if "runtime may override" in w.message]
    assert ws == []


# ── Rule 73: icon widget too small for icon_char ──────────────────────


def test_r73_icon_sufficient_size():
    d = _make([{"type": "icon", "x": 0, "y": 0, "width": 10, "height": 10, "icon_char": "A"}])
    ws = [
        w
        for w in _warns(d)
        if "too small" in w.message and "icon" in w.message and "min 6" in w.message
    ]
    assert ws == []


def test_r73_icon_too_narrow():
    d = _make([{"type": "icon", "x": 0, "y": 0, "width": 4, "height": 10, "icon_char": "A"}])
    ws = [
        w
        for w in _warns(d)
        if "too small" in w.message and "icon" in w.message and "min 6" in w.message
    ]
    assert len(ws) == 1


def test_r73_icon_too_short():
    d = _make([{"type": "icon", "x": 0, "y": 0, "width": 10, "height": 6, "icon_char": "A"}])
    ws = [
        w
        for w in _warns(d)
        if "too small" in w.message and "icon" in w.message and "min 6" in w.message
    ]
    assert len(ws) == 1


def test_r73_non_icon_small_ok():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 4, "height": 4}])
    ws = [w for w in _warns(d) if "too small" in w.message and "icon" in w.message]
    assert ws == []


# ── Rule 74: padding larger than widget interior ──────────────────────


def test_r74_padding_x_ok():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 40, "height": 20, "padding_x": 5}])
    ws = [w for w in _warns(d) if "padding_x" in w.message]
    assert ws == []


def test_r74_padding_x_fills_width():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "padding_x": 10}])
    ws = [w for w in _warns(d) if "padding_x" in w.message]
    assert len(ws) == 1


def test_r74_padding_x_exceeds_width():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "padding_x": 15}])
    ws = [w for w in _warns(d) if "padding_x" in w.message]
    assert len(ws) == 1


def test_r74_padding_y_ok():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 40, "height": 20, "padding_y": 5}])
    ws = [w for w in _warns(d) if "padding_y" in w.message]
    assert ws == []


def test_r74_padding_y_fills_height():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 40, "height": 20, "padding_y": 10}])
    ws = [w for w in _warns(d) if "padding_y" in w.message]
    assert len(ws) == 1


def test_r74_padding_y_exceeds_height():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 40, "height": 20, "padding_y": 15}])
    ws = [w for w in _warns(d) if "padding_y" in w.message]
    assert len(ws) == 1
