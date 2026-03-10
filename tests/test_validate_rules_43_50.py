"""Tests for validation rules 43-50 in tools/validate_design.py."""

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


# ── Rule 43: locked must be boolean ──


def test_rule43_locked_string_error():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "locked": "yes"}]
    errs = _errors(_make(w))
    assert any("locked" in e.message and "boolean" in e.message for e in errs)


def test_rule43_locked_int_error():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "locked": 1}]
    errs = _errors(_make(w))
    assert any("locked" in e.message for e in errs)


def test_rule43_locked_bool_ok():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "locked": True}]
    errs = _errors(_make(w))
    assert not any("locked" in e.message for e in errs)


def test_rule43_locked_false_ok():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "locked": False}]
    errs = _errors(_make(w))
    assert not any("locked" in e.message for e in errs)


def test_rule43_no_locked_field_ok():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14}]
    errs = _errors(_make(w))
    assert not any("locked" in e.message for e in errs)


# ── Rule 44: state_overrides must be dict of dicts ──


def test_rule44_state_overrides_list_error():
    w = [
        {"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "state_overrides": ["a", "b"]}
    ]
    errs = _errors(_make(w))
    assert any("state_overrides must be a dict" in e.message for e in errs)


def test_rule44_state_overrides_string_error():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "state_overrides": "bad"}]
    errs = _errors(_make(w))
    assert any("state_overrides must be a dict" in e.message for e in errs)


def test_rule44_state_overrides_inner_not_dict():
    w = [
        {
            "type": "label",
            "x": 0,
            "y": 0,
            "width": 40,
            "height": 14,
            "state_overrides": {"hover": "red"},
        }
    ]
    errs = _errors(_make(w))
    assert any("state_overrides['hover']" in e.message for e in errs)


def test_rule44_state_overrides_valid():
    w = [
        {
            "type": "label",
            "x": 0,
            "y": 0,
            "width": 40,
            "height": 14,
            "state_overrides": {"hover": {"color_fg": "red"}},
        }
    ]
    errs = _errors(_make(w))
    assert not any("state_overrides" in e.message for e in errs)


def test_rule44_state_overrides_none_ok():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "state_overrides": None}]
    errs = _errors(_make(w))
    assert not any("state_overrides" in e.message for e in errs)


def test_rule44_no_state_overrides_ok():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14}]
    errs = _errors(_make(w))
    assert not any("state_overrides" in e.message for e in errs)


# ── Rule 45: Scene dimensions overflow uint16 ──


def test_rule45_scene_dim_overflow():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14}]
    errs = _errors(_make(w, scene_w=70000, scene_h=64))
    assert any("overflow uint16" in e.message for e in errs)


def test_rule45_scene_dim_height_overflow():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14}]
    errs = _errors(_make(w, scene_w=128, scene_h=70000))
    assert any("overflow uint16" in e.message for e in errs)


def test_rule45_scene_dim_max_ok():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14}]
    errs = _errors(_make(w, scene_w=65535, scene_h=65535))
    assert not any("overflow uint16" in e.message and "scene" in e.message.lower() for e in errs)


# ── Rule 46: Textbox minimum size ──


def test_rule46_textbox_too_small():
    w = [{"type": "textbox", "x": 0, "y": 0, "width": 10, "height": 8}]
    warns = _warns(_make(w))
    assert any("textbox" in i.message and "too small" in i.message for i in warns)


def test_rule46_textbox_ok():
    w = [{"type": "textbox", "x": 0, "y": 0, "width": 40, "height": 20}]
    warns = _warns(_make(w))
    assert not any("textbox" in i.message and "too small" in i.message for i in warns)


# ── Rule 47: Panel with no border and no bg ──


def test_rule47_panel_no_border_no_bg():
    w = [
        {
            "type": "panel",
            "x": 0,
            "y": 0,
            "width": 40,
            "height": 30,
            "border": False,
            "color_bg": "",
        }
    ]
    warns = _warns(_make(w))
    assert any("panel" in i.message and "no border" in i.message for i in warns)


