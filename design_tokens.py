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
from typing import Any, Dict, Mapping, Tuple


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
class ResponsiveBreakpoints:
    """Viewport width breakpoints (columns/pixels depending on context)."""
    tiny: int = 40     # <40 cols: minimal UI
    small: int = 80    # 40-79: compact UI
    medium: int = 120  # 80-119: comfortable default
    wide: int = 160    # >=120: spacious layouts


@dataclass(frozen=True)
class ResponsiveTier:
    """Resolved responsive tier with convenience flags."""
    name: str
    is_tiny: bool
    is_small: bool
    is_medium: bool
    is_wide: bool


class ResponsiveEvaluator:
    """Map viewport sizes to responsive tiers using shared breakpoints."""

    def __init__(self, breakpoints: ResponsiveBreakpoints | None = None) -> None:
        self.breakpoints = breakpoints or ResponsiveBreakpoints()

    def classify(self, width: int, height: int | None = None) -> ResponsiveTier:
        """Return responsive tier for given width (height optional for future use)."""
        bp = self.breakpoints
        if width < bp.tiny:
            name = "tiny"
        elif width < bp.small:
            name = "small"
        elif width < bp.medium:
            name = "medium"
        else:
            name = "wide"
        return ResponsiveTier(
            name=name,
            is_tiny=name == "tiny",
            is_small=name == "small",
            is_medium=name == "medium",
            is_wide=name == "wide",
        )


def responsive_scalars(width: int, height: int | None = None) -> Dict[str, float | str]:
    """
    Return simple scaling factors for spacing and typography based on width.

    Intended for lightweight layout adjustments without changing scene data.
    """
    tier = responsive_evaluator.classify(width, height)
    if tier.is_tiny:
        space = 0.85
        font = 0.9
    elif tier.is_small:
        space = 0.95
        font = 0.95
    elif tier.is_medium:
        space = 1.0
        font = 1.0
    else:  # wide
        space = 1.1
        font = 1.05
    return {
        "tier": tier.name,
        "spacing_scale": space,
        "font_scale": font,
    }


@dataclass(frozen=True)
class DesignTokens:
    """Master design tokens registry."""
    
    colors: ColorTokens = ColorTokens()
    spacing: SpacingTokens = SpacingTokens()
    typography: TypographyTokens = TypographyTokens()
    elevation: ElevationTokens = ElevationTokens()
    animation: AnimationTokens = AnimationTokens()
    responsive: ResponsiveBreakpoints = ResponsiveBreakpoints()


# Global singleton instance
tokens = DesignTokens()
responsive_evaluator = ResponsiveEvaluator(tokens.responsive)


# --- Convenience resolvers -------------------------------------------------

# Precompute hex map for semantic roles
COLOR_HEX = {
    "primary": tokens.colors.to_hex(tokens.colors.primary),
    "primary_dark": tokens.colors.to_hex(tokens.colors.primary_dark),
    "primary_light": tokens.colors.to_hex(tokens.colors.primary_light),
    "surface": tokens.colors.to_hex(tokens.colors.surface),
    "surface_raised": tokens.colors.to_hex(tokens.colors.surface_raised),
    "surface_overlay": tokens.colors.to_hex(tokens.colors.surface_overlay),
    "text_primary": tokens.colors.to_hex(tokens.colors.text_primary),
    "text_secondary": tokens.colors.to_hex(tokens.colors.text_secondary),
    "text_disabled": tokens.colors.to_hex(tokens.colors.text_disabled),
    "success": tokens.colors.to_hex(tokens.colors.success),
    "warning": tokens.colors.to_hex(tokens.colors.warning),
    "error": tokens.colors.to_hex(tokens.colors.error),
    "info": tokens.colors.to_hex(tokens.colors.info),
    "border": tokens.colors.to_hex(tokens.colors.border),
    "border_focus": tokens.colors.to_hex(tokens.colors.border_focus),
    "shadow": tokens.colors.to_hex(tokens.colors.shadow),
}

