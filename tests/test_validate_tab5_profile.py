"""Tests for the device-profile layer and rules 133-135 in validate_design.py.

The validator's constants describe ONE panel: the 256x128 4bpp OLED with the
monospaced font6x8. A 1280x720 colour panel with a proportional font needs its
own numbers, and applying the OLED's produces nonsense in both directions --
findings that cannot apply, and silence exactly where a real defect sits.

Covered here:
  profile resolution   explicit key, by scene size, unknown, default
  Rule 133             collision detection SAYS when it skipped a scene
  Rule 134             near-miss alignment (a typed coordinate that missed)
  Rule 135             touch target measured in millimetres, not pixels
  charset by profile   font6x8 folds case; Montserrat does not
  contrast by profile  WCAG ratio instead of a brightness delta
  Rule 63 regression   x/y must not leak in from an earlier widget loop

Every rule is tested with a counter-example as well: a gauge that only ever
fires proves nothing about the class it claims to detect.
"""

import json
import pathlib

from tools.validate_design import (
    PROFILE_OLED256,
    PROFILE_TAB5,
    _profile_for,
    validate_data,
)

FL = "test"
FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def _make(widgets, *, scene_w=1280, scene_h=720, device="tab5", **root):
    data = {"scenes": {"main": {"width": scene_w, "height": scene_h, "widgets": widgets}}}
    if device is not None:
        data["device"] = device
    data.update(root)
    return data


def _issues(data, **kw):
    return validate_data(data, file_label=FL, warnings_as_errors=False, **kw)


def _msgs(data, **kw):
    return [i.message for i in _issues(data, **kw)]


def _errors(data, **kw):
    return [i.message for i in _issues(data, **kw) if i.level == "ERROR"]


def _w(t="label", x=64, y=104, ww=200, hh=20, text="AHOJ", **kw):
    d = {
        "type": t,
        "x": x,
        "y": y,
        "width": ww,
        "height": hh,
        "text": text,
        "color_fg": "#e6e1ce",
        "color_bg": "#14170f",
    }
    d.update(kw)
    return d


# -- profile resolution ------------------------------------------------


def test_profile_explicit_key_wins():
    assert _profile_for({"device": "tab5", "width": 256, "height": 128}) is PROFILE_TAB5


def test_profile_by_root_dimensions():
    assert _profile_for({"width": 1280, "height": 720}) is PROFILE_TAB5


def test_profile_by_scene_dimensions_when_root_missing():
    data = {"scenes": {"main": {"width": 1280, "height": 720, "widgets": []}}}
    assert _profile_for(data) is PROFILE_TAB5


def test_profile_unknown_name_falls_back_to_oled():
    assert _profile_for({"device": "no-such-panel"}) is PROFILE_OLED256


def test_profile_default_is_oled_so_existing_designs_are_unchanged():
    assert _profile_for({"width": 256, "height": 128}) is PROFILE_OLED256
    assert _profile_for({}) is PROFILE_OLED256


def test_tab5_millimetre_conversion():
    # 294 PPI: 1 px = 25.4/293.7 mm. A 44 px control is 3.8 mm, not "big enough".
    assert round(PROFILE_TAB5.mm(44), 1) == 3.8
    assert round(PROFILE_TAB5.mm(81), 1) == 7.0


# -- Rule 133: collision detection announces its own blind spot ---------


