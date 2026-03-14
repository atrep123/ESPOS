"""Targeted tests for every rule in tools/validate_design.py.

Each rule is tested by constructing a minimal JSON fixture that deliberately
trips the rule, then asserting the expected issue is reported.
"""

from tools.validate_design import validate_data

FL = "test"  # file_label used in all calls


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


# ── Rule 1: Duplicate widget IDs ──


def test_rule1_duplicate_ids():
    w = [
        {"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "_widget_id": "lbl1"},
        {"type": "label", "x": 0, "y": 20, "width": 40, "height": 14, "_widget_id": "lbl1"},
    ]
    errs = _errors(_make(w))
    assert any("duplicate" in e.message.lower() for e in errs)


def test_rule1_unique_ids_no_error():
    w = [
        {"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "_widget_id": "a"},
        {"type": "label", "x": 0, "y": 20, "width": 40, "height": 14, "_widget_id": "b"},
    ]
    errs = _errors(_make(w))
    assert not any("duplicate" in e.message.lower() for e in errs)


# ── Rule 2: Valid widget type ──


def test_rule2_unsupported_type():
    w = [{"type": "foobar", "x": 0, "y": 0, "width": 10, "height": 10}]
    errs = _errors(_make(w))
    assert any("unsupported type" in e.message.lower() for e in errs)


def test_rule2_missing_type():
    w = [{"x": 0, "y": 0, "width": 10, "height": 10}]
    errs = _errors(_make(w))
    assert any("missing" in e.message.lower() and "type" in e.message.lower() for e in errs)


def test_rule2_empty_type():
    w = [{"type": "", "x": 0, "y": 0, "width": 10, "height": 10}]
    errs = _errors(_make(w))
    assert any("missing" in e.message.lower() or "invalid" in e.message.lower() for e in errs)


# ── Rule 3: Positive dimensions ──


def test_rule3_zero_dimensions():
    w = [{"type": "box", "x": 0, "y": 0, "width": 0, "height": 10}]
    errs = _errors(_make(w))
    assert any("must be >= 1x1" in e.message for e in errs)


def test_rule3_negative_dimension():
    w = [{"type": "box", "x": 0, "y": 0, "width": -5, "height": 10}]
    errs = _errors(_make(w))
    assert any("must be >= 1x1" in e.message for e in errs)


# ── Rule 4: Within scene bounds ──


def test_rule4_out_of_bounds():
    w = [{"type": "box", "x": 100, "y": 50, "width": 50, "height": 20}]
    warns = _warns(_make(w, scene_w=128, scene_h=64))
    assert any("out of bounds" in i.message.lower() for i in warns)


def test_rule4_negative_origin():
    w = [{"type": "box", "x": -5, "y": 0, "width": 10, "height": 10}]
    errs = _errors(_make(w))
    assert any("negative" in e.message.lower() for e in errs)


def test_rule4_within_bounds_no_issue():
    w = [{"type": "box", "x": 0, "y": 0, "width": 40, "height": 30}]
    issues = _issues(_make(w))
    assert not any("out of bounds" in i.message.lower() for i in issues)
    assert not any("negative" in i.message.lower() for i in issues)


# ── Rule 5: Integer coordinates ──


def test_rule5_float_x():
    w = [{"type": "box", "x": 1.5, "y": 0, "width": 10, "height": 10}]
    errs = _errors(_make(w))
    assert any("must be int" in e.message for e in errs)


def test_rule5_string_width():
    w = [{"type": "box", "x": 0, "y": 0, "width": "10", "height": 10}]
    errs = _errors(_make(w))
    assert any("must be int" in e.message for e in errs)


def test_rule5_bool_not_int():
    w = [{"type": "box", "x": 0, "y": 0, "width": True, "height": 10}]
    errs = _errors(_make(w))
    assert any("must be int" in e.message for e in errs)


# ── Rule 6: Minimum height for text types ──


def test_rule6_label_too_short():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 8}]
    warns = _warns(_make(w))
    assert any("min" in i.message.lower() and "text widget" in i.message.lower() for i in warns)


def test_rule6_label_ok_height():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14}]
    warns = _warns(_make(w))
    assert not any("text widget" in i.message.lower() for i in warns)


def test_rule6_box_not_text_type():
    # box is not a text type, so no min-height warning
    w = [{"type": "box", "x": 0, "y": 0, "width": 40, "height": 5}]
    warns = _warns(_make(w))
    assert not any("text widget" in i.message.lower() for i in warns)


# ── Rule 7: Text overflow (H+V) ──


def test_rule7_text_overflow_horizontal():
    # 40px wide → inner = 40-4 = 36px → 36/6 = 6 chars max
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "text": "ABCDEFGHIJ"}]
    warns = _warns(_make(w))
    assert any("chars" in i.message.lower() or "ch)" in i.message for i in warns)


