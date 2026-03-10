"""Tests for validation rules 91-98 in tools/validate_design.py."""

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


def _multi_scene(scenes_dict):
    return {"scenes": scenes_dict}


def _issues(data, **kw):
    return validate_data(data, file_label=FL, warnings_as_errors=False, **kw)


def _errors(data, **kw):
    return [i for i in _issues(data, **kw) if i.level == "ERROR"]


def _warns(data, **kw):
    return [i for i in _issues(data, **kw) if i.level == "WARN"]


# ── Rule 91: text field must be a string ──────────────────────────────


def test_r91_text_int_errors():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": 42}])
    es = [e for e in _errors(d) if "text=" in e.message and "must be a string" in e.message]
    assert len(es) == 1


def test_r91_text_list_errors():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": ["a", "b"]}])
    es = [e for e in _errors(d) if "text=" in e.message and "must be a string" in e.message]
    assert len(es) == 1


def test_r91_text_string_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hello"}])
    es = [e for e in _errors(d) if "text=" in e.message and "must be a string" in e.message]
    assert es == []


def test_r91_text_absent_ok():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 50, "height": 20}])
    es = [e for e in _errors(d) if "text=" in e.message and "must be a string" in e.message]
    assert es == []


def test_r91_text_none_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": None}])
    es = [e for e in _errors(d) if "text=" in e.message and "must be a string" in e.message]
    assert es == []


# ── Rule 92: valign on non-text widget ────────────────────────────────


def test_r92_valign_top_on_gauge_warns():
    d = _make([{"type": "gauge", "x": 0, "y": 0, "width": 40, "height": 20,
                "value": 50, "valign": "top"}])
    ws = [w for w in _warns(d) if "valign" in w.message and "non-text" in w.message]
    assert len(ws) == 1


def test_r92_valign_bottom_on_box_warns():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 40, "height": 20,
                "valign": "bottom"}])
    ws = [w for w in _warns(d) if "valign" in w.message and "non-text" in w.message]
    assert len(ws) == 1


def test_r92_valign_middle_on_gauge_ok():
    d = _make([{"type": "gauge", "x": 0, "y": 0, "width": 40, "height": 20,
                "value": 50, "valign": "middle"}])
    ws = [w for w in _warns(d) if "valign" in w.message and "non-text" in w.message]
    assert ws == []


def test_r92_valign_on_label_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi", "valign": "top"}])
    ws = [w for w in _warns(d) if "valign" in w.message and "non-text" in w.message]
    assert ws == []


# ── Rule 93: chart-only style on non-chart widget ────────────────────


def test_r93_bar_style_on_label_warns():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi", "style": "bar"}])
    ws = [w for w in _warns(d) if "chart-specific" in w.message]
    assert len(ws) == 1


def test_r93_line_style_on_button_warns():
    d = _make([{"type": "button", "x": 0, "y": 0, "width": 50, "height": 14,
                "text": "ok", "style": "line"}])
    ws = [w for w in _warns(d) if "chart-specific" in w.message]
    assert len(ws) == 1


def test_r93_bar_on_chart_ok():
    d = _make([{"type": "chart", "x": 0, "y": 0, "width": 40, "height": 30,
                "data_points": [1, 2], "style": "bar"}])
    ws = [w for w in _warns(d) if "chart-specific" in w.message]
    assert ws == []


def test_r93_default_style_on_label_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi", "style": "default"}])
    ws = [w for w in _warns(d) if "chart-specific" in w.message]
    assert ws == []


# ── Rule 94: font_size firmware range ─────────────────────────────────


def test_r94_font_size_256_errors():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi", "font_size": 256}])
    es = [e for e in _errors(d) if "font_size" in e.message and "uint8" in e.message]
    assert len(es) == 1


def test_r94_font_size_255_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi", "font_size": 255}])
    es = [e for e in _errors(d) if "font_size" in e.message and "uint8" in e.message]
    assert es == []


def test_r94_font_size_8_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi", "font_size": 8}])
    es = [e for e in _errors(d) if "font_size" in e.message and "uint8" in e.message]
    assert es == []


# ── Rule 95: runtime field must be a string ───────────────────────────


def test_r95_runtime_int_errors():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi", "runtime": 123}])
    es = [e for e in _errors(d) if "runtime=" in e.message and "must be a string" in e.message]
    assert len(es) == 1


def test_r95_runtime_list_errors():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi", "runtime": ["a"]}])
    es = [e for e in _errors(d) if "runtime=" in e.message and "must be a string" in e.message]
    assert len(es) == 1


