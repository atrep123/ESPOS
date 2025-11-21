#!/usr/bin/env python3
"""
Design Tokens Registry for ESP32OS UI System.

Centralized source of truth for:
- Colors (semantic roles)
- Spacing (consistent scale)
- Typography (sizes, weights, families)
- Elevation (depth levels with ASCII strategies)
- Animation (durations, easing curves)

Usage:
    from design_tokens import tokens
    
    bg_color = tokens.colors.surface
    spacing = tokens.spacing.md
    duration = tokens.animation.base
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class ColorTokens:
    """Semantic color roles (RGB tuples)."""
    
    # Primary brand colors
    primary: Tuple[int, int, int] = (0, 122, 204)  # #007ACC (VS Code blue)
    primary_dark: Tuple[int, int, int] = (0, 90, 158)
    primary_light: Tuple[int, int, int] = (80, 160, 220)
    
    # Surface colors
    surface: Tuple[int, int, int] = (30, 30, 30)  # Dark background
    surface_raised: Tuple[int, int, int] = (45, 45, 45)
    surface_overlay: Tuple[int, int, int] = (60, 60, 60)
    
    # Text colors
    text_primary: Tuple[int, int, int] = (255, 255, 255)
    text_secondary: Tuple[int, int, int] = (200, 200, 200)
    text_disabled: Tuple[int, int, int] = (120, 120, 120)
    
    # Semantic status colors
    success: Tuple[int, int, int] = (80, 200, 120)
    warning: Tuple[int, int, int] = (255, 200, 0)
    error: Tuple[int, int, int] = (240, 80, 80)
    info: Tuple[int, int, int] = (100, 180, 255)
    
    # Component-specific
    border: Tuple[int, int, int] = (80, 80, 80)
    border_focus: Tuple[int, int, int] = (0, 122, 204)
    shadow: Tuple[int, int, int] = (0, 0, 0)
    
    def to_hex(self, color: Tuple[int, int, int]) -> str:
        """Convert RGB tuple to hex string."""
        return f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"


@dataclass(frozen=True)
class SpacingTokens:
    """Spacing scale (4px base unit)."""
    
    xs: int = 4   # 4px
    sm: int = 8   # 8px
    md: int = 16  # 16px (base)
    lg: int = 24  # 24px
    xl: int = 32  # 32px
    xxl: int = 48 # 48px
    
    # Component-specific
    button_padding_x: int = 16
    button_padding_y: int = 8
    dialog_padding: int = 24
    list_item_padding: int = 12


@dataclass(frozen=True)
class TypographyTokens:
    """Typography scale and families."""
    
    # Font families
    family_monospace: str = "Courier New, monospace"
    family_sans: str = "Arial, sans-serif"
    
    # Font sizes (px)
    size_xs: int = 10
    size_sm: int = 12
    size_base: int = 14
    size_lg: int = 16
    size_xl: int = 20
    size_xxl: int = 24
    
    # Font weights
    weight_normal: int = 400
    weight_medium: int = 500
    weight_bold: int = 700
    
    # Line heights (relative)
    line_height_tight: float = 1.2
    line_height_base: float = 1.5
    line_height_relaxed: float = 1.8


@dataclass(frozen=True)
class ElevationTokens:
    """Elevation levels (depth/shadow)."""
    
    # Elevation levels (0-4)
    level_0: int = 0  # Flat (no shadow)
    level_1: int = 1  # Raised (subtle shadow)
    level_2: int = 2  # Card (medium shadow)
    level_3: int = 3  # Dialog (strong shadow)
    level_4: int = 4  # Tooltip/overlay (maximum shadow)
    
    # Shadow blur radius per level (px)
    shadow_blur: Dict[int, int] = None
    
    # ASCII shading characters per level
    ascii_shading: Dict[int, str] = None
    
    def __post_init__(self):
        # Shadow blur mapping
        object.__setattr__(self, 'shadow_blur', {
            0: 0,
            1: 2,
            2: 4,
            3: 8,
            4: 12
        })
        
        # ASCII shading characters (for terminal rendering)
        object.__setattr__(self, 'ascii_shading', {
            0: '',
            1: '░',
            2: '▒',
            3: '▓',
            4: '█'
        })


@dataclass(frozen=True)
class AnimationTokens:
    """Animation durations and easing."""
    
    # Durations (ms)
    fast: int = 80      # Quick interactions
    base: int = 160     # Standard transitions
    slow: int = 240     # Modal/overlay animations
    
    # Easing curves (cubic-bezier values)
    ease_in: str = "cubic-bezier(0.4, 0.0, 1.0, 1.0)"
    ease_out: str = "cubic-bezier(0.0, 0.0, 0.2, 1.0)"
    ease_in_out: str = "cubic-bezier(0.4, 0.0, 0.2, 1.0)"
    
    # Frame budget (ms per frame for 60fps)
    frame_budget_60fps: float = 16.67
    frame_budget_30fps: float = 33.33


@dataclass(frozen=True)
class DesignTokens:
    """Master design tokens registry."""
    
    colors: ColorTokens = ColorTokens()
    spacing: SpacingTokens = SpacingTokens()
    typography: TypographyTokens = TypographyTokens()
    elevation: ElevationTokens = ElevationTokens()
    animation: AnimationTokens = AnimationTokens()


# Global singleton instance
tokens = DesignTokens()


if __name__ == "__main__":
    # Demo usage
    print("=== ESP32OS Design Tokens ===\n")
    
    print("Colors:")
    print(f"  Primary: {tokens.colors.primary} ({tokens.colors.to_hex(tokens.colors.primary)})")
    print(f"  Surface: {tokens.colors.surface} ({tokens.colors.to_hex(tokens.colors.surface)})")
    print(f"  Success: {tokens.colors.success} ({tokens.colors.to_hex(tokens.colors.success)})")
    
    print("\nSpacing:")
    print(f"  Small: {tokens.spacing.sm}px")
    print(f"  Medium: {tokens.spacing.md}px")
    print(f"  Large: {tokens.spacing.lg}px")
    
    print("\nTypography:")
    print(f"  Base size: {tokens.typography.size_base}px")
    print(f"  Monospace: {tokens.typography.family_monospace}")
    print(f"  Line height: {tokens.typography.line_height_base}")
    
    print("\nElevation:")
    print(f"  Level 2 shadow blur: {tokens.elevation.shadow_blur[2]}px")
    print(f"  Level 3 ASCII shading: '{tokens.elevation.ascii_shading[3]}'")
    
    print("\nAnimation:")
    print(f"  Base duration: {tokens.animation.base}ms")
    print(f"  Ease out: {tokens.animation.ease_out}")
    print(f"  60fps frame budget: {tokens.animation.frame_budget_60fps}ms")