def test_rule7_text_fits():
    w = [{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "text": "ABC"}]
    warns = _warns(_make(w))
    assert not any("chars" in i.message.lower() and "ch)" in i.message for i in warns)


# ── Rule 8: Minimum widget width for text types ──


def test_rule8_too_narrow_for_text():
    # min_w = 2*2 + 6 = 10
    w = [{"type": "label", "x": 0, "y": 0, "width": 8, "height": 14, "text": "A"}]
    warns = _warns(_make(w))
    assert any("can't fit" in i.message.lower() or "min" in i.message.lower() for i in warns)


# ── Rule 9: Value range sanity ──


def test_rule9_min_ge_max():
    w = [
        {
            "type": "gauge",
            "x": 0,
            "y": 0,
            "width": 30,
            "height": 30,
            "min_value": 100,
            "max_value": 50,
        }
    ]
    errs = _errors(_make(w))
    assert any("min_value" in e.message and "max_value" in e.message for e in errs)


def test_rule9_value_out_of_range():
    w = [
        {
            "type": "slider",
            "x": 0,
            "y": 0,
            "width": 60,
            "height": 14,
            "min_value": 0,
            "max_value": 100,
            "value": 200,
        }
    ]
    warns = _warns(_make(w))
    assert any("value=" in i.message for i in warns)


def test_rule9_valid_range_no_issue():
    w = [
        {
            "type": "gauge",
            "x": 0,
            "y": 0,
            "width": 30,
            "height": 30,
            "min_value": 0,
            "max_value": 100,
            "value": 50,
        }
    ]
    issues = _issues(_make(w))
    assert not any("min_value" in i.message or "value=" in i.message for i in issues)


# ── Rule 11: Valid align/valign ──


def test_rule11_invalid_align():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "align": "justify"}]
    errs = _errors(_make(w))
    assert any("invalid align" in e.message.lower() for e in errs)


def test_rule11_invalid_valign():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "valign": "stretch"}]
    errs = _errors(_make(w))
    assert any("invalid valign" in e.message.lower() for e in errs)


def test_rule11_valid_align():
    w = [
        {
            "type": "label",
            "x": 0,
            "y": 0,
            "width": 40,
            "height": 14,
            "align": "center",
            "valign": "middle",
        }
    ]
    errs = _errors(_make(w))
    assert not any("align" in e.message.lower() for e in errs)


# ── Rule 12: Valid border_style ──


def test_rule12_invalid_border_style():
    w = [{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "border_style": "wavy"}]
    errs = _errors(_make(w))
    assert any("invalid border_style" in e.message.lower() for e in errs)


def test_rule12_valid_border_style():
    for bs in ("single", "double", "rounded", "bold", "dashed", "none"):
        w = [{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "border_style": bs}]
        errs = _errors(_make(w))
        assert not any("border_style" in e.message.lower() for e in errs), (
            f"failed for style '{bs}'"
        )


# ── Rule 13: border=True requires visible border_style ──


def test_rule13_border_true_none_style():
    w = [
        {
            "type": "box",
            "x": 0,
            "y": 0,
            "width": 20,
            "height": 20,
            "border": True,
            "border_style": "none",
        }
    ]
    warns = _warns(_make(w))
    assert any("border=true" in i.message.lower() for i in warns)


def test_rule13_border_true_with_style():
    w = [
        {
            "type": "box",
            "x": 0,
            "y": 0,
            "width": 20,
            "height": 20,
            "border": True,
            "border_style": "single",
        }
    ]
    warns = _warns(_make(w))
    assert not any("border=true" in i.message.lower() for i in warns)


# ── Rule 14: Valid text_overflow ──


def test_rule14_invalid_text_overflow():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "text_overflow": "scroll"}]
    errs = _errors(_make(w))
    assert any("invalid text_overflow" in e.message.lower() for e in errs)


def test_rule14_valid_text_overflow():
    for ov in ("ellipsis", "wrap", "clip", "auto"):
        w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "text_overflow": ov}]
        errs = _errors(_make(w))
        assert not any("text_overflow" in e.message.lower() for e in errs), f"failed for '{ov}'"


# ── Rule 15: Foreground color parseable + visibility ──


def test_rule15_unparseable_fg():
    w = [
        {
            "type": "label",
            "x": 0,
            "y": 0,
            "width": 40,
            "height": 14,
            "text": "HI",
            "color_fg": "rgb(1,2,3)",
        }
    ]
    warns = _warns(_make(w))
    assert any("can't parse color_fg" in i.message.lower() for i in warns)


def test_rule15_dim_fg():
    # Brightness of #050505 ≈ 5, below MIN_VISIBLE_BRIGHTNESS (0x20=32)
    w = [
        {
            "type": "label",
            "x": 0,
            "y": 0,
            "width": 40,
            "height": 14,
            "text": "HI",
            "color_fg": "#050505",
        }
    ]
    warns = _warns(_make(w))
    assert any("too dim" in i.message.lower() for i in warns)