# Legacy/utility colors observed in existing UI (for incremental migration)
_LEGACY_HEX = {
    # Common palette used in legacy widgets and ASCII preview tags
    "legacy_green": "#00ff00",
    "legacy_green_dark": "#00aa00",
    "legacy_green_deep": "#003300",
    "legacy_green_ultradark": "#001100",
    "legacy_green_mid": "#00cc00",
    "legacy_green_midbright": "#00dd33",
    "legacy_green_mid2": "#00cc66",
    "legacy_matrix": "#008f11",
    "legacy_cyan": "#00ffff",
    "legacy_magenta": "#ff00ff",
    "legacy_blue": "#0066cc",
    "legacy_blue_mid": "#3a8fd8",
    "legacy_blue_light": "#66b3ff",
    "legacy_blue_cyan": "#33c0ff",
    "legacy_orange": "#ff6600",
    "legacy_orange_warm": "#ff7a1a",
    "legacy_orange_deep": "#ff5a00",
    "legacy_orange_soft": "#ff9e5c",
    "legacy_orange_bright": "#ff8c1a",
    "legacy_orange_hot": "#ff4500",
    "legacy_gray1": "#888888",
    "legacy_gray2": "#666666",
    "legacy_gray3": "#333333",
    "legacy_gray4": "#2b2b2b",
    "legacy_gray5": "#1a1a1a",
    "legacy_gray6": "#4d4d4d",
    "legacy_gray8": "#444444",
    "legacy_gray9": "#d4d4d4",
    "legacy_gray10": "#808080",
    "legacy_gray11": "#555555",
    "legacy_gray14": "#aaaaaa",
    "legacy_gray15": "#101010",
    "legacy_gray16": "#4a4a4a",
    "legacy_gray18": "#e8e8e8",
    "legacy_gray19": "#f5f5f5",
    "legacy_gray20": "#fafafa",
    "legacy_gray_lighter": "#ededed",
    "legacy_gray24": "#222222",
    "legacy_gray_light": "#cccccc",
    "legacy_gray_faint": "#f9f9f9",
    "legacy_gray_soft": "#eceff4",
    "legacy_offwhite": "#f8f8f2",
    "legacy_gray17": "#0d0d0d",
    "legacy_gray7": "#999999",
    "legacy_gray21": "#f0f0f0",
    "legacy_gray23": "#191a21",
    # Nord/Dracula palettes used in ui_themes
    "legacy_nord_cyan": "#88c0d0",
    "legacy_nord_slate": "#4c566a",
    "legacy_nord_purple": "#bd93f9",
    "legacy_nord_blue": "#6272a4",
    "legacy_nord_bg": "#3b4252",
    "legacy_nord_base": "#2e3440",
    "legacy_nord_light": "#d8dee9",
    "legacy_nord_blue2": "#81a1c1",
    "legacy_nord_green": "#a3be8c",
    "legacy_nord_yellow": "#ebcb8b",
    "legacy_nord_red": "#bf616a",
    "legacy_nord_slate2": "#434c5e",
    "legacy_nord_slate3": "#616e88",
    "legacy_gray22": "#1c1f26",
    "legacy_dracula_bg": "#282a36",
    "legacy_dracula_slate": "#44475a",
    "legacy_dracula_pink": "#ff79c6",
    "legacy_dracula_green": "#50fa7b",
    "legacy_dracula_yellow": "#f1fa8c",
    "legacy_dracula_red": "#ff5555",
    "legacy_dracula_cyan": "#8be9fd",
    "legacy_yellow": "#ffd700",
    "legacy_pink_hot": "#ff2e88",
    "legacy_green_base": "#008800",
    "legacy_green_soft": "#66cc88",
    "legacy_green_midbright": "#00dd33",
    "legacy_green_dark": "#008000",
    "legacy_green_deep": "#006600",
    "legacy_red": "#ff0000",
    "legacy_red_bright": "#ff4444",
    "legacy_red_dark": "#b30000",
    "legacy_red_soft": "#ff6666",
    "legacy_cyan_mid": "#33cccc",
    "legacy_cyan_soft": "#7fd8e6",
    "legacy_teal_muted": "#4fa3a3",
    "legacy_navyslate": "#1f2d3d",
    "legacy_navy_ink": "#0f1626",
    "legacy_navy_dark": "#101820",
    "legacy_navy_base": "#0b1220",
    # Bright utility reds/blues for theme fallbacks
    "legacy_red": "#ff0000",
    "legacy_red_bright": "#ff4444",
    "legacy_blue_bright": "#66b3ff",
    "legacy_blue_material": "#2196f3",
    "legacy_gold": "#d4af37",
    "legacy_gray12": "#bbbbbb",
    "legacy_gray13": "#a3a3a3",
    "legacy_green_lime": "#99ff00",
    "legacy_green_material": "#4caf50",
    "legacy_green_mint": "#3eb489",
    "legacy_salmon": "#fa8072",
    "legacy_teal": "#008080",
    # Removed unused legacy tokens (intentionally minimal whitelist)
    # Designer theme palettes (kept explicit for CLI/export parity)
    "theme_light_bg": "#f7f7f7",
    "theme_light_text": "#111111",
    "theme_light_primary": "#0066cc",
    "theme_light_secondary": "#2e7d32",
    "theme_light_accent": "#ff8f00",
    "theme_light_danger": "#c62828",
    "theme_dark_bg": "#121212",
    "theme_dark_text": "#e0e0e0",
    "theme_dark_primary": "#64b5f6",
    "theme_dark_secondary": "#81c784",
    "theme_dark_accent": "#ffd54f",
    "theme_dark_danger": "#ef5350",
    "theme_hc_bg": "#000000",
    "theme_hc_text": "#ffffff",
    "theme_hc_primary": "#00ffff",
    "theme_hc_secondary": "#00ff00",
    "theme_hc_accent": "#ffff00",
    "theme_hc_danger": "#ff0000",
    "theme_default_bg": "#000000",
    "theme_default_text": "#ffffff",
    "theme_default_primary": "#00ffff",
    "theme_default_secondary": "#00ff00",
    "theme_default_accent": "#ffff00",
    "theme_default_danger": "#ff0000",
    "theme_cyber_bg": "#0a0f14",
    "theme_cyber_text": "#05f1fe",
    "theme_cyber_primary": "#27f78d",
    "theme_cyber_secondary": "#9a4dff",
    "theme_cyber_accent": "#ff2e97",
    "theme_cyber_danger": "#ff3b30",
    # Interactive affordances
    "accent_handle_base": "#4cb2ff",
    "accent_handle_hover": "#6cc8ff",
    "selection_outline": "#3ea7ff",
    "selection_fill": "#45a4ff",
}
COLOR_HEX.update(_LEGACY_HEX)

