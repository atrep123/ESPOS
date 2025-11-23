#!/usr/bin/env python3
"""
Tests for design tokens module.
"""
import pytest
from design_tokens import (
    tokens,
    ColorTokens,
    SpacingTokens,
    ResponsiveBreakpoints,
    ResponsiveEvaluator,
    responsive_scalars,
)


def test_color_tokens_immutable():
    """Design tokens should be immutable."""
    with pytest.raises(Exception):  # FrozenInstanceError
        tokens.colors.primary = (255, 0, 0)


def test_color_to_hex():
    """Color conversion to hex should work correctly."""
    assert tokens.colors.to_hex((255, 0, 0)) == "#ff0000"
    assert tokens.colors.to_hex((0, 122, 204)) == "#007acc"
    assert tokens.colors.to_hex((30, 30, 30)) == "#1e1e1e"


def test_spacing_scale():
    """Spacing should follow 4px base scale."""
    assert tokens.spacing.xs == 4
    assert tokens.spacing.sm == 8
    assert tokens.spacing.md == 16
    assert tokens.spacing.lg == 24
    assert tokens.spacing.xl == 32
    assert tokens.spacing.xxl == 48


def test_typography_sizes():
    """Typography sizes should be defined."""
    assert tokens.typography.size_base == 14
    assert tokens.typography.size_sm < tokens.typography.size_base
    assert tokens.typography.size_lg > tokens.typography.size_base


def test_elevation_levels():
    """Elevation levels 0-4 should have shadow blur and ASCII shading."""
    for level in range(5):
        assert level in tokens.elevation.shadow_blur
        assert level in tokens.elevation.ascii_shading
    
    # Higher levels should have more blur
    assert tokens.elevation.shadow_blur[0] < tokens.elevation.shadow_blur[4]


def test_animation_durations():
    """Animation durations should be ordered fast < base < slow."""
    assert tokens.animation.fast < tokens.animation.base
    assert tokens.animation.base < tokens.animation.slow


def test_frame_budget():
    """Frame budget for 60fps should be ~16.67ms."""
    assert 16 <= tokens.animation.frame_budget_60fps <= 17
    assert 33 <= tokens.animation.frame_budget_30fps <= 34


def test_tokens_singleton():
    """Tokens should be a singleton instance."""
    from design_tokens import tokens as tokens2
    assert tokens is tokens2


def test_responsive_evaluator():
    """Responsive evaluator should map widths to expected tiers."""
    bp = ResponsiveBreakpoints(tiny=40, small=80, medium=120, wide=160)
    ev = ResponsiveEvaluator(bp)
    assert ev.classify(30).name == "tiny"
    assert ev.classify(50).is_small
    assert ev.classify(90).is_medium
    assert ev.classify(140).is_wide
    assert ev.classify(200).name == "wide"


def test_responsive_scalars():
    """Scaling factors should be monotonic across tiers."""
    tiny = responsive_scalars(30)
    small = responsive_scalars(60)
    medium = responsive_scalars(100)
    wide = responsive_scalars(180)
    assert tiny["spacing_scale"] < small["spacing_scale"] <= medium["spacing_scale"] <= wide["spacing_scale"]
    assert tiny["font_scale"] < wide["font_scale"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