def test_rule15_bright_fg_no_warning():
    w = [
        {
            "type": "label",
            "x": 0,
            "y": 0,
            "width": 40,
            "height": 14,
            "text": "HI",
            "color_fg": "#ffffff",
        }
    ]
    warns = _warns(_make(w))
    assert not any("too dim" in i.message.lower() for i in warns)


# ── Rule 16: Background color parseable ──


def test_rule16_unparseable_bg():
    w = [{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "color_bg": "invalid!"}]
    warns = _warns(_make(w))
    assert any("can't parse color_bg" in i.message.lower() for i in warns)


def test_rule16_valid_bg():
    w = [{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "color_bg": "#303030"}]
    warns = _warns(_make(w))
    assert not any("color_bg" in i.message.lower() for i in warns)


# ── Rule 17: Contrast check ──


def test_rule17_low_contrast():
    w = [
        {
            "type": "label",
            "x": 0,
            "y": 0,
            "width": 60,
            "height": 14,
            "text": "HI",
            "color_fg": "#808080",
            "color_bg": "#7a7a7a",
        }
    ]
    warns = _warns(_make(w))
    assert any("low contrast" in i.message.lower() for i in warns)


def test_rule17_good_contrast():
    w = [
        {
            "type": "label",
            "x": 0,
            "y": 0,
            "width": 60,
            "height": 14,
            "text": "HI",
            "color_fg": "#ffffff",
            "color_bg": "#000000",
        }
    ]
    warns = _warns(_make(w))
    assert not any("contrast" in i.message.lower() for i in warns)


# ── Rule 18: Minimum gauge/slider/progressbar size ──


def test_rule18_gauge_too_small():
    w = [{"type": "gauge", "x": 0, "y": 0, "width": 5, "height": 5}]
    errs = _errors(_make(w))
    assert any("too small" in e.message.lower() for e in errs)


def test_rule18_slider_too_narrow():
    w = [{"type": "slider", "x": 0, "y": 0, "width": 10, "height": 14}]
    errs = _errors(_make(w))
    assert any("too narrow" in e.message.lower() for e in errs)


def test_rule18_progressbar_too_narrow():
    w = [{"type": "progressbar", "x": 0, "y": 0, "width": 5, "height": 14}]
    errs = _errors(_make(w))
    assert any("too narrow" in e.message.lower() for e in errs)


def test_rule18_gauge_ok_size():
    w = [{"type": "gauge", "x": 0, "y": 0, "width": 30, "height": 30}]
    errs = _errors(_make(w))
    assert not any("too small" in e.message.lower() for e in errs)


# ── Rule 19: z_index is an integer ──


def test_rule19_z_index_string():
    w = [{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "z_index": "top"}]
    errs = _errors(_make(w))
    assert any("z_index" in e.message for e in errs)


def test_rule19_z_index_int_ok():
    w = [{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "z_index": 5}]
    errs = _errors(_make(w))
    assert not any("z_index" in e.message for e in errs)


# ── Rule 20: Runtime string format ──


def test_rule20_runtime_missing_equals():
    w = [
        {
            "type": "label",
            "x": 0,
            "y": 0,
            "width": 40,
            "height": 14,
            "text": "T",
            "runtime": "speed",
        }
    ]
    errs = _errors(_make(w))
    assert any("runtime" in e.message.lower() and "missing '='" in e.message for e in errs)


def test_rule20_valid_runtime():
    w = [
        {
            "type": "label",
            "x": 0,
            "y": 0,
            "width": 40,
            "height": 14,
            "text": "T",
            "runtime": "text=speed_value",
        }
    ]
    errs = _errors(_make(w))
    assert not any("runtime" in e.message.lower() and "missing" in e.message for e in errs)


def test_rule20_multi_runtime():
    w = [
        {
            "type": "label",
            "x": 0,
            "y": 0,
            "width": 40,
            "height": 14,
            "text": "T",
            "runtime": "text=a;value=b",
        }
    ]
    errs = _errors(_make(w))
    assert not any("runtime" in e.message.lower() and "missing" in e.message for e in errs)


# ── Rule 21: Overlap detection ──


def test_rule21_overlapping_widgets():
    w = [
        {"type": "box", "x": 0, "y": 0, "width": 30, "height": 30},
        {"type": "box", "x": 10, "y": 10, "width": 30, "height": 30},
    ]
    warns = _warns(_make(w))
    assert any("overlap" in i.message.lower() for i in warns)


def test_rule21_no_overlap():
    w = [
        {"type": "box", "x": 0, "y": 0, "width": 10, "height": 10},
        {"type": "box", "x": 50, "y": 50, "width": 10, "height": 10},
    ]
    warns = _warns(_make(w))
    assert not any("overlap" in i.message.lower() for i in warns)


# ── Rule 22: Scene must not be empty ──


def test_rule22_empty_scene():
    warns = _warns(_make([]))
    assert any("0 widgets" in i.message for i in warns)


