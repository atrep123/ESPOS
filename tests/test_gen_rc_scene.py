"""Tests for gen_rc_scene.py — helper functions, scene builders, and validator."""

import pytest

from gen_rc_scene import (
    CHAR_W,
    LH,
    RENDER_PAD,
    VALID_TYPES,
    H,
    W,
    _brightness,
    _parse_color,
    _wref,
    btn_w,
    scene_rc_channels,
    scene_rc_failsafe,
    scene_rc_main,
    scene_rc_mixer,
    scene_rc_model,
    scene_rc_rates,
    scene_rc_setup,
    scene_rc_telemetry,
    scene_rc_trims,
    text_w,
    validate_all,
    validate_scene,
    widget,
)

# ── text_w / btn_w ─────────────────────────────────────────────────────


def test_text_w_one_char():
    assert text_w(1) == 1 * CHAR_W + RENDER_PAD * 2


def test_text_w_zero():
    assert text_w(0) == RENDER_PAD * 2


def test_text_w_ten():
    assert text_w(10) == 10 * CHAR_W + RENDER_PAD * 2


def test_btn_w_same_as_text_w():
    for n in range(20):
        assert btn_w(n) == text_w(n)


# ── widget helper ──────────────────────────────────────────────────────


def test_widget_returns_dict():
    w = widget("label", 0, 0, 60, 12, "HI", wid="t.1")
    assert isinstance(w, dict)
    assert w["type"] == "label"
    assert w["x"] == 0
    assert w["y"] == 0
    assert w["width"] == 60
    assert w["height"] == 12
    assert w["text"] == "HI"
    assert w["_widget_id"] == "t.1"


def test_widget_default_fields():
    w = widget("box", 10, 20, 30, 40, wid="t.2")
    assert w["style"] == "default"
    assert w["color_fg"] == "#f0f0f0"
    assert w["color_bg"] == "black"
    assert w["border"] is False
    assert w["enabled"] is True
    assert w["visible"] is True
    assert w["runtime"] == ""
    assert w["data_points"] == []
    assert w["locked"] is False


def test_widget_custom_fields():
    w = widget(
        "button",
        0,
        0,
        40,
        12,
        "GO",
        wid="t.3",
        fg="#ffffff",
        bg="#111111",
        border=True,
        border_style="single",
        bold=True,
        runtime="bind=x;kind=int",
    )
    assert w["color_fg"] == "#ffffff"
    assert w["color_bg"] == "#111111"
    assert w["border"] is True
    assert w["border_style"] == "single"
    assert w["bold"] is True
    assert w["runtime"] == "bind=x;kind=int"


def test_widget_data_points_none_becomes_empty_list():
    w = widget("chart", 0, 0, 100, 50, wid="t.4", data_points=None)
    assert w["data_points"] == []


def test_widget_data_points_preserved():
    w = widget("chart", 0, 0, 100, 50, wid="t.5", data_points=[1, 2, 3])
    assert w["data_points"] == [1, 2, 3]


# ── _parse_color ───────────────────────────────────────────────────────


def test_parse_color_hex():
    assert _parse_color("#ff0000") == (255, 0, 0)


def test_parse_color_hex_mixed_case():
    assert _parse_color("#aaBBcc") == (0xAA, 0xBB, 0xCC)


def test_parse_color_named_black():
    assert _parse_color("black") == (0, 0, 0)


def test_parse_color_named_white():
    assert _parse_color("white") == (255, 255, 255)


def test_parse_color_named_red():
    assert _parse_color("red") == (255, 0, 0)


def test_parse_color_named_grey():
    assert _parse_color("grey") == (128, 128, 128)


def test_parse_color_named_gray():
    assert _parse_color("gray") == (128, 128, 128)


def test_parse_color_empty_returns_none():
    assert _parse_color("") is None


def test_parse_color_none_input():
    assert _parse_color(None) is None


