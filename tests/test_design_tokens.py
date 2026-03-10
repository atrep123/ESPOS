"""Tests for design_tokens.py — token dataclasses, resolvers, and helpers."""

from __future__ import annotations

import pytest

from design_tokens import (
    COLOR_HEX,
    SPACING_MAP,
    AnimationTokens,
    ColorTokens,
    ElevationTokens,
    ResponsiveBreakpoints,
    ResponsiveEvaluator,
    SpacingTokens,
    TypographyTokens,
    apply_tokens,
    color_hex,
    get_semantic_color,
    resolve_token,
    responsive_evaluator,
    responsive_scalars,
    rgb_to_terminal_color_name,
    spacing,
    tokens,
)

# ---------------------------------------------------------------------------
# Token dataclass defaults
# ---------------------------------------------------------------------------


class TestColorTokens:
    def test_primary_default(self):
        c = ColorTokens()
        assert c.primary == (0, 122, 204)

    def test_to_hex(self):
        c = ColorTokens()
        assert c.to_hex((0, 0, 0)) == "#000000"
        assert c.to_hex((255, 255, 255)) == "#ffffff"
        assert c.to_hex((0, 122, 204)) == "#007acc"

    def test_frozen(self):
        c = ColorTokens()
        with pytest.raises(AttributeError):
            c.primary = (1, 2, 3)  # type: ignore[misc]


class TestSpacingTokens:
    def test_scale(self):
        s = SpacingTokens()
        assert s.xs < s.sm < s.md < s.lg < s.xl < s.xxl

    def test_component_spacing(self):
        s = SpacingTokens()
        assert s.button_padding_x == 16
        assert s.button_padding_y == 8
        assert s.dialog_padding == 24
        assert s.list_item_padding == 12


class TestTypographyTokens:
    def test_size_scale(self):
        t = TypographyTokens()
        assert t.size_xs < t.size_sm < t.size_base < t.size_lg < t.size_xl < t.size_xxl

    def test_weights(self):
        t = TypographyTokens()
        assert t.weight_normal < t.weight_medium < t.weight_bold

    def test_line_heights(self):
        t = TypographyTokens()
        assert t.line_height_tight < t.line_height_base < t.line_height_relaxed


class TestElevationTokens:
    def test_levels(self):
        e = ElevationTokens()
        assert e.level_0 == 0
        assert e.level_4 == 4

    def test_shadow_blur_mapping(self):
        e = ElevationTokens()
        assert e.shadow_blur[0] == 0
        assert e.shadow_blur[2] == 4
        assert e.shadow_blur[4] == 12

    def test_ascii_shading(self):
        e = ElevationTokens()
        assert e.ascii_shading[0] == ""
        assert e.ascii_shading[4] == "█"
        assert len(e.ascii_shading) == 5


class TestAnimationTokens:
    def test_duration_ordering(self):
        a = AnimationTokens()
        assert a.fast < a.base < a.slow

    def test_frame_budgets(self):
        a = AnimationTokens()
        assert a.frame_budget_60fps < a.frame_budget_30fps
        assert a.frame_budget_60fps == pytest.approx(16.67)

    def test_easing_curves(self):
        a = AnimationTokens()
        assert "cubic-bezier" in a.ease_in
        assert "cubic-bezier" in a.ease_out
        assert "cubic-bezier" in a.ease_in_out


# ---------------------------------------------------------------------------
# Responsive system
# ---------------------------------------------------------------------------


class TestResponsiveEvaluator:
    def test_tiny(self):
        tier = responsive_evaluator.classify(20)
        assert tier.name == "tiny"
        assert tier.is_tiny is True
        assert tier.is_small is False

    def test_small(self):
        tier = responsive_evaluator.classify(60)
        assert tier.name == "small"
        assert tier.is_small is True

    def test_medium(self):
        tier = responsive_evaluator.classify(100)
        assert tier.name == "medium"
        assert tier.is_medium is True

    def test_wide(self):
        tier = responsive_evaluator.classify(200)
        assert tier.name == "wide"
        assert tier.is_wide is True

    def test_boundary_tiny_small(self):
        bp = ResponsiveBreakpoints()
        tier = responsive_evaluator.classify(bp.tiny - 1)
        assert tier.is_tiny
        tier = responsive_evaluator.classify(bp.tiny)
        assert tier.is_small

    def test_custom_breakpoints(self):
        custom = ResponsiveBreakpoints(tiny=10, small=20, medium=30, wide=40)
        ev = ResponsiveEvaluator(custom)
        assert ev.classify(5).is_tiny
        assert ev.classify(15).is_small
        assert ev.classify(25).is_medium
        assert ev.classify(35).is_wide

    def test_default_breakpoints(self):
        ev = ResponsiveEvaluator()
        assert ev.breakpoints.tiny == 40


