"""Tests for validation rules 51-58 in tools/validate_design.py."""

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


# ── Rule 51: constraints must be a dict ──


def test_rule51_constraints_list_error():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "constraints": [1, 2]}]
    errs = _errors(_make(w))
    assert any("constraints must be a dict" in e.message for e in errs)


def test_rule51_constraints_string_error():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "constraints": "bad"}]
    errs = _errors(_make(w))
    assert any("constraints must be a dict" in e.message for e in errs)


def test_rule51_constraints_dict_ok():
    w = [
        {"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "constraints": {"ax": "left"}}
    ]
    errs = _errors(_make(w))
    assert not any("constraints" in e.message for e in errs)


def test_rule51_constraints_none_ok():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "constraints": None}]
    errs = _errors(_make(w))
    assert not any("constraints" in e.message for e in errs)


def test_rule51_no_constraints_ok():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14}]
    errs = _errors(_make(w))
    assert not any("constraints" in e.message for e in errs)


# ── Rule 52: responsive_rules must be a list ──


def test_rule52_responsive_rules_dict_error():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "responsive_rules": {"a": 1}}]
    errs = _errors(_make(w))
    assert any("responsive_rules must be a list" in e.message for e in errs)


def test_rule52_responsive_rules_string_error():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "responsive_rules": "bad"}]
    errs = _errors(_make(w))
    assert any("responsive_rules must be a list" in e.message for e in errs)


def test_rule52_responsive_rules_list_ok():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "responsive_rules": []}]
    errs = _errors(_make(w))
    assert not any("responsive_rules" in e.message for e in errs)


def test_rule52_responsive_rules_none_ok():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "responsive_rules": None}]
    errs = _errors(_make(w))
    assert not any("responsive_rules" in e.message for e in errs)


# ── Rule 53: parent_id references existing widget ──


def test_rule53_parent_id_missing_ref():
    w = [
        {
            "type": "label",
            "x": 0,
            "y": 0,
            "width": 40,
            "height": 14,
            "_widget_id": "lbl1",
            "parent_id": "panel99",
        },
    ]
    warns = _warns(_make(w))
    assert any("parent_id" in i.message and "not found" in i.message for i in warns)


def test_rule53_parent_id_valid_ref():
    w = [
        {"type": "panel", "x": 0, "y": 0, "width": 60, "height": 50, "_widget_id": "pnl1"},
        {
            "type": "label",
            "x": 2,
            "y": 2,
            "width": 40,
            "height": 14,
            "_widget_id": "lbl1",
            "parent_id": "pnl1",
        },
    ]
    warns = _warns(_make(w))
    assert not any("parent_id" in i.message and "not found" in i.message for i in warns)


def test_rule53_no_parent_id_ok():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14}]
    warns = _warns(_make(w))
    assert not any("parent_id" in i.message for i in warns)


# ── Rule 54: Center-aligned in narrow widget ──


def test_rule54_center_narrow():
    # CHAR_W=6, RENDER_PAD=2 → min = 6*3 + 2*2 = 22
    w = [
        {
            "type": "label",
            "x": 0,
            "y": 0,
            "width": 15,
            "height": 14,
            "align": "center",
            "text": "Hi",
        }
    ]
    warns = _warns(_make(w))
    assert any("center-aligned" in i.message and "narrow" in i.message for i in warns)


def test_rule54_center_wide_ok():
    w = [
        {
            "type": "label",
            "x": 0,
            "y": 0,
            "width": 40,
            "height": 14,
            "align": "center",
            "text": "Hi",
        }
    ]
    warns = _warns(_make(w))
    assert not any("center-aligned" in i.message and "narrow" in i.message for i in warns)


def test_rule54_left_aligned_narrow_ok():
    w = [
        {"type": "label", "x": 0, "y": 0, "width": 10, "height": 14, "align": "left", "text": "Hi"}
    ]
    warns = _warns(_make(w))
    assert not any("center-aligned" in i.message for i in warns)


# ── Rule 55: Widget ID max length ──


def test_rule55_id_too_long():
    long_id = "a" * 65
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "_widget_id": long_id}]
    warns = _warns(_make(w))
    assert any("exceeds 64" in i.message for i in warns)


def test_rule55_id_64_ok():
    ok_id = "a" * 64
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "_widget_id": ok_id}]
    warns = _warns(_make(w))
    assert not any("exceeds 64" in i.message for i in warns)


# ── Rule 56: data_points on non-chart widget ──


def test_rule56_data_points_on_label():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "data_points": [1, 2, 3]}]
    warns = _warns(_make(w))
    assert any("data_points on non-chart" in i.message for i in warns)


def test_rule56_data_points_on_chart_ok():
    w = [{"type": "chart", "x": 0, "y": 0, "width": 60, "height": 30, "data_points": [1, 2, 3]}]
    warns = _warns(_make(w))
    assert not any("data_points on non-chart" in i.message for i in warns)


def test_rule56_no_data_points_ok():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14}]
    warns = _warns(_make(w))
    assert not any("data_points on non-chart" in i.message for i in warns)


# ── Rule 57: value fields on non-value widget ──


def test_rule57_min_value_on_label():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "min_value": 5}]
    warns = _warns(_make(w))
    assert any("min_value on non-value" in i.message for i in warns)


def test_rule57_max_value_on_label():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "max_value": 50}]
    warns = _warns(_make(w))
    assert any("max_value on non-value" in i.message for i in warns)


def test_rule57_value_fields_on_gauge_ok():
    w = [
        {
            "type": "gauge",
            "x": 0,
            "y": 0,
            "width": 40,
            "height": 30,
            "min_value": 0,
            "max_value": 100,
        }
    ]
    warns = _warns(_make(w))
    assert not any("on non-value" in i.message for i in warns)


def test_rule57_zero_values_ok():
    """min_value=0 and max_value=0 are not flagged (default values)."""
    w = [
        {"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "min_value": 0, "max_value": 0}
    ]
    warns = _warns(_make(w))
    assert not any("on non-value" in i.message for i in warns)


# ── Rule 58: Negative dimensions ──


def test_rule58_negative_width():
    w = [{"type": "label", "x": 0, "y": 0, "width": -5, "height": 14}]
    errs = _errors(_make(w))
    assert any("negative dimension" in e.message or "must be >= 1x1" in e.message for e in errs)


def test_rule58_negative_height():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": -3}]
    errs = _errors(_make(w))
    assert any("negative dimension" in e.message or "must be >= 1x1" in e.message for e in errs)
