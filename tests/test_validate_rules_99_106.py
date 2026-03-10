"""Tests for validation rules 99-106 in tools/validate_design.py."""

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


# ── Rule 99: border_width firmware uint8 overflow ─────────────────────


def test_r99_border_width_256_errors():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 50, "height": 20,
                "border": True, "border_width": 256}])
    es = [e for e in _errors(d) if "border_width=" in e.message and "uint8" in e.message]
    assert len(es) == 1


def test_r99_border_width_255_ok():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 50, "height": 20,
                "border": True, "border_width": 255}])
    es = [e for e in _errors(d) if "border_width=" in e.message and "uint8" in e.message]
    assert len(es) == 0


def test_r99_border_width_1000_errors():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 50, "height": 20,
                "border": True, "border_width": 1000}])
    es = [e for e in _errors(d) if "uint8" in e.message]
    assert len(es) >= 1


def test_r99_border_width_0_ok():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 50, "height": 20,
                "border_width": 0}])
    es = [e for e in _errors(d) if "border_width=" in e.message and "uint8" in e.message]
    assert len(es) == 0


# ── Rule 100: corner_radius firmware uint8 overflow ───────────────────


def test_r100_corner_radius_256_errors():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 50, "height": 20,
                "corner_radius": 256}])
    es = [e for e in _errors(d) if "corner_radius=" in e.message and "uint8" in e.message]
    assert len(es) == 1


def test_r100_corner_radius_255_ok():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 50, "height": 20,
                "corner_radius": 255}])
    es = [e for e in _errors(d) if "corner_radius=" in e.message and "uint8" in e.message]
    assert len(es) == 0


def test_r100_corner_radius_500_errors():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 50, "height": 20,
                "corner_radius": 500}])
    es = [e for e in _errors(d) if "uint8" in e.message and "corner_radius" in e.message]
    assert len(es) >= 1


# ── Rule 101: chart data_points count limit ───────────────────────────


def test_r101_chart_129_points_warns():
    pts = list(range(129))
    d = _make([{"type": "chart", "x": 0, "y": 0, "width": 60, "height": 30,
                "data_points": pts}])
    ws = [w for w in _warns(d) if "data_points has" in w.message and "129" in w.message]
    assert len(ws) == 1


def test_r101_chart_128_points_ok():
    pts = list(range(128))
    d = _make([{"type": "chart", "x": 0, "y": 0, "width": 60, "height": 30,
                "data_points": pts}])
    ws = [w for w in _warns(d) if "data_points has" in w.message and "sub-pixel" in w.message]
    assert len(ws) == 0


def test_r101_chart_256_points_warns():
    pts = list(range(256))
    d = _make([{"type": "chart", "x": 0, "y": 0, "width": 60, "height": 30,
                "data_points": pts}])
    ws = [w for w in _warns(d) if "sub-pixel" in w.message]
    assert len(ws) == 1


def test_r101_non_chart_many_points_no_warn():
    """data_points on non-chart is warned elsewhere; rule 101 only fires for chart."""
    pts = list(range(200))
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 60, "height": 30,
                "data_points": pts}])
    ws = [w for w in _warns(d) if "sub-pixel" in w.message]
    assert len(ws) == 0


# ── Rule 102: empty runtime binding value ─────────────────────────────


def test_r102_empty_value_warns():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi", "runtime": "text="}])
    ws = [w for w in _warns(d) if "empty value after '='" in w.message]
    assert len(ws) == 1


def test_r102_whitespace_value_warns():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi", "runtime": "text=  "}])
    ws = [w for w in _warns(d) if "empty value after '='" in w.message]
    assert len(ws) == 1


def test_r102_normal_value_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi", "runtime": "text=sensor.temp"}])
    ws = [w for w in _warns(d) if "empty value after '='" in w.message]
    assert len(ws) == 0


def test_r102_multi_part_one_empty():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi", "runtime": "text=ok;value="}])
    ws = [w for w in _warns(d) if "empty value after '='" in w.message]
    assert len(ws) == 1


def test_r102_no_runtime_ok():
    d = _make([{"type": "label", "x": 0, "y": 0, "width": 50, "height": 12,
                "text": "hi"}])
    ws = [w for w in _warns(d) if "empty value after '='" in w.message]
    assert len(ws) == 0


# ── Rule 103: chart with no data and no runtime ──────────────────────


def test_r103_chart_no_data_no_runtime_warns():
    d = _make([{"type": "chart", "x": 0, "y": 0, "width": 60, "height": 30}])
    ws = [w for w in _warns(d) if "chart has no data_points" in w.message]
    assert len(ws) == 1