def test_r133_skip_is_announced():
    many = [
        _w(x=1 + (i % 40) * 30, y=104 + (i // 40) * 30, ww=8, hh=8, text="")
        for i in range(PROFILE_TAB5.hard_widgets + 1)
    ]
    msgs = _msgs(_make(many))
    assert any("collision detection SKIPPED" in m for m in msgs)


def test_r133_silent_when_scene_is_within_budget():
    msgs = _msgs(_make([_w(), _w(y=200)]))
    assert not any("collision detection SKIPPED" in m for m in msgs)


# -- Rule 134: near-miss alignment --------------------------------------


def test_r134_left_edges_two_px_apart_are_flagged():
    msgs = _msgs(_make([_w(x=64, y=104, text="NAMERENO"), _w(x=66, y=200, text="PERIODA")]))
    assert any("near-miss alignment: left edges 64 and 66" in m for m in msgs)


def test_r134_left_edges_far_apart_are_not_flagged():
    msgs = _msgs(_make([_w(x=64, y=104), _w(x=200, y=200)]))
    assert not any("near-miss alignment" in m for m in msgs)


def test_r134_equal_left_edges_are_not_flagged():
    msgs = _msgs(_make([_w(x=64, y=104), _w(x=64, y=200)]))
    assert not any("near-miss alignment" in m for m in msgs)


def test_r134_top_edges_are_never_compared():
    """The vertical variant existed and was removed: every firing in two
    codebases was glyph-extreme noise on rows sharing the same coordinate,
    and the real vertical defects (a control 10 px low, mixed row heights)
    are out of its reach anyway."""
    msgs = _msgs(_make([_w(x=64, y=104, hh=20), _w(x=400, y=106, hh=20)]))
    assert not any("top edges" in m for m in msgs)


def test_r134_top_edges_of_different_type_sizes_are_not_flagged():
    """A title and its subtitle share a BASELINE, so their tops differ by a few
    pixels on purpose. Comparing them measures type size, not alignment."""
    msgs = _msgs(
        _make([_w(x=20, y=20, hh=30, text="Terminal"), _w(x=340, y=23, hh=18, text="otevren")])
    )
    assert not any("near-miss alignment" in m for m in msgs)


def test_r134_ignores_hidden_and_empty_text():
    msgs = _msgs(
        _make([_w(x=64, y=104), _w(x=66, y=200, visible=False), _w(x=67, y=300, text="  ")])
    )
    assert not any("near-miss alignment" in m for m in msgs)


# -- Rule 135: touch target in millimetres ------------------------------


def test_r135_error_below_five_millimetres():
    errs = _errors(_make([_w("button", ww=200, hh=44, text="Maly")]))
    assert any("touch target 200x44" in m and "3.8 mm" in m for m in errs)


def test_r135_warn_between_five_and_seven_millimetres():
    issues = _issues(_make([_w("button", ww=200, hh=64, text="Skoro")]))
    hit = [i for i in issues if "touch target" in i.message]
    assert hit and all(i.level == "WARN" for i in hit)


def test_r135_silent_at_seven_millimetres():
    msgs = _msgs(_make([_w("button", ww=200, hh=88, text="Dost")]))
    assert not any("touch target" in m for m in msgs)


def test_r135_does_not_apply_to_labels():
    msgs = _msgs(_make([_w("label", ww=200, hh=20)]))
    assert not any("touch target" in m for m in msgs)


def test_r135_does_not_apply_to_the_oled_profile():
    data = _make(
        [_w("button", ww=60, hh=20, text="OK")], scene_w=256, scene_h=128, device="oled256"
    )
    assert not any("touch target" in m for m in _msgs(data))


# -- charset follows the font that is actually shipped ------------------


def test_tab5_flags_a_character_missing_from_the_shipped_font():
    # U+2020 DAGGER is not in the cut. LVGL skips a missing glyph without a
    # word. (Earlier examples - minus, then prime - kept getting cut INTO
    # the font precisely because this test showed what silence costs.)
    msgs = _msgs(_make([_w(text="pozn.† k mereni")]))
    assert any("unsupported chars" in m for m in msgs)


def test_tab5_accepts_the_nine_glyphs_added_2026_08():
    msgs = _msgs(_make([_w(text="−58 dBm · 10,2 µs · ±4 · 1×, → ← · 5′ · 120 Ω · Δ")]))
    assert not any("unsupported chars" in m for m in msgs)


def test_tab5_accepts_czech_lowercase():
    msgs = _msgs(_make([_w(text="přenešeno · záznam")]))
    assert not any("unsupported chars" in m for m in msgs)


def test_oled_still_folds_lowercase_to_uppercase():
    data = _make([_w(text="ahoj")], scene_w=256, scene_h=128, device="oled256")
    assert not any("unsupported chars" in m for m in _msgs(data))


# -- contrast follows the panel, not the polarity -----------------------


def test_tab5_uses_the_wcag_ratio():
    # muted grey on cream enamel is about 1.9:1
    msgs = _msgs(_make([_w(text="sotva videt", color_fg="#9ba28d", color_bg="#e6e1ce")]))
    assert any("low contrast" in m and ":1" in m for m in msgs)


def test_tab5_accepts_dark_ink_on_a_light_surface():
    """The OLED rule assumes text is always the BRIGHTER thing. On enamel the
    correct design is dark ink on cream, which that rule would call 'too dim'."""
    msgs = _msgs(_make([_w(text="12,4 kB", color_fg="#12150e", color_bg="#e6e1ce")]))
    assert not any("too dim" in m for m in msgs)
    assert not any("low contrast" in m for m in msgs)


def test_oled_keeps_the_brightness_delta_rule():
    data = _make(
        [_w(text="AHOJ", color_fg="#101010", color_bg="#000000")],
        scene_w=256,
        scene_h=128,
        device="oled256",
    )
    msgs = _msgs(data)
    assert any("too dim" in m for m in msgs)


# -- Rule 63 regression: geometry must not leak between loops -----------


def test_r63_does_not_leak_coordinates_from_an_earlier_widget():
    """A frame fully inside the scene was reported as '12% visible', and the
    percentage moved as unrelated widgets were added: the rule combined this
    widget's size with a previous widget's position."""
    frame = _w("panel", x=48, y=88, ww=1192, hh=592, text="")
    tail = [_w(x=64, y=620 + i * 24, ww=200, hh=20, text=f"RADEK {i}") for i in range(4)]
    msgs = _msgs(_make([frame, *tail]))
    assert not any("visible inside scene bounds" in m for m in msgs)


def test_r63_still_catches_a_genuinely_offscreen_widget():
    msgs = _msgs(_make([_w(x=1240, y=104, ww=400, hh=20)]))
    assert any("visible inside scene bounds" in m for m in msgs)


# -- the Tab5 display as a test piece -----------------------------------


def _fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_tab5_clean_fixture_has_no_errors():
    assert _errors(_fixture("tab5_clean.json")) == []


def test_tab5_clean_fixture_resolves_to_the_tab5_profile():
    assert _profile_for(_fixture("tab5_clean.json")) is PROFILE_TAB5


def test_tab5_defects_fixture_fires_every_seeded_class():
    msgs = _msgs(_fixture("tab5_defects.json"))
    for marker in (
        "touch target",
        "near-miss alignment",
        "unsupported chars",
        "low contrast",
        "visible content collision",
    ):
        assert any(marker in m for m in msgs), f"nenalezeno: {marker}"


# -- odolnost pravidla 134 a profil na scenu ----------------------------


def test_r134_ignores_centred_text():
    """The left BOX edge is where the text starts only when it is left-aligned.
    Two centred runs sharing a centre but differing in width look like a 2 px
    miss and are not one."""
    msgs = _msgs(
        _make(
            [
                _w(x=64, ww=200, align="center", text="A"),
                _w(x=66, y=200, ww=196, align="center", text="B"),
            ]
        )
    )
    assert not any("near-miss alignment" in m for m in msgs)


def test_r134_still_fires_for_left_aligned_text():
    msgs = _msgs(_make([_w(x=64, align="left", text="A"), _w(x=66, y=200, align="left", text="B")]))
    assert any("near-miss alignment" in m for m in msgs)


def test_r134_survives_a_malformed_height():
    """A bad height used to be used as a dict key and killed the whole run."""
    msgs = _msgs(_make([_w(), _w(y=200, hh=[])]))
    assert isinstance(msgs, list)


def test_profile_is_resolved_per_scene_not_per_document():
    """One file can hold scenes for different panels. Resolving once measured
    every scene by the first one's panel."""
    small = _w("button", x=8, y=8, ww=60, hh=20, text="OK")
    big = _w("button", x=64, y=104, ww=200, hh=44, text="Maly")
    data = {
        "scenes": {
            "velka": {"width": 1280, "height": 720, "widgets": [big]},
            "mala": {"width": 256, "height": 128, "widgets": [small]},
        }
    }
    touch = [m for m in _msgs(data) if "touch target" in m]
    assert len(touch) == 1 and "velka" in touch[0]


def test_explicit_device_key_still_governs_the_whole_document():
    small = _w("button", x=8, y=8, ww=60, hh=20, text="OK")
    data = {"device": "tab5", "scenes": {"mala": {"width": 256, "height": 128, "widgets": [small]}}}
    assert any("touch target" in m for m in _msgs(data))


def test_r101_chart_limit_follows_the_panel():
    """The limit was a bare 128 with 'on 256px display' in the message: half the
    OLED's width, simply false on a 1280 px panel."""
    pts = list(range(200))
    chart = {"type": "chart", "x": 64, "y": 104, "width": 600, "height": 200, "data_points": pts}
    assert not any("sub-pixel" in m for m in _msgs(_make([chart])))
    small = dict(chart, width=60, height=30)
    oled = _make([small], scene_w=256, scene_h=128, device="oled256")
    assert any("sub-pixel" in m for m in _msgs(oled))