def test_rule22_non_empty_no_warning():
    w = [{"type": "box", "x": 0, "y": 0, "width": 10, "height": 10}]
    warns = _warns(_make(w))
    assert not any("0 widgets" in i.message for i in warns)


# ── Rule 24: Edge margin ──


def test_rule24_right_edge_too_close():
    # scene 128x64, widget at x=110, w=17 → right=127 > 128-2=126
    w = [{"type": "box", "x": 110, "y": 0, "width": 17, "height": 10}]
    errs = _errors(_make(w, scene_w=128, scene_h=64))
    assert any("right edge" in i.message.lower() or "boundary" in i.message.lower() for i in errs)


def test_rule24_bottom_edge_too_close():
    w = [{"type": "box", "x": 0, "y": 50, "width": 10, "height": 13}]
    errs = _errors(_make(w, scene_w=128, scene_h=64))
    assert any("bottom edge" in i.message.lower() or "boundary" in i.message.lower() for i in errs)


def test_rule24_full_span_no_warning():
    # Full-width widget (w==scene_w) should not trigger edge margin
    w = [{"type": "box", "x": 0, "y": 0, "width": 128, "height": 10}]
    warns = _warns(_make(w, scene_w=128, scene_h=64))
    errs = _errors(_make(w, scene_w=128, scene_h=64))
    assert not any("edge" in i.message.lower() and "boundary" in i.message.lower() for i in warns)
    assert not any("edge" in i.message.lower() and "boundary" in i.message.lower() for i in errs)


def test_rule24_left_edge_too_close():
    # x=1, which is < MIN_EDGE_MARGIN=2
    w = [{"type": "box", "x": 1, "y": 10, "width": 20, "height": 10}]
    errs = _errors(_make(w, scene_w=128, scene_h=64))
    assert any("left edge" in i.message.lower() for i in errs)


def test_rule24_top_edge_too_close():
    # y=1, which is < MIN_EDGE_MARGIN=2
    w = [{"type": "box", "x": 10, "y": 1, "width": 20, "height": 10}]
    errs = _errors(_make(w, scene_w=128, scene_h=64))
    assert any("top edge" in i.message.lower() for i in errs)


def test_rule24_flush_right_no_border_ok():
    # Non-bordered widget flush to right edge is allowed
    w = [
        {"type": "label", "x": 64, "y": 0, "width": 64, "height": 12, "text": "OK", "border": False}
    ]
    errs = _errors(_make(w, scene_w=128, scene_h=64))
    assert not any("right edge" in i.message.lower() for i in errs)


def test_rule24_flush_right_with_border_error():
    # Bordered widget flush to right edge is an error
    w = [
        {"type": "label", "x": 64, "y": 10, "width": 64, "height": 14, "text": "OK", "border": True}
    ]
    errs = _errors(_make(w, scene_w=128, scene_h=64))
    assert any("right edge" in i.message.lower() for i in errs)


# ── Rule 25: Text widget with no text and no runtime binding ──


def test_rule25_empty_text_no_runtime():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14}]
    warns = _warns(_make(w))
    assert any("no text" in i.message.lower() and "no runtime" in i.message.lower() for i in warns)


def test_rule25_empty_text_with_runtime():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "runtime": "text=val"}]
    warns = _warns(_make(w))
    assert not any(
        "no text" in i.message.lower() and "no runtime" in i.message.lower() for i in warns
    )


def test_rule25_has_text():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "text": "OK"}]
    warns = _warns(_make(w))
    assert not any(
        "no text" in i.message.lower() and "no runtime" in i.message.lower() for i in warns
    )


# ── Rule 26: Font charset compliance ──


def test_rule26_unsupported_chars():
    w = [{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "text": "café"}]
    warns = _warns(_make(w))
    assert any("unsupported char" in i.message.lower() for i in warns)


def test_rule26_supported_chars():
    w = [{"type": "label", "x": 0, "y": 0, "width": 60, "height": 14, "text": "HELLO 123"}]
    warns = _warns(_make(w))
    assert not any("unsupported char" in i.message.lower() for i in warns)


# ── Bool field validation ──


def test_bool_field_string_rejected():
    w = [{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "border": "yes"}]
    errs = _errors(_make(w))
    assert any("must be boolean" in e.message for e in errs)


# ── No scenes ──


def test_no_scenes():
    errs = _errors({"width": 128, "height": 64})
    assert any("no scenes" in e.message.lower() for e in errs)


# ── Invalid scene width/height ──


def test_scene_invalid_width():
    data = {"scenes": {"main": {"width": "big", "height": 64, "widgets": []}}}
    errs = _errors(data)
    assert any("width must be int" in e.message for e in errs)


# ── warnings_as_errors flag ──


def test_warnings_as_errors_promotes():
    data = _make([])  # empty scene → WARN
    plain = validate_data(data, file_label=FL, warnings_as_errors=False)
    promoted = validate_data(data, file_label=FL, warnings_as_errors=True)
    assert any(i.level == "WARN" for i in plain)
    assert all(i.level == "ERROR" for i in promoted)


