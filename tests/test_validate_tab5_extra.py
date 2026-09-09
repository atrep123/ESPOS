"""Additional Tab5 profile boundaries and malformed-interface tests.

These tests pin every display-dependent validator number at its effective
boundary. They complement test_validate_tab5_profile.py: broad examples live
there, while exact off-by-one behaviour and malformed profile inputs live here.
"""

import pytest

from tools.validate_design import (
    PROFILE_OLED256,
    PROFILE_TAB5,
    _profile_for,
    validate_data,
)

FL = "test"


def _make(widgets, *, scene_w=1280, scene_h=720, device="tab5", **root):
    data = {
        "scenes": {
            "main": {
                "width": scene_w,
                "height": scene_h,
                "widgets": widgets,
            }
        }
    }
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


def _many(n):
    """Keep count-boundary tests linear by making geometry invalid immediately."""
    return [_w(x=None, text=f"W{i}") for i in range(n)]


# -- Rule 135: exact touch-target boundaries ----------------------------


@pytest.mark.parametrize(
    ("size", "level", "millimetres"),
    [
        (57, "ERROR", "4.9"),
        (58, "WARN", "5.0"),
        (80, "WARN", "6.9"),
        (81, None, None),
    ],
)
def test_r135_exact_pixel_boundaries(size, level, millimetres):
    issues = _issues(_make([_w("button", ww=200, hh=size, text="OK")]))
    hits = [i for i in issues if "touch target" in i.message]

    if level is None:
        assert hits == []
        return

    expected = (
        f"test: main: scene 'main': widget[0] (#0): "
        f"touch target 200x{size} is {millimetres} mm on its short side "
        f"(min 7.0 mm = 81 px on this panel)"
    )
    assert [(i.level, i.message) for i in hits] == [(level, expected)]


# -- Rule 134: exact near-alignment boundary ----------------------------


def test_r134_three_pixel_difference_is_reported():
    msgs = _msgs(
        _make(
            [
                _w(x=64, y=104, text="A"),
                _w(x=67, y=200, text="B"),
            ]
        )
    )
    assert (
        "test: main: near-miss alignment: left edges 64 and 67 differ by 3px ('A' vs 'B')"
    ) in msgs


def test_r134_four_pixel_difference_is_silent():
    msgs = _msgs(
        _make(
            [
                _w(x=64, y=104, text="A"),
                _w(x=68, y=200, text="B"),
            ]
        )
    )
    assert not any("near-miss alignment" in m for m in msgs)


# -- MIN_CONTRAST: immediately below and above WCAG 4.5:1 --------------


def test_tab5_contrast_immediately_below_4_5_is_reported():
    # #777777 on white is approximately 4.48:1.
    msgs = _msgs(
        _make(
            [
                _w(
                    text="HRANICE",
                    color_fg="#777777",
                    color_bg="#ffffff",
                )
            ]
        )
    )
    assert any("low contrast (4.48:1 < 4.5:1) fg='#777777' vs bg='#ffffff'" in m for m in msgs)


def test_tab5_contrast_immediately_above_4_5_is_accepted():
    # #767676 on white is approximately 4.54:1.
    msgs = _msgs(
        _make(
            [
                _w(
                    text="HRANICE",
                    color_fg="#767676",
                    color_bg="#ffffff",
                )
            ]
        )
    )
    assert not any("low contrast" in m for m in msgs)


# -- CHAR_W -------------------------------------------------------------


def test_tab5_char_width_boundary_is_two_pixels():
    below = _msgs(_make([_w(ww=1, hh=6, text="A")]))
    at_limit = _msgs(_make([_w(ww=2, hh=6, text="A")]))

    assert any("w=1 < min 2 (can't fit 1 char)" in m for m in below)
    assert not any("can't fit 1 char" in m for m in at_limit)


# -- CHAR_H -------------------------------------------------------------


def test_tab5_char_height_boundary_is_six_pixels():
    below = _msgs(
        _make(
            [
                _w(
                    "chart",
                    ww=100,
                    hh=5,
                    text="A",
                    data_points=[0],
                )
            ]
        )
    )
    at_limit = _msgs(
        _make(
            [
                _w(
                    "chart",
                    ww=100,
                    hh=6,
                    text="A",
                    data_points=[0],
                )
            ]
        )
    )

    assert any("chart height=5 too short to render text (need >=6)" in m for m in below)
    assert not any("too short to render text" in m for m in at_limit)


# -- MIN_TEXT_H ---------------------------------------------------------


def test_tab5_minimum_text_height_boundary_is_six_pixels():
    below = _msgs(_make([_w(hh=5, text="A")]))
    at_limit = _msgs(_make([_w(hh=6, text="A")]))

    assert any("h=5 < min 6 for text widget" in m for m in below)
    assert not any("< min 6 for text widget" in m for m in at_limit)


# -- RENDER_PAD ---------------------------------------------------------


def test_tab5_zero_render_padding_makes_two_lines_need_twelve_pixels():
    assert PROFILE_TAB5.render_pad == 0

    below = _msgs(
        _make(
            [
                _w(
                    hh=11,
                    text="AB",
                    text_overflow="wrap",
                )
            ]
        )
    )
    at_limit = _msgs(
        _make(
            [
                _w(
                    hh=12,
                    text="AB",
                    text_overflow="wrap",
                )
            ]
        )
    )

    assert any(
        "text_overflow='wrap' but height=11 too short for 2 lines (need 12)" in m for m in below
    )
    assert not any("too short for 2 lines" in m for m in at_limit)


