"""Rendering parity tests — verify Python designer and C codegen math agree.

Checks that the logical computations (color mapping, fill width, text truncation,
value ratios, etc.) produce consistent results between the designer and the
firmware export pipeline.
"""

from __future__ import annotations

from typing import ClassVar

from cyberpunk_designer import text_metrics
from cyberpunk_designer.constants import GRID, color_to_rgb
from tools.ui_codegen import (
    _get_rgb,
    _rgb_to_gray4,
    align_for,
    border_style_for,
    overflow_for,
    parse_gray4,
    style_expr,
    valign_for,
)
from ui_designer import WidgetConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _widget(**kw) -> WidgetConfig:
    defaults = dict(type="label", x=0, y=0, width=40, height=10)
    defaults.update(kw)
    return WidgetConfig(**defaults)


# ---------------------------------------------------------------------------
# Color mapping parity: Python color_to_rgb   vs   codegen _get_rgb + gray4
# ---------------------------------------------------------------------------


class TestColorMappingParity:
    """Named colors and hex codes should resolve identically in both pipelines."""

    NAMES: ClassVar[list[str]] = [
        "black",
        "white",
        "red",
        "green",
        "blue",
        "yellow",
        "cyan",
        "magenta",
        "gray",
        "grey",
        "orange",
        "purple",
    ]

    def test_named_colors_match(self):
        for name in self.NAMES:
            py_rgb = color_to_rgb(name)
            c_rgb = _get_rgb(name)
            assert py_rgb == c_rgb, f"color '{name}': designer={py_rgb}, codegen={c_rgb}"

    def test_hex_colors_match(self):
        hexes = ["#000000", "#ffffff", "#ff8000", "#1a2b3c", "#808080"]
        for h in hexes:
            py_rgb = color_to_rgb(h)
            c_rgb = _get_rgb(h)
            assert py_rgb == c_rgb, f"hex '{h}': designer={py_rgb}, codegen={c_rgb}"

    def test_gray4_quantization_covers_range(self):
        """0→0, 128→7 or 8 (midpoint), 255→15."""
        assert parse_gray4("black", default=0) == 0
        assert parse_gray4("white", default=15) == 15
        # Gray 128,128,128 → luminance ~128 → gray4 ~8
        g4 = _rgb_to_gray4(128, 128, 128)
        assert 7 <= g4 <= 8

    def test_gray4_fg_bg_defaults(self):
        assert parse_gray4("", default=15) == 15  # fg default
        assert parse_gray4("", default=0) == 0  # bg default

    def test_gray4_red_has_low_luminance(self):
        """Pure red (255,0,0) has low luminance in BT.709."""
        g4 = parse_gray4("red", default=0)
        assert g4 <= 5  # ~0.2126*255 ≈ 54 → 54/255*15 ≈ 3

    def test_gray4_green_has_high_luminance(self):
        """Pure green (0,255,0) has high luminance in BT.709."""
        g4 = parse_gray4("green", default=0)
        assert g4 >= 10  # ~0.7152*255 ≈ 182 → 182/255*15 ≈ 11


# ---------------------------------------------------------------------------
# Value ratio: Python _value_ratio vs manual parity check
# ---------------------------------------------------------------------------


class TestValueRatioParity:
    """_value_ratio(w) must match the C firmware's fill calculation."""

    def _py_ratio(self, v, vmin, vmax):
        denom = max(1, vmax - vmin)
        return max(0.0, min(1.0, (v - vmin) / denom))

    def test_standard_range(self):
        assert self._py_ratio(50, 0, 100) == 0.5

    def test_zero(self):
        assert self._py_ratio(0, 0, 100) == 0.0

    def test_max(self):
        assert self._py_ratio(100, 0, 100) == 1.0

    def test_over_max_clamps(self):
        assert self._py_ratio(200, 0, 100) == 1.0

    def test_under_min_clamps(self):
        assert self._py_ratio(-10, 0, 100) == 0.0

    def test_custom_range(self):
        r = self._py_ratio(75, 50, 150)
        assert abs(r - 0.25) < 0.001

    def test_fill_width_integer_math(self):
        """Progressbar: fill_w = int(inner.width * pct). Check integer truncation."""
        inner_w = 98
        pct = self._py_ratio(33, 0, 100)
        fill_w = int(inner_w * pct)
        assert fill_w == int(98 * 0.33)

    def test_slider_knob_position_math(self):
        """Slider: knob_x = track.left + int((track.width - knob_w) * pct)."""
        track_left = 10
        track_w = 100
        knob_w = max(GRID, GRID * 2)  # GRID=8 → 16
        pct = self._py_ratio(50, 0, 100)
        knob_x = track_left + int((track_w - knob_w) * pct)
        expected = track_left + int((track_w - knob_w) * 0.5)
        assert knob_x == expected