def test_r103_chart_empty_list_no_runtime_warns():
    d = _make([{"type": "chart", "x": 0, "y": 0, "width": 60, "height": 30,
                "data_points": []}])
    ws = [w for w in _warns(d) if "chart has no data_points" in w.message]
    assert len(ws) == 1


def test_r103_chart_with_data_ok():
    d = _make([{"type": "chart", "x": 0, "y": 0, "width": 60, "height": 30,
                "data_points": [1, 2, 3]}])
    ws = [w for w in _warns(d) if "chart has no data_points" in w.message]
    assert len(ws) == 0


def test_r103_chart_with_runtime_ok():
    d = _make([{"type": "chart", "x": 0, "y": 0, "width": 60, "height": 30,
                "runtime": "data_points=sensor.history"}])
    ws = [w for w in _warns(d) if "chart has no data_points" in w.message]
    assert len(ws) == 0


def test_r103_non_chart_no_data_no_warn():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 60, "height": 30}])
    ws = [w for w in _warns(d) if "chart has no data_points" in w.message]
    assert len(ws) == 0


# ── Rule 104: animations list contains empty strings ──────────────────


def test_r104_empty_animation_warns():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 50, "height": 20,
                "animations": ["fade", ""]}])
    ws = [w for w in _warns(d) if "empty string" in w.message]
    assert len(ws) == 1


def test_r104_whitespace_animation_warns():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 50, "height": 20,
                "animations": ["  ", "fade"]}])
    ws = [w for w in _warns(d) if "empty string" in w.message]
    assert len(ws) == 1


def test_r104_two_empty_warns_once():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 50, "height": 20,
                "animations": ["", ""]}])
    ws = [w for w in _warns(d) if "2 empty string" in w.message]
    assert len(ws) == 1


def test_r104_all_valid_ok():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 50, "height": 20,
                "animations": ["fade", "slide"]}])
    ws = [w for w in _warns(d) if "empty string" in w.message]
    assert len(ws) == 0


def test_r104_no_animations_ok():
    d = _make([{"type": "box", "x": 0, "y": 0, "width": 50, "height": 20}])
    ws = [w for w in _warns(d) if "empty string" in w.message]
    assert len(ws) == 0


# ── Rule 105: overlapping widgets with identical z_index ──────────────


def test_r105_overlap_same_z_warns():
    d = _make([
        {"type": "box", "x": 0, "y": 0, "width": 20, "height": 10, "z_index": 5},
        {"type": "box", "x": 10, "y": 0, "width": 20, "height": 10, "z_index": 5},
    ])
    ws = [w for w in _warns(d) if "same z_index" in w.message]
    assert len(ws) == 1


def test_r105_overlap_different_z_ok():
    d = _make([
        {"type": "box", "x": 0, "y": 0, "width": 20, "height": 10, "z_index": 1},
        {"type": "box", "x": 10, "y": 0, "width": 20, "height": 10, "z_index": 2},
    ])
    ws = [w for w in _warns(d) if "same z_index" in w.message]
    assert len(ws) == 0


def test_r105_no_overlap_same_z_ok():
    d = _make([
        {"type": "box", "x": 0, "y": 0, "width": 10, "height": 10, "z_index": 5},
        {"type": "box", "x": 20, "y": 0, "width": 10, "height": 10, "z_index": 5},
    ])
    ws = [w for w in _warns(d) if "same z_index" in w.message]
    assert len(ws) == 0


def test_r105_overlap_default_z_warns():
    """Both widgets have default z_index=0 (omitted)."""
    d = _make([
        {"type": "box", "x": 0, "y": 0, "width": 20, "height": 10},
        {"type": "box", "x": 10, "y": 0, "width": 20, "height": 10},
    ])
    ws = [w for w in _warns(d) if "same z_index" in w.message]
    assert len(ws) == 1


# ── Rule 106: scene dimensions too small ──────────────────────────────


def test_r106_scene_4x4_warns():
    d = _make([], scene_w=4, scene_h=4)
    ws = [w for w in _warns(d) if "too small" in w.message and "8x8" in w.message]
    assert len(ws) == 1


def test_r106_scene_7x64_warns():
    d = _make([], scene_w=7, scene_h=64)
    ws = [w for w in _warns(d) if "too small" in w.message]
    assert len(ws) == 1


def test_r106_scene_128x3_warns():
    d = _make([], scene_w=128, scene_h=3)
    ws = [w for w in _warns(d) if "too small" in w.message]
    assert len(ws) == 1


def test_r106_scene_8x8_ok():
    d = _make([], scene_w=8, scene_h=8)
    ws = [w for w in _warns(d) if "too small" in w.message and "8x8" in w.message]
    assert len(ws) == 0


def test_r106_scene_128x64_ok():
    d = _make([], scene_w=128, scene_h=64)
    ws = [w for w in _warns(d) if "too small" in w.message]
    assert len(ws) == 0