class TestResponsiveScalars:
    def test_tiny_scales_down(self):
        r = responsive_scalars(10)
        assert r["tier"] == "tiny"
        assert r["spacing_scale"] < 1.0
        assert r["font_scale"] < 1.0

    def test_medium_is_unity(self):
        r = responsive_scalars(100)
        assert r["tier"] == "medium"
        assert r["spacing_scale"] == 1.0
        assert r["font_scale"] == 1.0

    def test_wide_scales_up(self):
        r = responsive_scalars(200)
        assert r["tier"] == "wide"
        assert r["spacing_scale"] > 1.0
        assert r["font_scale"] > 1.0


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------


class TestDesignTokensSingleton:
    def test_singleton_has_all_sub_tokens(self):
        assert isinstance(tokens.colors, ColorTokens)
        assert isinstance(tokens.spacing, SpacingTokens)
        assert isinstance(tokens.typography, TypographyTokens)
        assert isinstance(tokens.elevation, ElevationTokens)
        assert isinstance(tokens.animation, AnimationTokens)
        assert isinstance(tokens.responsive, ResponsiveBreakpoints)


# ---------------------------------------------------------------------------
# Lookup maps
# ---------------------------------------------------------------------------


class TestColorHexMap:
    def test_semantic_roles_present(self):
        for role in ("primary", "surface", "success", "error", "warning", "info"):
            assert role in COLOR_HEX

    def test_legacy_colors_merged(self):
        assert "legacy_green" in COLOR_HEX
        assert COLOR_HEX["legacy_green"] == "#00ff00"

    def test_theme_colors_present(self):
        assert "theme_dark_bg" in COLOR_HEX
        assert "theme_hc_text" in COLOR_HEX


class TestSpacingMap:
    def test_all_tokens_present(self):
        for name in ("xs", "sm", "md", "lg", "xl", "xxl"):
            assert name in SPACING_MAP
        assert SPACING_MAP["md"] == 16


# ---------------------------------------------------------------------------
# Resolver functions
# ---------------------------------------------------------------------------


class TestColorHexFunc:
    def test_known_role(self):
        assert color_hex("primary") == "#007acc"

    def test_unknown_role_raises(self):
        with pytest.raises(KeyError, match="Unknown color role"):
            color_hex("nonexistent_role_xyz")


class TestSpacingFunc:
    def test_known_token(self):
        assert spacing("md") == 16

    def test_unknown_token_raises(self):
        with pytest.raises(KeyError, match="Unknown spacing token"):
            spacing("nonexistent_token_xyz")


class TestResolveToken:
    def test_resolves_color(self):
        assert resolve_token("primary") == "#007acc"

    def test_resolves_spacing(self):
        assert resolve_token("md") == 16

    def test_unknown_raises(self):
        with pytest.raises(KeyError, match="Unknown design token"):
            resolve_token("does_not_exist")


class TestApplyTokens:
    def test_apply_to_dict(self):
        d = {"bg": "old", "pad": 0}
        result = apply_tokens(d, {"bg": "surface", "pad": "md"})
        assert result["bg"] == color_hex("surface")
        assert result["pad"] == 16

    def test_apply_to_object(self):
        class Obj:
            color = ""
            gap = 0

        o = Obj()
        apply_tokens(o, {"color": "primary", "gap": "sm"})
        assert o.color == "#007acc"
        assert o.gap == 8

    def test_unknown_token_skipped(self):
        d = {"x": 1}
        apply_tokens(d, {"x": "nonexistent_should_skip"})
        assert d["x"] == 1  # unchanged

    def test_new_field_added_to_dict(self):
        d = {"a": 1}
        apply_tokens(d, {"missing_field": "primary"})
        # dicts accept any key, so new fields get added
        assert d["missing_field"] == "#007acc"

    def test_unknown_attr_skipped_on_object(self):
        class Obj:
            x = 1

        o = Obj()
        apply_tokens(o, {"no_such_attr": "primary"})
        assert not hasattr(o, "no_such_attr")

    def test_returns_target(self):
        d = {}
        assert apply_tokens(d, {}) is d


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


class TestRgbToTerminalColor:
    def test_black(self):
        assert rgb_to_terminal_color_name((0, 0, 0)) == "black"

    def test_white(self):
        assert rgb_to_terminal_color_name((255, 255, 255)) == "white"

    def test_gray(self):
        assert rgb_to_terminal_color_name((128, 128, 128)) == "gray"

    def test_pure_red(self):
        assert rgb_to_terminal_color_name((255, 0, 0)) == "red"

    def test_pure_green(self):
        assert rgb_to_terminal_color_name((0, 255, 0)) == "green"

    def test_pure_blue(self):
        assert rgb_to_terminal_color_name((0, 0, 255)) == "blue"

    def test_yellow_ish(self):
        # Red dominant with green present → yellow
        assert rgb_to_terminal_color_name((255, 200, 0)) == "yellow"

    def test_cyan_ish(self):
        # Blue dominant with green → cyan
        assert rgb_to_terminal_color_name((0, 200, 255)) == "cyan"

    def test_low_saturation_fallback(self):
        # All channels low but not close enough for grayscale
        assert rgb_to_terminal_color_name((50, 50, 100)) == "white"