def test_parse_color_invalid_returns_none():
    assert _parse_color("chartreuse") is None


def test_parse_color_short_hex_invalid():
    assert _parse_color("#fff") is None


# ── _brightness ────────────────────────────────────────────────────────


def test_brightness_white():
    # rec.709: int(0.2126*255 + 0.7152*255 + 0.0722*255) = 254 (rounding)
    assert _brightness((255, 255, 255)) == 254


def test_brightness_black():
    assert _brightness((0, 0, 0)) == 0


def test_brightness_red():
    br = _brightness((255, 0, 0))
    assert 50 <= br <= 60  # rec.709: 0.2126*255 ≈ 54


def test_brightness_green():
    br = _brightness((0, 255, 0))
    assert 180 <= br <= 185  # rec.709: 0.7152*255 ≈ 182


def test_brightness_blue():
    br = _brightness((0, 0, 255))
    assert 15 <= br <= 20  # rec.709: 0.0722*255 ≈ 18


# ── _wref ──────────────────────────────────────────────────────────────


def test_wref_with_id():
    w = {"_widget_id": "rc.test"}
    assert _wref("main", w, 3) == "main/rc.test"


def test_wref_without_id():
    w = {}
    assert _wref("main", w, 5) == "main/#5"


def test_wref_none_id():
    w = {"_widget_id": None}
    assert _wref("setup", w, 0) == "setup/#0"


# ── validate_scene ─────────────────────────────────────────────────────


def _ok_widget(wid, **overrides):
    """A minimal valid widget for testing."""
    base = widget("label", 4, 4, text_w(3), LH, "ABC", wid=wid, fg="#f0f0f0")
    base.update(overrides)
    return base


def _scene(widgets):
    return {"width": W, "height": H, "widgets": widgets}


def test_validate_scene_clean():
    errs = validate_scene("test", _scene([_ok_widget("v.1")]))
    assert errs == []


def test_validate_scene_missing_id():
    w = _ok_widget(None)
    w["_widget_id"] = None
    errs = validate_scene("test", _scene([w]))
    assert any("MISSING_ID" in e for e in errs)


def test_validate_scene_duplicate_id():
    errs = validate_scene("test", _scene([_ok_widget("dup"), _ok_widget("dup")]))
    assert any("DUPLICATE_ID" in e for e in errs)


def test_validate_scene_bad_type():
    w = _ok_widget("v.2")
    w["type"] = "banana"
    errs = validate_scene("test", _scene([w]))
    assert any("BAD_TYPE" in e for e in errs)


def test_validate_scene_zero_size():
    w = _ok_widget("v.3")
    w["width"] = 0
    errs = validate_scene("test", _scene([w]))
    assert any("BAD_SIZE" in e for e in errs)


def test_validate_scene_out_of_bounds():
    w = _ok_widget("v.4")
    w["x"] = W - 1
    w["width"] = 10
    errs = validate_scene("test", _scene([w]))
    assert any("OUT_OF_BOUNDS" in e for e in errs)


def test_validate_scene_bad_fg_color():
    w = _ok_widget("v.5")
    w["color_fg"] = "notacolor"
    errs = validate_scene("test", _scene([w]))
    assert any("BAD_COLOR_FG" in e for e in errs)


def test_validate_scene_empty():
    errs = validate_scene("test", _scene([]))
    assert any("EMPTY_SCENE" in e for e in errs)


def test_validate_scene_overlap():
    w1 = _ok_widget("v.6")
    w1["x"], w1["y"], w1["width"], w1["height"] = 4, 4, 30, 14
    w2 = _ok_widget("v.7")
    w2["x"], w2["y"], w2["width"], w2["height"] = 10, 4, 30, 14
    errs = validate_scene("test", _scene([w1, w2]))
    assert any("OVERLAP" in e for e in errs)


