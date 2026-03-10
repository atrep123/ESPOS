"""Tests for validation rules 59-66 in tools/validate_design.py."""

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


# ── Rule 59: font_size must be positive int if present ─────────────────


def test_r59_font_size_valid():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "font_size": 8}])
    errs = [e for e in _errors(d) if "font_size" in e.message]
    assert errs == []


def test_r59_font_size_none_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "font_size": None}])
    errs = [e for e in _errors(d) if "font_size" in e.message]
    assert errs == []


def test_r59_font_size_zero():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "font_size": 0}])
    errs = [e for e in _errors(d) if "font_size" in e.message]
    assert len(errs) == 1


def test_r59_font_size_negative():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "font_size": -1}])
    errs = [e for e in _errors(d) if "font_size" in e.message]
    assert len(errs) == 1


def test_r59_font_size_string():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "font_size": "big"}])
    errs = [e for e in _errors(d) if "font_size" in e.message]
    assert len(errs) == 1


def test_r59_font_size_bool():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "font_size": True}])
    errs = [e for e in _errors(d) if "font_size" in e.message]
    assert len(errs) == 1


# ── Rule 60: corner_radius must be non-negative int if present ─────────


def test_r60_corner_radius_valid():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "corner_radius": 4}])
    errs = [e for e in _errors(d) if "corner_radius" in e.message]
    assert errs == []


def test_r60_corner_radius_zero_ok():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "corner_radius": 0}])
    errs = [e for e in _errors(d) if "corner_radius" in e.message]
    assert errs == []


def test_r60_corner_radius_none_ok():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "corner_radius": None}])
    errs = [e for e in _errors(d) if "corner_radius" in e.message]
    assert errs == []


def test_r60_corner_radius_negative():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "corner_radius": -1}])
    errs = [e for e in _errors(d) if "corner_radius" in e.message]
    assert len(errs) == 1


def test_r60_corner_radius_string():
    d = _make(
        [{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "corner_radius": "round"}]
    )
    errs = [e for e in _errors(d) if "corner_radius" in e.message]
    assert len(errs) == 1


def test_r60_corner_radius_float():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "corner_radius": 2.5}])
    errs = [e for e in _errors(d) if "corner_radius" in e.message]
    assert len(errs) == 1


# ── Rule 61: border_width must be non-negative int if present ──────────


def test_r61_border_width_valid():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "border_width": 2}])
    errs = [e for e in _errors(d) if "border_width" in e.message]
    assert errs == []


def test_r61_border_width_zero_ok():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "border_width": 0}])
    errs = [e for e in _errors(d) if "border_width" in e.message]
    assert errs == []


def test_r61_border_width_none_ok():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "border_width": None}])
    errs = [e for e in _errors(d) if "border_width" in e.message]
    assert errs == []


def test_r61_border_width_negative():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "border_width": -1}])
    errs = [e for e in _errors(d) if "border_width" in e.message]
    assert len(errs) == 1


def test_r61_border_width_string():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "border_width": "thick"}])
    errs = [e for e in _errors(d) if "border_width" in e.message]
    assert len(errs) == 1


# ── Rule 62: border_color parseable ────────────────────────────────────


def test_r62_border_color_valid_hex():
    d = _make(
        [{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "border_color": "#ff0000"}]
    )
    ws = [w for w in _warns(d) if "border_color" in w.message]
    assert ws == []


def test_r62_border_color_valid_named():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "border_color": "white"}])
    ws = [w for w in _warns(d) if "border_color" in w.message]
    assert ws == []


def test_r62_border_color_empty_ok():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "border_color": ""}])
    ws = [w for w in _warns(d) if "border_color" in w.message]
    assert ws == []


def test_r62_border_color_invalid():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "border_color": "nope"}])
    ws = [w for w in _warns(d) if "border_color" in w.message]
    assert len(ws) == 1


def test_r62_border_color_bad_hex():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "border_color": "#xyz"}])
    ws = [w for w in _warns(d) if "border_color" in w.message]
    assert len(ws) == 1


# ── Rule 63: Widget mostly outside scene (>75% area outside) ──────────


def test_r63_fully_inside_no_warn():
    d = _make([{"type": "box", "x": 10, "y": 10, "width": 20, "height": 20}])
    ws = [w for w in _warns(d) if "visible inside" in w.message]
    assert ws == []