def test_r95_runtime_string_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi", "runtime": "bind=temp"}])
    es = [e for e in _errors(d) if "runtime=" in e.message and "must be a string" in e.message]
    assert es == []


def test_r95_runtime_absent_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi"}])
    es = [e for e in _errors(d) if "runtime=" in e.message and "must be a string" in e.message]
    assert es == []


# ── Rule 96: state_overrides keys must be valid ──────────────────────


def test_r96_empty_key_errors():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi", "state_overrides": {"": {"color_fg": "red"}}}])
    es = [e for e in _errors(d) if "state_overrides key" in e.message]
    assert len(es) == 1


def test_r96_valid_keys_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi", "state_overrides": {"hover": {"color_fg": "red"}}}])
    es = [e for e in _errors(d) if "state_overrides key" in e.message]
    assert es == []


def test_r96_no_overrides_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi"}])
    es = [e for e in _errors(d) if "state_overrides key" in e.message]
    assert es == []


# ── Rule 97: cross-scene duplicate widget IDs ────────────────────────


def test_r97_same_id_two_scenes_warns():
    d = _multi_scene({
        "scene_a": {"width": 128, "height": 64,
                     "widgets": [{"type": "label", "x": 0, "y": 0, "width": 50,
                                  "height": 12, "text": "A", "_widget_id": "lbl1"}]},
        "scene_b": {"width": 128, "height": 64,
                     "widgets": [{"type": "label", "x": 0, "y": 0, "width": 50,
                                  "height": 12, "text": "B", "_widget_id": "lbl1"}]},
    })
    ws = [w for w in _warns(d) if "lbl1" in w.message and "both" in w.message]
    assert len(ws) == 1


def test_r97_unique_ids_across_scenes_ok():
    d = _multi_scene({
        "scene_a": {"width": 128, "height": 64,
                     "widgets": [{"type": "label", "x": 0, "y": 0, "width": 50,
                                  "height": 12, "text": "A", "_widget_id": "lbl_a"}]},
        "scene_b": {"width": 128, "height": 64,
                     "widgets": [{"type": "label", "x": 0, "y": 0, "width": 50,
                                  "height": 12, "text": "B", "_widget_id": "lbl_b"}]},
    })
    ws = [w for w in _warns(d) if "both" in w.message]
    assert ws == []


def test_r97_no_ids_ok():
    d = _multi_scene({
        "scene_a": {"width": 128, "height": 64,
                     "widgets": [{"type": "box", "x": 0, "y": 0, "width": 50, "height": 20}]},
        "scene_b": {"width": 128, "height": 64,
                     "widgets": [{"type": "box", "x": 0, "y": 0, "width": 50, "height": 20}]},
    })
    ws = [w for w in _warns(d) if "both" in w.message]
    assert ws == []


def test_r97_same_id_same_scene_not_flagged_by_97():
    """Intra-scene duplicates are handled by Rule 1, not Rule 97."""
    d = _make([
        {"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
         "text": "A", "_widget_id": "dup"},
        {"type": "label", "x": 60, "y": 0, "width": 50, "height": 12,
         "text": "B", "_widget_id": "dup"},
    ])
    ws = [w for w in _warns(d) if "both" in w.message and "dup" in w.message]
    assert ws == []  # rule 97 only fires cross-scene


# ── Rule 98: corner_radius exceeds half of min dimension ─────────────


def test_r98_corner_radius_exceeds_warns():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20,
                "corner_radius": 15}])
    ws = [w for w in _warns(d) if "corner_radius" in w.message and "exceeds" in w.message]
    assert len(ws) == 1


def test_r98_corner_radius_ok():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20,
                "corner_radius": 10}])
    ws = [w for w in _warns(d) if "corner_radius" in w.message and "exceeds" in w.message]
    assert ws == []


def test_r98_corner_radius_zero_ok():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20,
                "corner_radius": 0}])
    ws = [w for w in _warns(d) if "corner_radius" in w.message and "exceeds" in w.message]
    assert ws == []


def test_r98_corner_radius_rect_widget():
    d = _make([{"type": "button", "x": 0, "y": 0, "width": 60, "height": 14,
                "text": "ok", "corner_radius": 20}])
    ws = [w for w in _warns(d) if "corner_radius" in w.message and "exceeds" in w.message]
    assert len(ws) == 1  # 20 > min(60,14)//2 = 7


def test_r98_no_corner_radius_ok():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 20, "height": 20}])
    ws = [w for w in _warns(d) if "corner_radius" in w.message and "exceeds" in w.message]
    assert ws == []