SPACING_MAP = {
    "xs": tokens.spacing.xs,
    "sm": tokens.spacing.sm,
    "md": tokens.spacing.md,
    "lg": tokens.spacing.lg,
    "xl": tokens.spacing.xl,
    "xxl": tokens.spacing.xxl,
    "button_padding_x": tokens.spacing.button_padding_x,
    "button_padding_y": tokens.spacing.button_padding_y,
    "dialog_padding": tokens.spacing.dialog_padding,
    "list_item_padding": tokens.spacing.list_item_padding,
}


def color_hex(role: str) -> str:
    """Return hex color for a semantic role; raises KeyError if unknown."""
    if role not in COLOR_HEX:
        raise KeyError(f"Unknown color role: {role}")
    return COLOR_HEX[role]


def spacing(name: str) -> int:
    """Return spacing value for a named spacing token; raises KeyError if unknown."""
    if name not in SPACING_MAP:
        raise KeyError(f"Unknown spacing token: {name}")
    return SPACING_MAP[name]


def resolve_token(name: str) -> str | int:
    """Resolve a design token name to its concrete value (color hex or spacing)."""
    if name in COLOR_HEX:
        return COLOR_HEX[name]
    if name in SPACING_MAP:
        return SPACING_MAP[name]
    raise KeyError(f"Unknown design token: {name}")


def apply_tokens(target: Any, mapping: Mapping[str, str]) -> Any:
    """
    Apply token names to a dict-like object or simple attribute container.

    Each mapping entry is {field: token_name}. Fields present on the target
    are updated to the resolved token value (color hex or spacing integer).
    Unknown fields or token names are ignored to keep the helper safe for
    incremental migrations.
    """
    for field, token_name in mapping.items():
        try:
            value = resolve_token(token_name)
        except KeyError:
            continue
        if isinstance(target, dict):
            target[field] = value
        elif hasattr(target, field):
            try:
                setattr(target, field, value)
            except Exception:
                continue
    return target


# Helper functions for compatibility with existing codebase
def rgb_to_terminal_color_name(rgb: Tuple[int, int, int]) -> str:
    """Convert RGB tuple to terminal color name (approximation).
    
    Used for compatibility with existing string-based color system.
    Maps design token RGB values to nearest ANSI color name.
    """
    r, g, b = rgb
    
    # Grayscale detection
    if abs(r - g) < 20 and abs(g - b) < 20 and abs(r - b) < 20:
        if r < 50:
            return "black"
        elif r > 200:
            return "white"
        else:
            return "gray"
    
    # Color channel dominance
    max_channel = max(r, g, b)
    
    if max_channel == b and b > 150:
        return "blue" if r < 100 and g < 100 else "cyan"
    elif max_channel == g and g > 150:
        return "green" if r < 100 and b < 100 else "cyan"
    elif max_channel == r and r > 150:
        return "red" if g < 100 and b < 100 else "yellow"
    
    return "white"


def get_semantic_color(semantic_name: str) -> Tuple[int, int, int]:
    """Get RGB color for semantic token name.
    
    Args:
        semantic_name: Token name like 'primary', 'surface', 'success', etc.
        
    Returns:
        RGB tuple (r, g, b)
    """
    return getattr(tokens.colors, semantic_name)


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
    
    # Demo helper functions
    print("\n=== Helper Functions ===")
    print(f"Primary → terminal color: '{rgb_to_terminal_color_name(tokens.colors.primary)}'")
    print(f"Error → terminal color: '{rgb_to_terminal_color_name(tokens.colors.error)}'")
    print(f"Get semantic 'success': {get_semantic_color('success')}")