# ── Rule 10: Firmware int16 overflow ──


def test_rule10_value_overflow():
    w = [{"type": "gauge", "x": 0, "y": 0, "width": 40, "height": 20, "value": 40000}]
    errs = _errors(_make(w))
    assert any("overflows int16" in e.message for e in errs)


def test_rule10_min_value_underflow():
    w = [{"type": "slider", "x": 0, "y": 0, "width": 40, "height": 20, "min_value": -40000}]
    errs = _errors(_make(w))
    assert any("overflows int16" in e.message for e in errs)


def test_rule10_max_value_overflow():
    w = [{"type": "progressbar", "x": 0, "y": 0, "width": 40, "height": 20, "max_value": 32768}]
    errs = _errors(_make(w))
    assert any("overflows int16" in e.message for e in errs)


def test_rule10_values_in_range_ok():
    w = [
        {
            "type": "gauge",
            "x": 0,
            "y": 0,
            "width": 40,
            "height": 20,
            "value": 0,
            "min_value": -32768,
            "max_value": 32767,
        }
    ]
    errs = _errors(_make(w))
    assert not any("overflows int16" in e.message for e in errs)


# ── Rule 23: Style field validation ──


def test_rule23_invalid_style():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "style": "neon"}]
    errs = _errors(_make(w))
    assert any("invalid style" in e.message for e in errs)


def test_rule23_valid_style_bold():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "style": "bold"}]
    errs = _errors(_make(w))
    assert not any("invalid style" in e.message for e in errs)


def test_rule23_valid_style_inverse():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "style": "inverse"}]
    errs = _errors(_make(w))
    assert not any("invalid style" in e.message for e in errs)


def test_rule23_valid_style_default():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "style": "default"}]
    errs = _errors(_make(w))
    assert not any("invalid style" in e.message for e in errs)


def test_rule23_valid_style_highlight():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "style": "highlight"}]
    errs = _errors(_make(w))
    assert not any("invalid style" in e.message for e in errs)


def test_rule23_style_not_string():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "style": 42}]
    errs = _errors(_make(w))
    assert any("invalid style" in e.message for e in errs)


def test_rule23_valid_chart_style_bar():
    w = [{"type": "chart", "x": 0, "y": 0, "width": 40, "height": 30, "style": "bar"}]
    errs = _errors(_make(w))
    assert not any("invalid style" in e.message for e in errs)


def test_rule23_valid_chart_style_line():
    w = [{"type": "chart", "x": 0, "y": 0, "width": 40, "height": 30, "style": "line"}]
    errs = _errors(_make(w))
    assert not any("invalid style" in e.message for e in errs)


# ── Rule 27: Widget ID format ──


def test_rule27_id_with_spaces():
    w = [{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "_widget_id": "my widget"}]
    errs = _errors(_make(w))
    assert any("invalid characters" in e.message for e in errs)


def test_rule27_id_with_special_chars():
    w = [{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "_widget_id": "w@#!"}]
    errs = _errors(_make(w))
    assert any("invalid characters" in e.message for e in errs)


def test_rule27_id_starts_with_digit():
    w = [{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "_widget_id": "123abc"}]
    errs = _errors(_make(w))
    assert any("invalid characters" in e.message for e in errs)


def test_rule27_valid_id():
    w = [{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "_widget_id": "my_widget_1"}]
    errs = _errors(_make(w))
    assert not any("invalid characters" in e.message for e in errs)


def test_rule27_valid_id_with_hyphen():
    w = [{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "_widget_id": "btn-ok"}]
    errs = _errors(_make(w))
    assert not any("invalid characters" in e.message for e in errs)