# -- MIN_EDGE_MARGIN ----------------------------------------------------


def test_tab5_edge_margin_boundary_is_eight_pixels():
    below = _errors(_make([_w(x=7)]))
    at_limit = _errors(_make([_w(x=8)]))

    assert any("left edge too close to boundary (x=7 < 8)" in m for m in below)
    assert not any("left edge too close to boundary" in m for m in at_limit)


# -- MAX_TEXT_LEN -------------------------------------------------------


def test_tab5_text_length_boundary_is_256_characters():
    at_limit = _msgs(
        _make(
            [
                _w(
                    x=40,
                    ww=1200,
                    text="A" * 256,
                )
            ]
        )
    )
    above = _msgs(
        _make(
            [
                _w(
                    x=40,
                    ww=1200,
                    text="A" * 257,
                )
            ]
        )
    )

    assert not any("text length" in m for m in at_limit)
    assert any("text length 257 exceeds 256 chars" in m for m in above)


# -- FONT_CHARS ---------------------------------------------------------


def test_tab5_accepts_all_shipped_glyphs():
    assert PROFILE_TAB5.font_chars is not None
    text = "".join(sorted(PROFILE_TAB5.font_chars))
    # 201 = 141 textovych glyfu + 60 symbolu LVGL. Zdroj pravdy je cmap
    # `lv_font_tabos_*.c`; toto cislo pribiji test_jeden_zdroj_pravdy.py.
    assert len(text) == 201

    msgs = _msgs(
        _make(
            [
                _w(
                    x=40,
                    ww=1200,
                    text=text,
                )
            ]
        )
    )
    assert not any("unsupported chars" in m for m in msgs)


def test_tab5_rejects_a_character_just_outside_the_shipped_set():
    msgs = _msgs(_make([_w(text="\N{NO-BREAK SPACE}")]))
    assert any("unsupported chars in text: '\\xa0'" in m for m in msgs)


# -- soft widget limit --------------------------------------------------


def test_tab5_soft_widget_limit_is_silent_at_200():
    msgs = _msgs(_make(_many(200)))

    assert not any("exceeds recommended max" in m for m in msgs)
    assert not any("exceeds hard limit" in m for m in msgs)


def test_tab5_soft_widget_limit_warns_at_201():
    msgs = _msgs(_make(_many(201)))
    assert "test: main: 201 widgets exceeds recommended max 200" in msgs


# -- hard widget limit --------------------------------------------------


def test_tab5_hard_widget_limit_is_not_exceeded_at_800():
    msgs = _msgs(_make(_many(800)))

    assert "test: main: 800 widgets exceeds recommended max 200" in msgs
    assert not any("exceeds hard limit" in m for m in msgs)
    assert not any("collision detection SKIPPED" in m for m in msgs)


def test_tab5_hard_widget_limit_and_collision_skip_fire_at_801():
    issues = _issues(_make(_many(801)))
    hard = [i for i in issues if "exceeds hard limit" in i.message]
    skipped = [i for i in issues if "collision detection SKIPPED" in i.message]

    assert [(i.level, i.message) for i in hard] == [
        ("ERROR", "test: main: 801 widgets exceeds hard limit 800")
    ]
    assert [(i.level, i.message) for i in skipped] == [
        (
            "WARN",
            "test: main: collision detection SKIPPED (801 widgets > 800); "
            "this scene is unchecked for overlaps",
        )
    ]


# -- MIN_VISIBLE_BRIGHTNESS --------------------------------------------


def test_tab5_zero_visible_brightness_allows_black_text():
    assert PROFILE_TAB5.min_visible_brightness == 0

    msgs = _msgs(
        _make(
            [
                _w(
                    text="CERNY INKOUST",
                    color_fg="#000000",
                    color_bg="#ffffff",
                )
            ]
        )
    )
    assert not any("too dim" in m for m in msgs)
    assert not any("low contrast" in m for m in msgs)


# -- malformed and unknown device interface ----------------------------


@pytest.mark.parametrize(
    "device",
    [17, ["tab5"]],
    ids=["number", "list"],
)
def test_non_string_device_is_ignored_and_scene_size_selects_tab5(device):
    data = _make(
        [_w("button", ww=200, hh=57, text="OK")],
        device=device,
    )

    assert _profile_for(data) is PROFILE_TAB5
    assert any("touch target 200x57" in m for m in _msgs(data))


def test_unknown_device_name_does_not_block_dimension_match():
    data = _make(
        [_w("button", ww=200, hh=57, text="OK")],
        device="no-such-panel",
    )

    assert _profile_for(data) is PROFILE_TAB5
    assert any("touch target 200x57" in m for m in _msgs(data))


def test_unmatched_800x480_scene_falls_back_to_oled():
    data = _make(
        [_w("button", ww=200, hh=57, text="OK")],
        scene_w=800,
        scene_h=480,
        device=None,
    )

    assert _profile_for(data) is PROFILE_OLED256
    assert not any("touch target" in m for m in _msgs(data))


def test_scene_without_dimensions_falls_back_to_oled_and_reports_width():
    data = {"scenes": {"main": {"widgets": []}}}

    assert _profile_for(data) is PROFILE_OLED256
    assert _errors(data) == ["test: main: width must be int >= 1"]