def test_r63_mostly_outside_right():
    # 128-120=8 visible, total 40. 8*20=160 / 40*20=800 = 20% visible → warn
    d = _make([{"type": "box", "x": 120, "y": 0, "width": 40, "height": 20}])
    ws = [w for w in _warns(d) if "visible inside" in w.message]
    assert len(ws) == 1


def test_r63_mostly_outside_bottom():
    # 64-55=9 visible, total 40. 20*9=180 / 20*40=800 = 22.5% visible → warn
    d = _make([{"type": "box", "x": 0, "y": 55, "width": 20, "height": 40}])
    ws = [w for w in _warns(d) if "visible inside" in w.message]
    assert len(ws) == 1


def test_r63_half_visible_no_warn():
    # 128-100=28 visible, total 56. 28*20=560 / 56*20=1120 = 50% → no warn
    d = _make([{"type": "box", "x": 100, "y": 0, "width": 56, "height": 20}])
    ws = [w for w in _warns(d) if "visible inside" in w.message]
    assert ws == []


def test_r63_completely_outside():
    d = _make([{"type": "box", "x": 200, "y": 200, "width": 20, "height": 20}])
    ws = [w for w in _warns(d) if "visible inside" in w.message]
    assert ws == []


# ── Rule 64: bold field must be bool ───────────────────────────────────


def test_r64_bold_true_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "bold": True}])
    errs = [e for e in _errors(d) if "bold" in e.message]
    assert errs == []


def test_r64_bold_false_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "bold": False}])
    errs = [e for e in _errors(d) if "bold" in e.message]
    assert errs == []


def test_r64_bold_int():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "bold": 1}])
    errs = [e for e in _errors(d) if "bold" in e.message]
    assert len(errs) == 1


def test_r64_bold_string():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "bold": "yes"}])
    errs = [e for e in _errors(d) if "bold" in e.message]
    assert len(errs) == 1


# ── Rule 65: Duplicate geometry ────────────────────────────────────────


def test_r65_unique_geometry_no_warn():
    d = _make(
        [
            {"type": "label", "x": 0, "y": 0, "width": 60, "height": 14},
            {"type": "label", "x": 10, "y": 0, "width": 60, "height": 14},
        ]
    )
    ws = [w for w in _warns(d) if "identical geometry" in w.message]
    assert ws == []


def test_r65_duplicate_geometry_warns():
    d = _make(
        [
            {"type": "label", "x": 0, "y": 0, "width": 60, "height": 14},
            {"type": "button", "x": 0, "y": 0, "width": 60, "height": 14},
        ]
    )
    ws = [w for w in _warns(d) if "identical geometry" in w.message]
    assert len(ws) == 1


def test_r65_triple_duplicate():
    d = _make(
        [
            {"type": "label", "x": 5, "y": 5, "width": 20, "height": 20},
            {"type": "box", "x": 5, "y": 5, "width": 20, "height": 20},
            {"type": "button", "x": 5, "y": 5, "width": 20, "height": 20},
        ]
    )
    ws = [w for w in _warns(d) if "identical geometry" in w.message]
    assert len(ws) == 1  # single warning listing all indices


# ── Rule 66: Disabled with no runtime ──────────────────────────────────


def test_r66_enabled_no_warn():
    d = _make([{"type": "button", "x": 0, "y": 0, "width": 40, "height": 14, "enabled": True}])
    ws = [w for w in _warns(d) if "disabled" in w.message]
    assert ws == []


def test_r66_disabled_no_runtime_warns():
    d = _make(
        [
            {
                "type": "button",
                "x": 0,
                "y": 0,
                "width": 40,
                "height": 14,
                "enabled": False,
                "text": "OFF",
            }
        ]
    )
    ws = [w for w in _warns(d) if "disabled" in w.message and "runtime" in w.message]
    assert len(ws) == 1


def test_r66_disabled_with_runtime_ok():
    d = _make(
        [
            {
                "type": "button",
                "x": 0,
                "y": 0,
                "width": 40,
                "height": 14,
                "enabled": False,
                "runtime": "enabled=sys.ready",
            }
        ]
    )
    ws = [w for w in _warns(d) if "disabled" in w.message and "runtime" in w.message]
    assert ws == []


def test_r66_disabled_and_hidden_no_warn():
    d = _make(
        [
            {
                "type": "button",
                "x": 0,
                "y": 0,
                "width": 40,
                "height": 14,
                "enabled": False,
                "visible": False,
            }
        ]
    )
    ws = [w for w in _warns(d) if "disabled" in w.message and "runtime" in w.message]
    assert ws == []