def test_rule27_valid_id_with_dots():
    w = [
        {"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "_widget_id": "status_bar.left"}
    ]
    errs = _errors(_make(w))
    assert not any("invalid characters" in e.message for e in errs)


# ── Rule 28: Chart data_points validation ──


def test_rule28_data_points_not_list():
    w = [{"type": "chart", "x": 0, "y": 0, "width": 40, "height": 30, "data_points": "1,2,3"}]
    errs = _errors(_make(w))
    assert any("data_points must be a list" in e.message for e in errs)


def test_rule28_data_points_non_numeric():
    w = [{"type": "chart", "x": 0, "y": 0, "width": 40, "height": 30, "data_points": [1, "abc", 3]}]
    errs = _errors(_make(w))
    assert any("non-numeric" in e.message for e in errs)


def test_rule28_data_points_bool_rejected():
    w = [{"type": "chart", "x": 0, "y": 0, "width": 40, "height": 30, "data_points": [True, 2]}]
    errs = _errors(_make(w))
    assert any("non-numeric" in e.message for e in errs)


def test_rule28_data_points_valid():
    w = [{"type": "chart", "x": 0, "y": 0, "width": 40, "height": 30, "data_points": [10, 20, 30]}]
    errs = _errors(_make(w))
    assert not any("data_points" in e.message for e in errs)


def test_rule28_data_points_none_ok():
    w = [{"type": "chart", "x": 0, "y": 0, "width": 40, "height": 30}]
    errs = _errors(_make(w))
    assert not any("data_points" in e.message for e in errs)


def test_rule28_data_points_float_ok():
    w = [{"type": "chart", "x": 0, "y": 0, "width": 40, "height": 30, "data_points": [1.5, 2.7]}]
    errs = _errors(_make(w))
    assert not any("data_points" in e.message for e in errs)


# ── Rule 29: Icon widget requires icon_char ──


def test_rule29_icon_no_char():
    w = [{"type": "icon", "x": 0, "y": 0, "width": 24, "height": 24}]
    warns = _warns(_make(w))
    assert any("icon_char" in i.message for i in warns)


def test_rule29_icon_empty_char():
    w = [{"type": "icon", "x": 0, "y": 0, "width": 24, "height": 24, "icon_char": ""}]
    warns = _warns(_make(w))
    assert any("icon_char" in i.message for i in warns)


def test_rule29_icon_with_char():
    w = [{"type": "icon", "x": 0, "y": 0, "width": 24, "height": 24, "icon_char": "A"}]
    warns = _warns(_make(w))
    assert not any("icon_char" in i.message for i in warns)


# ── Rule 30: Checkbox/radiobutton minimum size ──


def test_rule30_checkbox_too_small():
    w = [{"type": "checkbox", "x": 0, "y": 0, "width": 8, "height": 8}]
    warns = _warns(_make(w))
    assert any("too small" in i.message and "checkbox" in i.message for i in warns)


def test_rule30_radiobutton_too_small():
    w = [{"type": "radiobutton", "x": 0, "y": 0, "width": 9, "height": 12}]
    warns = _warns(_make(w))
    assert any("too small" in i.message and "radiobutton" in i.message for i in warns)


def test_rule30_checkbox_ok():
    w = [{"type": "checkbox", "x": 0, "y": 0, "width": 10, "height": 12}]
    warns = _warns(_make(w))
    assert not any("too small" in i.message and "checkbox" in i.message for i in warns)


def test_rule30_radiobutton_ok():
    w = [{"type": "radiobutton", "x": 0, "y": 0, "width": 12, "height": 12}]
    warns = _warns(_make(w))
    assert not any("too small" in i.message and "radiobutton" in i.message for i in warns)


# ── Rule 31: Non-negative padding/margin ──


def test_rule31_negative_padding_x():
    w = [{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "padding_x": -1}]
    errs = _errors(_make(w))
    assert any("padding_x" in e.message and ">= 0" in e.message for e in errs)


def test_rule31_negative_margin_y():
    w = [{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "margin_y": -5}]
    errs = _errors(_make(w))
    assert any("margin_y" in e.message and ">= 0" in e.message for e in errs)


def test_rule31_zero_padding_ok():
    w = [{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "padding_x": 0, "padding_y": 0}]
    errs = _errors(_make(w))
    assert not any("padding" in e.message and ">= 0" in e.message for e in errs)


def test_rule31_positive_margin_ok():
    w = [{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "margin_x": 4, "margin_y": 2}]
    errs = _errors(_make(w))
    assert not any("margin" in e.message and ">= 0" in e.message for e in errs)


# ── Rule 32: Value field type check ──


def test_rule32_value_float():
    w = [{"type": "gauge", "x": 0, "y": 0, "width": 40, "height": 20, "value": 3.14}]
    errs = _errors(_make(w))
    assert any("value=" in e.message and "must be int" in e.message for e in errs)


def test_rule32_min_value_string():
    w = [{"type": "slider", "x": 0, "y": 0, "width": 40, "height": 20, "min_value": "low"}]
    errs = _errors(_make(w))
    assert any("min_value=" in e.message and "must be int" in e.message for e in errs)


def test_rule32_max_value_bool():
    w = [{"type": "progressbar", "x": 0, "y": 0, "width": 40, "height": 20, "max_value": True}]
    errs = _errors(_make(w))
    assert any("max_value=" in e.message and "must be int" in e.message for e in errs)


def test_rule32_value_int_ok():
    w = [
        {
            "type": "gauge",
            "x": 0,
            "y": 0,
            "width": 40,
            "height": 20,
            "value": 50,
            "min_value": 0,
            "max_value": 100,
        }
    ]
    errs = _errors(_make(w))
    assert not any(
        "must be int" in e.message
        and ("value=" in e.message or "min_value=" in e.message or "max_value=" in e.message)
        for e in errs
    )


def test_rule32_non_value_type_ignored():
    """Labels with accidental value fields should not trigger rule 32."""
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "value": "text"}]
    errs = _errors(_make(w))
    assert not any("must be int" in e.message and "value=" in e.message for e in errs)