def test_validate_scene_wrong_dims():
    scene = {"width": 100, "height": 50, "widgets": [_ok_widget("v.8")]}
    # Scene dims don't match W×H → error
    errs = validate_scene("test", scene)
    assert any("SCENE_SIZE" in e for e in errs)


def test_validate_scene_bad_runtime():
    w = _ok_widget("v.9")
    w["runtime"] = "missing_equals"
    errs = validate_scene("test", _scene([w]))
    assert any("BAD_RUNTIME" in e for e in errs)


def test_validate_scene_bad_style():
    w = _ok_widget("v.10")
    w["style"] = "neon"
    errs = validate_scene("test", _scene([w]))
    assert any("BAD_STYLE" in e for e in errs)


def test_validate_scene_bad_align():
    w = _ok_widget("v.11")
    w["align"] = "justify"
    errs = validate_scene("test", _scene([w]))
    assert any("BAD_ALIGN" in e for e in errs)


def test_validate_scene_low_contrast():
    w = _ok_widget("v.12")
    w["color_fg"] = "#111111"
    w["color_bg"] = "#101010"
    errs = validate_scene("test", _scene([w]))
    assert any("LOW_CONTRAST" in e for e in errs)


def test_validate_scene_empty_text_no_runtime():
    w = widget("label", 4, 4, 40, LH, "", wid="v.13", fg="#f0f0f0")
    w["runtime"] = ""
    errs = validate_scene("test", _scene([w]))
    assert any("EMPTY_TEXT" in e for e in errs)


# ── validate_all ───────────────────────────────────────────────────────


def test_validate_all_clean(capsys):
    doc = {"scenes": {"main": _scene([_ok_widget("g.1")])}}
    ok = validate_all(doc)
    assert ok is True


def test_validate_all_no_scenes(capsys):
    ok = validate_all({"scenes": {}})
    assert ok is False


def test_validate_all_cross_scene_dup_id(capsys):
    doc = {
        "scenes": {
            "a": _scene([_ok_widget("shared")]),
            "b": _scene([_ok_widget("shared")]),
        }
    }
    ok = validate_all(doc)
    assert ok is False
    captured = capsys.readouterr()
    assert "GLOBAL_DUP_ID" in captured.out


def test_validate_all_too_many_widgets(capsys):
    """Exceeding 500 total widgets triggers TOO_MANY_WIDGETS."""
    scenes = {}
    for s in range(60):
        sws = [_ok_widget(f"s{s}w{j}") for j in range(9)]
        scenes[f"s{s}"] = _scene(sws)
    ok = validate_all({"scenes": scenes})
    assert ok is False
    captured = capsys.readouterr()
    assert "TOO_MANY_WIDGETS" in captured.out


def test_validate_scene_negative_origin():
    w = _ok_widget("v.neg")
    w["x"] = -5
    errs = validate_scene("test", _scene([w]))
    assert any("OUT_OF_BOUNDS" in e for e in errs)


def test_validate_scene_non_int_coords():
    w = _ok_widget("v.float")
    w["x"] = 4.5
    errs = validate_scene("test", _scene([w]))
    assert any("NON_INT" in e for e in errs)


def test_validate_scene_bad_valign():
    w = _ok_widget("v.val")
    w["valign"] = "stretch"
    errs = validate_scene("test", _scene([w]))
    assert any("BAD_VALIGN" in e for e in errs)


def test_validate_scene_bad_border_style():
    w = _ok_widget("v.bs")
    w["border_style"] = "triple"
    errs = validate_scene("test", _scene([w]))
    assert any("BAD_BORDER_STYLE" in e for e in errs)


def test_validate_scene_border_no_style():
    w = _ok_widget("v.bns")
    w["border"] = True
    w["border_style"] = "none"
    errs = validate_scene("test", _scene([w]))
    assert any("BORDER_NO_STYLE" in e for e in errs)


def test_validate_scene_bad_overflow():
    w = _ok_widget("v.of")
    w["text_overflow"] = "scroll"
    errs = validate_scene("test", _scene([w]))
    assert any("BAD_OVERFLOW" in e for e in errs)