class TestGetSemanticColor:
    def test_primary(self):
        assert get_semantic_color("primary") == (0, 122, 204)

    def test_success(self):
        assert get_semantic_color("success") == (80, 200, 120)

    def test_unknown_raises(self):
        with pytest.raises(AttributeError):
            get_semantic_color("nonexistent_color")


# ---------------------------------------------------------------------------
# Extended edge-case coverage
# ---------------------------------------------------------------------------


class TestColorTokensExtended:
    def test_to_hex_zero(self):
        ct = ColorTokens()
        assert ct.to_hex((0, 0, 0)) == "#000000"

    def test_to_hex_max(self):
        ct = ColorTokens()
        assert ct.to_hex((255, 255, 255)) == "#ffffff"

    def test_to_hex_mixed(self):
        ct = ColorTokens()
        assert ct.to_hex((1, 128, 255)) == "#0180ff"

    def test_frozen(self):
        ct = ColorTokens()
        with pytest.raises(AttributeError):
            ct.primary = (0, 0, 0)


class TestElevationExtended:
    def test_shadow_blur_all_levels(self):
        el = ElevationTokens()
        for level in range(5):
            assert level in el.shadow_blur

    def test_ascii_shading_all_levels(self):
        el = ElevationTokens()
        for level in range(5):
            assert level in el.ascii_shading
        assert el.ascii_shading[0] == ""
        assert el.ascii_shading[4] == "█"

    def test_frozen(self):
        el = ElevationTokens()
        with pytest.raises(AttributeError):
            el.level_0 = 99


class TestResponsiveEvaluatorExtended:
    def test_boundary_tiny(self):
        tier = responsive_evaluator.classify(39)
        assert tier.is_tiny

    def test_boundary_small(self):
        tier = responsive_evaluator.classify(40)
        assert tier.is_small

    def test_boundary_medium(self):
        tier = responsive_evaluator.classify(80)
        assert tier.is_medium

    def test_boundary_wide(self):
        tier = responsive_evaluator.classify(120)
        assert tier.is_wide

    def test_zero_width(self):
        tier = responsive_evaluator.classify(0)
        assert tier.is_tiny

    def test_custom_breakpoints(self):
        bp = ResponsiveBreakpoints(tiny=10, small=20, medium=30, wide=40)
        ev = ResponsiveEvaluator(bp)
        assert ev.classify(5).is_tiny
        assert ev.classify(15).is_small
        assert ev.classify(25).is_medium
        assert ev.classify(35).is_wide


class TestApplyTokensExtended:
    def test_unknown_token_skipped(self):
        target = {"color": "#000"}
        result = apply_tokens(target, {"color": "nonexistent_token_xyz"})
        assert result["color"] == "#000"  # unchanged

    def test_unknown_field_on_dict(self):
        target = {}
        result = apply_tokens(target, {"new_field": "primary"})
        assert result["new_field"] == COLOR_HEX["primary"]

    def test_apply_spacing_to_dict(self):
        target = {"pad": 0}
        apply_tokens(target, {"pad": "md"})
        assert target["pad"] == 16


class TestResolveTokenExtended:
    def test_resolve_color(self):
        assert resolve_token("primary") == COLOR_HEX["primary"]

    def test_resolve_spacing(self):
        assert resolve_token("md") == 16

    def test_resolve_unknown_raises(self):
        with pytest.raises(KeyError):
            resolve_token("totally_unknown_xyz")


class TestResponsiveScalarsExtended:
    def test_tiny_scale(self):
        r = responsive_scalars(10)
        assert r["tier"] == "tiny"
        assert r["spacing_scale"] < 1.0

    def test_wide_scale(self):
        r = responsive_scalars(200)
        assert r["tier"] == "wide"
        assert r["spacing_scale"] > 1.0
        assert r["font_scale"] > 1.0

    def test_small_scale(self):
        """Lines 217-218: small tier (width 40-79)."""
        r = responsive_scalars(50)
        assert r["tier"] == "small"
        assert r["spacing_scale"] < 1.0
        assert r["font_scale"] < 1.0


class TestApplyTokensEdge:
    def test_setattr_failure_skipped(self):
        """Lines 464-465: setattr raises → silently skipped."""
        from design_tokens import apply_tokens

        class Frozen:
            @property
            def color_fg(self):
                return "#000000"
            # no setter → setattr raises AttributeError

        target = Frozen()
        result = apply_tokens(target, {"color_fg": "primary"})
        assert result is target  # no crash

