#!/usr/bin/env python3
"""
Tests for design tokens module.
"""
import pytest
from design_tokens import tokens, ColorTokens, SpacingTokens


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