def test_rule47_panel_with_border_ok():
    w = [
        {"type": "panel", "x": 0, "y": 0, "width": 40, "height": 30, "border": True, "color_bg": ""}
    ]
    warns = _warns(_make(w))
    assert not any("panel" in i.message and "no border" in i.message for i in warns)


def test_rule47_panel_with_bg_ok():
    w = [
        {
            "type": "panel",
            "x": 0,
            "y": 0,
            "width": 40,
            "height": 30,
            "border": False,
            "color_bg": "#333333",
        }
    ]
    warns = _warns(_make(w))
    assert not any("panel" in i.message and "no border" in i.message for i in warns)


def test_rule47_non_panel_no_warn():
    w = [
        {
            "type": "label",
            "x": 0,
            "y": 0,
            "width": 40,
            "height": 14,
            "border": False,
            "color_bg": "",
        }
    ]
    warns = _warns(_make(w))
    assert not any("panel" in i.message and "no border" in i.message for i in warns)


# ── Rule 48: z_index extreme range ──


def test_rule48_z_index_too_high():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "z_index": 500}]
    warns = _warns(_make(w))
    assert any("z_index" in i.message and "extreme" in i.message for i in warns)


def test_rule48_z_index_too_low():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "z_index": -200}]
    warns = _warns(_make(w))
    assert any("z_index" in i.message and "extreme" in i.message for i in warns)


def test_rule48_z_index_normal_ok():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "z_index": 5}]
    warns = _warns(_make(w))
    assert not any("z_index" in i.message and "extreme" in i.message for i in warns)


def test_rule48_z_index_boundary_ok():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "z_index": -100}]
    warns = _warns(_make(w))
    assert not any("z_index" in i.message and "extreme" in i.message for i in warns)


def test_rule48_z_index_boundary_high_ok():
    w = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "z_index": 200}]
    warns = _warns(_make(w))
    assert not any("z_index" in i.message and "extreme" in i.message for i in warns)


# ── Rule 49: Duplicate text in scene ──


def test_rule49_duplicate_text_4_times():
    w = [
        {"type": "label", "x": 0, "y": i * 16, "width": 40, "height": 14, "text": "Hello World"}
        for i in range(4)
    ]
    warns = _warns(_make(w))
    assert any("Hello World" in i.message and "4 times" in i.message for i in warns)


def test_rule49_duplicate_text_3_times_ok():
    w = [
        {"type": "label", "x": 0, "y": i * 16, "width": 40, "height": 14, "text": "Hello World"}
        for i in range(3)
    ]
    warns = _warns(_make(w))
    assert not any("Hello World" in i.message and "times" in i.message for i in warns)


def test_rule49_short_text_not_flagged():
    """Texts of 3 chars or fewer are excluded from duplicate check."""
    w = [
        {"type": "label", "x": 0, "y": i * 16, "width": 40, "height": 14, "text": "OK"}
        for i in range(5)
    ]
    warns = _warns(_make(w))
    assert not any("OK" in i.message and "times" in i.message for i in warns)


# ── Rule 50: icon_char length check ──


def test_rule50_icon_char_too_long():
    w = [{"type": "icon", "x": 0, "y": 0, "width": 20, "height": 20, "icon_char": "AB"}]
    warns = _warns(_make(w))
    assert any("icon_char" in i.message and "single character" in i.message for i in warns)


def test_rule50_icon_char_single_ok():
    w = [{"type": "icon", "x": 0, "y": 0, "width": 20, "height": 20, "icon_char": "A"}]
    warns = _warns(_make(w))
    assert not any("icon_char" in i.message and "single character" in i.message for i in warns)


def test_rule50_icon_char_empty_ok():
    w = [{"type": "icon", "x": 0, "y": 0, "width": 20, "height": 20, "icon_char": ""}]
    warns = _warns(_make(w))
    assert not any("icon_char" in i.message and "single character" in i.message for i in warns)