# ── Rule 33: Excessive widget count per scene ──


def test_rule33_too_many_widgets():
    widgets = [
        {"type": "box", "x": i % 16 * 8, "y": i // 16 * 8, "width": 8, "height": 8}
        for i in range(65)
    ]
    warns = _warns(_make(widgets, scene_w=256, scene_h=128))
    assert any("exceeds recommended max" in i.message for i in warns)


def test_rule33_within_limit():
    widgets = [{"type": "box", "x": i * 8, "y": 0, "width": 8, "height": 8} for i in range(10)]
    warns = _warns(_make(widgets))
    assert not any("exceeds recommended max" in i.message for i in warns)


def test_rule33_hard_limit_errors():
    """Exceeding HARD_WIDGET_LIMIT (256) produces ERROR, not just WARN."""
    widgets = [
        {"type": "box", "x": i % 32 * 8, "y": i // 32 * 8, "width": 8, "height": 8}
        for i in range(257)
    ]
    errs = _errors(_make(widgets, scene_w=256, scene_h=128))
    assert any("hard limit" in e.message for e in errs)


def test_rule21_skipped_above_hard_limit():
    """O(n^2) overlap checks are skipped when widget count exceeds hard limit."""
    widgets = [{"type": "box", "x": 0, "y": 0, "width": 10, "height": 10} for _ in range(257)]
    warns = _warns(_make(widgets, scene_w=256, scene_h=128))
    # All 257 widgets overlap at (0,0), but overlap detection should be skipped
    assert not any("OVERLAP" in w.message for w in warns)


# ── Rule 34: Slider minimum height ──


def test_rule34_slider_too_short():
    w = [{"type": "slider", "x": 0, "y": 0, "width": 40, "height": 8}]
    warns = _warns(_make(w))
    assert any("slider" in i.message and "too short" in i.message for i in warns)


def test_rule34_slider_height_ok():
    w = [{"type": "slider", "x": 0, "y": 0, "width": 40, "height": 14}]
    warns = _warns(_make(w))
    assert not any("slider" in i.message and "too short" in i.message for i in warns)


# ── Rule 35: Double border minimum size ──


def test_rule35_double_border_too_small():
    w = [{"type": "box", "x": 0, "y": 0, "width": 4, "height": 4, "border_style": "double"}]
    warns = _warns(_make(w))
    assert any("double border" in i.message and "5x5" in i.message for i in warns)


def test_rule35_double_border_small_height():
    w = [{"type": "box", "x": 0, "y": 0, "width": 10, "height": 3, "border_style": "double"}]
    warns = _warns(_make(w))
    assert any("double border" in i.message for i in warns)


def test_rule35_double_border_ok():
    w = [{"type": "box", "x": 0, "y": 0, "width": 10, "height": 10, "border_style": "double"}]
    warns = _warns(_make(w))
    assert not any("double border" in i.message for i in warns)


def test_rule35_single_border_no_warn():
    w = [{"type": "box", "x": 0, "y": 0, "width": 3, "height": 3, "border_style": "single"}]
    warns = _warns(_make(w))
    assert not any("double border" in i.message for i in warns)


# ── Rule 36: Scene name validation ──


def test_rule36_scene_name_empty():
    data = {"scenes": {"": {"width": 128, "height": 64, "widgets": []}}}
    warns = _warns(data)
    assert any("scene name" in i.message and "invalid" in i.message for i in warns)


def test_rule36_scene_name_spaces():
    data = {"scenes": {"my scene": {"width": 128, "height": 64, "widgets": []}}}
    warns = _warns(data)
    assert any("scene name" in i.message and "invalid" in i.message for i in warns)


def test_rule36_scene_name_special_chars():
    data = {"scenes": {"sc@ne!": {"width": 128, "height": 64, "widgets": []}}}
    warns = _warns(data)
    assert any("scene name" in i.message and "invalid" in i.message for i in warns)


def test_rule36_scene_name_valid():
    data = _make([], scene_name="main_menu")
    warns = _warns(data)
    assert not any("scene name" in i.message and "invalid" in i.message for i in warns)


def test_rule36_scene_name_starts_digit():
    data = {"scenes": {"123abc": {"width": 128, "height": 64, "widgets": []}}}
    warns = _warns(data)
    assert any("scene name" in i.message and "invalid" in i.message for i in warns)


# ── Rule 37: Animations field must be a list ──


def test_rule37_animations_not_list():
    w = [{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "animations": "fade"}]
    errs = _errors(_make(w))
    assert any("animations must be a list" in e.message for e in errs)


def test_rule37_animations_non_string_items():
    w = [{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "animations": ["fade", 42]}]
    errs = _errors(_make(w))
    assert any("non-string" in e.message for e in errs)


def test_rule37_animations_valid():
    w = [
        {"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "animations": ["fade", "slide"]}
    ]
    errs = _errors(_make(w))
    assert not any("animations" in e.message for e in errs)


def test_rule37_animations_empty_list_ok():
    w = [{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "animations": []}]
    errs = _errors(_make(w))
    assert not any("animations" in e.message for e in errs)


def test_rule37_animations_none_ok():
    w = [{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20, "animations": None}]
    errs = _errors(_make(w))
    assert not any("animations" in e.message for e in errs)


# ── Rule 38: Geometry uint16 overflow ──


def test_rule38_x_overflow():
    w = [{"type": "box", "x": 70000, "y": 0, "width": 10, "height": 10}]
    errs = _errors(_make(w, scene_w=100000, scene_h=100000))
    assert any("overflows uint16" in e.message and "x=" in e.message for e in errs)


def test_rule38_width_overflow():
    w = [{"type": "box", "x": 0, "y": 0, "width": 70000, "height": 10}]
    errs = _errors(_make(w, scene_w=100000, scene_h=100000))
    assert any("overflows uint16" in e.message and "width=" in e.message for e in errs)


def test_rule38_normal_values_ok():
    w = [{"type": "box", "x": 0, "y": 0, "width": 128, "height": 64}]
    errs = _errors(_make(w))
    assert not any("overflows uint16" in e.message for e in errs)


# ── Rule 39: Text length warning ──


def test_rule39_text_too_long():
    long_text = "A" * 128
    w = [{"type": "label", "x": 0, "y": 0, "width": 120, "height": 14, "text": long_text}]
    warns = _warns(_make(w))
    assert any("exceeds" in i.message and "127" in i.message for i in warns)


def test_rule39_text_within_limit():
    ok_text = "A" * 127
    w = [{"type": "label", "x": 0, "y": 0, "width": 120, "height": 14, "text": ok_text}]
    warns = _warns(_make(w))
    assert not any("exceeds" in i.message and "127" in i.message for i in warns)


def test_rule39_non_text_type_ignored():
    long_text = "A" * 200
    w = [{"type": "box", "x": 0, "y": 0, "width": 40, "height": 20, "text": long_text}]
    warns = _warns(_make(w))
    assert not any("exceeds" in i.message and "127" in i.message for i in warns)


# ── Rule 40: Runtime key validation ──


def test_rule40_runtime_bad_key():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "runtime": "123bad=val"}]
    warns = _warns(_make(w))
    assert any("runtime key" in i.message and "invalid" in i.message for i in warns)


def test_rule40_runtime_key_spaces():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "runtime": "my key=val"}]
    warns = _warns(_make(w))
    assert any("runtime key" in i.message and "invalid" in i.message for i in warns)