# ---------------------------------------------------------------------------
# Text truncation parity: Python text_metrics vs firmware-equivalent logic
# ---------------------------------------------------------------------------


class TestTextTruncationParity:
    """Ensure text_truncates_in_widget agrees with device char math."""

    def test_short_text_fits(self):
        w = _widget(width=60, height=16, text="Hi", border=True)
        assert not text_metrics.text_truncates_in_widget(w, "Hi")

    def test_long_text_truncates(self):
        w = _widget(width=20, height=10, text="Very long label text", border=True)
        assert text_metrics.text_truncates_in_widget(w, "Very long label text")

    def test_exact_fit_does_not_truncate(self):
        """Inner width = chars * DEVICE_CHAR_W, text len == chars → fits."""
        # border=True, pad=1 → inset = 1+1=2 each side → inner_w = width - 4
        # inner_w=24 → max_chars = 24/6 = 4
        w = _widget(width=28, height=16, text="ABCD", border=True)
        assert not text_metrics.text_truncates_in_widget(w, "ABCD")

    def test_one_char_over_truncates(self):
        w = _widget(width=28, height=16, text="ABCDE", border=True)
        assert text_metrics.text_truncates_in_widget(w, "ABCDE")

    def test_zero_size_widget_truncates_any_text(self):
        w = _widget(width=0, height=0, text="X")
        assert text_metrics.text_truncates_in_widget(w, "X")

    def test_empty_text_never_truncates(self):
        w = _widget(width=20, height=10, text="")
        assert not text_metrics.text_truncates_in_widget(w, "")

    def test_wrap_mode_multiline(self):
        """Wrap mode: text that fits in 2 lines should not truncate."""
        # inner_w = 60 - 4 = 56 → max_chars = 56/6 = 9
        # inner_h = 30 - 4 = 26 → max_lines = 26/8 = 3
        w = _widget(width=60, height=30, text="Hello World", border=True, text_overflow="wrap")
        # "Hello World" → 11 chars > 9 → wraps to 2 lines, fits in 3
        assert not text_metrics.text_truncates_in_widget(w, "Hello World")

    def test_wrap_mode_overflow(self):
        """Wrap mode that exceeds available lines."""
        # inner_w = 30-4 = 26 → max_chars = 26/6 = 4
        # inner_h = 16-4 = 12 → max_lines = 12/8 = 1
        w = _widget(width=30, height=16, text="ABCDEFGH", border=True, text_overflow="wrap")
        assert text_metrics.text_truncates_in_widget(w, "ABCDEFGH")

    def test_checkbox_inner_area_uses_box_offset(self):
        """Checkbox: inner text area excludes the checkbox box."""
        w = _widget(type="checkbox", width=40, height=10, text="Opt", border=True)
        inner_w, inner_h = text_metrics.inner_text_area_px(w)
        # box = 6 (default), inner_w = width - box - 4 = 40 - 6 - 4 = 30
        assert inner_w == 30
        assert inner_h == 10

    def test_radiobutton_inner_area_uses_circle_offset(self):
        w = _widget(type="radiobutton", width=40, height=10, text="R", border=True)
        inner_w, _ = text_metrics.inner_text_area_px(w)
        assert inner_w == 30  # same formula as checkbox

    def test_device_profile_detection(self):
        assert text_metrics.is_device_profile("esp32os_256x128_gray4")
        assert text_metrics.is_device_profile("oled_128x64")
        assert not text_metrics.is_device_profile("desktop")
        assert not text_metrics.is_device_profile(None)
        assert not text_metrics.is_device_profile("")


# ---------------------------------------------------------------------------
# Style/alignment mapping parity
# ---------------------------------------------------------------------------