def test_validate_scene_too_short_label():
    w = widget("label", 4, 4, text_w(3), 8, "ABC", wid="v.short", fg="#f0f0f0")
    errs = validate_scene("test", _scene([w]))
    assert any("TOO_SHORT" in e for e in errs)


def test_validate_scene_too_narrow():
    w = widget("label", 4, 4, 4, LH, "ABC", wid="v.nar", fg="#f0f0f0")
    errs = validate_scene("test", _scene([w]))
    assert any("TOO_NARROW" in e for e in errs)


def test_validate_scene_gauge_too_small():
    w = widget("gauge", 4, 4, 4, 4, wid="v.gs", fg="#f0f0f0")
    errs = validate_scene("test", _scene([w]))
    assert any("GAUGE_TOO_SMALL" in e for e in errs)


def test_validate_scene_slider_too_narrow():
    w = widget("slider", 4, 4, 8, 12, wid="v.sl", fg="#f0f0f0")
    errs = validate_scene("test", _scene([w]))
    assert any("SLIDER_TOO_NARROW" in e for e in errs)


def test_validate_scene_pbar_too_narrow():
    w = widget("progressbar", 4, 4, 4, 12, wid="v.pb", fg="#f0f0f0")
    errs = validate_scene("test", _scene([w]))
    assert any("PBAR_TOO_NARROW" in e for e in errs)


def test_validate_scene_bad_bg_color():
    w = _ok_widget("v.bgc")
    w["color_bg"] = "nope"
    errs = validate_scene("test", _scene([w]))
    assert any("BAD_COLOR_BG" in e for e in errs)


def test_validate_scene_non_int_z_index():
    w = _ok_widget("v.zi")
    w["z_index"] = 1.5
    errs = validate_scene("test", _scene([w]))
    assert any("BAD_Z_INDEX" in e for e in errs)


def test_validate_scene_unsupported_chars():
    w = widget("label", 4, 4, text_w(6), LH, "HI\u2122", wid="v.uc", fg="#f0f0f0")
    errs = validate_scene("test", _scene([w]))
    assert any("UNSUPPORTED_CHAR" in e for e in errs)


def test_validate_scene_invisible_text():
    w = widget("label", 4, 4, text_w(3), LH, "ABC", wid="v.inv", fg="#050505")
    errs = validate_scene("test", _scene([w]))
    assert any("INVISIBLE_TEXT" in e for e in errs)


def test_validate_scene_text_overflow_v():
    # height=6 → inner_h=2 → 0 lines
    w = widget("label", 4, 4, text_w(3), 6, "ABC", wid="v.tov", fg="#f0f0f0")
    errs = validate_scene("test", _scene([w]))
    assert any("TEXT_OVERFLOW_V" in e for e in errs) or any("TOO_SHORT" in e for e in errs)


def test_validate_scene_text_overflow_h():
    w = widget("label", 4, 4, text_w(2), LH, "ABCDE", wid="v.toh", fg="#f0f0f0")
    errs = validate_scene("test", _scene([w]))
    assert any("TEXT_OVERFLOW_H" in e for e in errs)


# ── Scene builders — structural checks ─────────────────────────────────

_ALL_BUILDERS = [
    ("rc_main", scene_rc_main),
    ("rc_channels", scene_rc_channels),
    ("rc_trims", scene_rc_trims),
    ("rc_setup", scene_rc_setup),
    ("rc_model", scene_rc_model),
    ("rc_failsafe", scene_rc_failsafe),
    ("rc_telemetry", scene_rc_telemetry),
    ("rc_rates", scene_rc_rates),
    ("rc_mixer", scene_rc_mixer),
]