def test_rule40_runtime_valid_key():
    w = [
        {
            "type": "label",
            "x": 0,
            "y": 0,
            "width": 40,
            "height": 14,
            "runtime": "sensor.temp=format_temp",
        }
    ]
    warns = _warns(_make(w))
    assert not any("runtime key" in i.message and "invalid" in i.message for i in warns)


def test_rule40_runtime_multi_valid():
    w = [
        {
            "type": "label",
            "x": 0,
            "y": 0,
            "width": 40,
            "height": 14,
            "runtime": "text=get_val;value=get_num",
        }
    ]
    warns = _warns(_make(w))
    assert not any("runtime key" in i.message and "invalid" in i.message for i in warns)


# ── Rule 41: Completely invisible widget (fully off-screen) ──


def test_rule41_fully_offscreen():
    w = [{"type": "box", "x": 200, "y": 200, "width": 10, "height": 10}]
    warns = _warns(_make(w, scene_w=128, scene_h=64))
    assert any("fully outside" in i.message for i in warns)


def test_rule41_partially_visible_no_warn():
    w = [{"type": "box", "x": 120, "y": 50, "width": 20, "height": 20}]
    warns = _warns(_make(w, scene_w=128, scene_h=64))
    assert not any("fully outside" in i.message for i in warns)


def test_rule41_at_origin_ok():
    w = [{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20}]
    warns = _warns(_make(w))
    assert not any("fully outside" in i.message for i in warns)


# ── Rule 42: Hidden widget with runtime binding ──


def test_rule42_hidden_with_runtime():
    w = [
        {
            "type": "label",
            "x": 0,
            "y": 0,
            "width": 40,
            "height": 14,
            "visible": False,
            "runtime": "text=get_val",
        }
    ]
    warns = _warns(_make(w))
    assert any("hidden" in i.message and "runtime" in i.message for i in warns)


def test_rule42_visible_with_runtime_ok():
    w = [
        {
            "type": "label",
            "x": 0,
            "y": 0,
            "width": 40,
            "height": 14,
            "visible": True,
            "runtime": "text=get_val",
        }
    ]
    warns = _warns(_make(w))
    assert not any("hidden" in i.message and "runtime" in i.message for i in warns)


def test_rule42_hidden_no_runtime_ok():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "visible": False}]
    warns = _warns(_make(w))
    assert not any("hidden" in i.message and "runtime" in i.message for i in warns)