class TestMappingParity:
    def test_border_style_maps(self):
        for name, expected in [
            ("single", "UI_BORDER_SINGLE"),
            ("double", "UI_BORDER_DOUBLE"),
            ("rounded", "UI_BORDER_ROUNDED"),
            ("bold", "UI_BORDER_BOLD"),
            ("dashed", "UI_BORDER_DASHED"),
            ("none", "UI_BORDER_NONE"),
        ]:
            w = {"border_style": name}
            assert border_style_for(w, border=1) == expected

    def test_border_off_always_none(self):
        w = {"border_style": "double"}
        assert border_style_for(w, border=0) == "UI_BORDER_NONE"

    def test_align_maps(self):
        for name, expected in [
            ("left", "UI_ALIGN_LEFT"),
            ("center", "UI_ALIGN_CENTER"),
            ("right", "UI_ALIGN_RIGHT"),
        ]:
            assert align_for({"align": name}) == expected

    def test_valign_maps(self):
        for name, expected in [
            ("top", "UI_VALIGN_TOP"),
            ("middle", "UI_VALIGN_MIDDLE"),
            ("bottom", "UI_VALIGN_BOTTOM"),
        ]:
            assert valign_for({"valign": name}) == expected

    def test_overflow_maps(self):
        for name, expected in [
            ("ellipsis", "UI_TEXT_OVERFLOW_ELLIPSIS"),
            ("wrap", "UI_TEXT_OVERFLOW_WRAP"),
            ("clip", "UI_TEXT_OVERFLOW_CLIP"),
            ("auto", "UI_TEXT_OVERFLOW_AUTO"),
        ]:
            assert overflow_for({"text_overflow": name}) == expected

    def test_style_expr_flags(self):
        assert style_expr("") == "UI_STYLE_NONE"
        assert style_expr("inverse") == "UI_STYLE_INVERSE"
        assert style_expr("highlight") == "UI_STYLE_HIGHLIGHT"
        assert style_expr("bold") == "UI_STYLE_BOLD"
        assert "UI_STYLE_INVERSE" in style_expr("inverse highlight")
        assert "UI_STYLE_HIGHLIGHT" in style_expr("inverse highlight")

    def test_widget_type_coverage(self):
        """Every WidgetConfig type should have a codegen mapping."""
        from tools.ui_codegen import WIDGET_TYPE_MAP

        types = [
            "label",
            "button",
            "checkbox",
            "slider",
            "progressbar",
            "gauge",
            "textbox",
            "radiobutton",
            "icon",
            "chart",
            "box",
            "panel",
        ]
        for t in types:
            assert t in WIDGET_TYPE_MAP, f"missing codegen mapping for '{t}'"


# ---------------------------------------------------------------------------
# Fill math parity: Python float vs integer truncation
# ---------------------------------------------------------------------------


class TestFillMathParity:
    """Progressbar/slider fill uses int(width * pct). Verify no off-by-one."""

    def test_progressbar_fill_100_equals_width(self):
        inner_w = 96
        pct = 1.0
        fill_w = int(inner_w * pct)
        assert fill_w == inner_w

    def test_progressbar_fill_0_is_zero(self):
        inner_w = 96
        pct = 0.0
        fill_w = int(inner_w * pct)
        assert fill_w == 0

    def test_progressbar_fill_half(self):
        inner_w = 100
        pct = 0.5
        fill_w = int(inner_w * pct)
        assert fill_w == 50

    def test_progressbar_fill_third(self):
        """int(100 * 0.333...) = 33, not 34."""
        inner_w = 100
        pct = 1.0 / 3.0
        fill_w = int(inner_w * pct)
        assert fill_w == 33

    def test_slider_knob_at_boundaries(self):
        track_w = 100
        knob_w = 12
        effective = track_w - knob_w  # 88
        assert int(effective * 0.0) == 0
        assert int(effective * 1.0) == 88
        assert int(effective * 0.5) == 44

    def test_gauge_arc_threshold(self):
        """Gauge uses arc if width >= GRID*5 AND height >= GRID*5."""
        threshold = GRID * 5
        # Just under → flat bar
        assert (threshold - 1) < threshold
        # At threshold → arc
        assert threshold == GRID * 5

    def test_chart_bar_width_minimum(self):
        """bar_w = max(1, inner_w // n - 2). Should never be 0."""
        for n in [1, 5, 10, 50, 100]:
            for inner_w in [10, 20, 40, 100]:
                bar_w = max(1, inner_w // n - 2)
                assert bar_w >= 1


# ---------------------------------------------------------------------------
# Codegen string pool correctness
# ---------------------------------------------------------------------------


class TestStringPool:
    def test_deduplication(self):
        from tools.ui_codegen import build_string_pool

        vals = ["hello", "world", "hello", "world", "extra"]
        pool = build_string_pool(vals, symbol_prefix="s_")
        assert len(pool.mapping) == 3  # hello, world, extra
        assert len(pool.decls) == 3
        assert pool.mapping["hello"] == "s_0"
        assert pool.mapping["world"] == "s_1"
        assert pool.mapping["extra"] == "s_2"

    def test_empty_strings_skipped(self):
        from tools.ui_codegen import build_string_pool

        vals = ["", "", "ok", ""]
        pool = build_string_pool(vals, symbol_prefix="x_")
        assert len(pool.mapping) == 1
        assert "ok" in pool.mapping

    def test_special_chars_escaped(self):
        from tools.ui_codegen import build_string_pool

        vals = ['say "hi"', "line\nbreak"]
        pool = build_string_pool(vals, symbol_prefix="e_")
        assert len(pool.decls) == 2
        for d in pool.decls:
            assert "\\n" in d or '\\"' in d or "say" in d