@pytest.mark.parametrize(("name", "builder"), _ALL_BUILDERS)
def test_builder_returns_valid_structure(name, builder):
    s = builder()
    assert isinstance(s, dict)
    assert s["name"] == name
    assert s["width"] == W
    assert s["height"] == H
    assert isinstance(s["widgets"], list)
    assert len(s["widgets"]) > 0


@pytest.mark.parametrize(("name", "builder"), _ALL_BUILDERS)
def test_builder_all_types_valid(name, builder):
    s = builder()
    for w in s["widgets"]:
        assert w["type"] in VALID_TYPES, f"{name}: bad type {w['type']!r}"


@pytest.mark.parametrize(("name", "builder"), _ALL_BUILDERS)
def test_builder_unique_ids(name, builder):
    s = builder()
    ids = [w["_widget_id"] for w in s["widgets"] if w.get("_widget_id")]
    assert len(ids) == len(set(ids)), f"{name}: duplicate widget IDs"


@pytest.mark.parametrize(("name", "builder"), _ALL_BUILDERS)
def test_builder_passes_validation(name, builder):
    s = builder()
    errors = validate_scene(name, s)
    assert errors == [], f"{name} validation:\n" + "\n".join(errors)


@pytest.mark.parametrize(("name", "builder"), _ALL_BUILDERS)
def test_builder_widgets_have_ids(name, builder):
    s = builder()
    for i, w in enumerate(s["widgets"]):
        assert w.get("_widget_id"), f"{name}: widget #{i} missing _widget_id"


@pytest.mark.parametrize(("name", "builder"), _ALL_BUILDERS)
def test_builder_all_in_bounds(name, builder):
    s = builder()
    for w in s["widgets"]:
        assert w["x"] >= 0 and w["y"] >= 0
        assert w["x"] + w["width"] <= W
        assert w["y"] + w["height"] <= H


# Specific scene content checks


def test_rc_main_has_flight_mode():
    ids = {w["_widget_id"] for w in scene_rc_main()["widgets"]}
    assert "rc.flight_mode" in ids


def test_rc_main_has_4_stick_gauges():
    ws = scene_rc_main()["widgets"]
    gauges = [w for w in ws if w["type"] == "gauge"]
    assert len(gauges) == 4


def test_rc_channels_has_8_bars():
    ws = scene_rc_channels()["widgets"]
    bars = [w for w in ws if w["type"] == "progressbar"]
    assert len(bars) == 8


def test_rc_trims_has_sliders():
    ws = scene_rc_trims()["widgets"]
    sliders = [w for w in ws if w["type"] == "slider"]
    assert len(sliders) == 4


def test_rc_setup_has_buttons():
    ws = scene_rc_setup()["widgets"]
    btns = [w for w in ws if w["type"] == "button"]
    assert len(btns) >= 5


def test_rc_failsafe_has_sliders_and_mode():
    ws = scene_rc_failsafe()["widgets"]
    sliders = [w for w in ws if w["type"] == "slider"]
    assert len(sliders) == 4
    ids = {w["_widget_id"] for w in ws}
    assert "rcf.mode_btn" in ids


def test_rc_telemetry_has_chart():
    ws = scene_rc_telemetry()["widgets"]
    charts = [w for w in ws if w["type"] == "chart"]
    assert len(charts) >= 1


def test_rc_rates_has_4_axes():
    ws = scene_rc_rates()["widgets"]
    ids = {w["_widget_id"] for w in ws}
    for axis in ["ail", "ele", "thr", "rud"]:
        assert f"rcr.{axis}_lbl" in ids


def test_rc_mixer_has_checkboxes():
    ws = scene_rc_mixer()["widgets"]
    checks = [w for w in ws if w["type"] == "checkbox"]
    assert len(checks) >= 3


def test_rc_model_has_endpoints():
    ws = scene_rc_model()["widgets"]
    ids = {w["_widget_id"] for w in ws}
    for ch in range(1, 5):
        assert f"rcm.ch{ch}_min" in ids
        assert f"rcm.ch{ch}_max" in ids
