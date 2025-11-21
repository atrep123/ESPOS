#!/usr/bin/env python3
"""
Demo: Design Tokens Migration Example
Shows how to migrate from hardcoded colors/spacing to design tokens.
"""

from design_tokens import tokens, rgb_to_terminal_color_name


# ========================================
# BEFORE: Hardcoded values
# ========================================

def create_button_old_style():
    """Old approach: hardcoded colors and spacing."""
    return {
        "type": "button",
        "x": 20,
        "y": 100,  # Arbitrary pixel position
        "width": 80,  # Arbitrary pixel size
        "height": 30,  # Arbitrary pixel size
        "text": "Submit",
        "border": True,
        "color_fg": "white",  # Hardcoded color name
        "color_bg": "blue",   # Hardcoded color name
        "padding": 8,         # Magic number
    }


def create_dialog_old_style():
    """Old approach: inconsistent spacing."""
    return {
        "type": "panel",
        "x": 50,
        "y": 50,
        "width": 400,   # Random width
        "height": 200,  # Random height
        "border_style": "double",
        "color_fg": "yellow",
        "color_bg": "black",
        "title_padding": 12,  # Different padding than button
        "content_padding": 16,  # Yet another padding value
    }


# ========================================
# AFTER: Using design tokens
# ========================================

def create_button_with_tokens():
    """New approach: design tokens for consistency."""
    return {
        "type": "button",
        "x": tokens.spacing.xl,  # Semantic spacing
        "y": 100,
        "width": tokens.spacing.xl * 5,  # Based on spacing scale
        "height": tokens.spacing.lg,     # Consistent with system
        "text": "Submit",
        "border": True,
        "color_fg": rgb_to_terminal_color_name(tokens.colors.text_primary),
        "color_bg": rgb_to_terminal_color_name(tokens.colors.primary),
        "padding": tokens.spacing.sm,  # Named, not magic number
    }


def create_dialog_with_tokens():
    """New approach: using spacing tokens."""
    return {
        "type": "panel",
        "x": tokens.spacing.xl,
        "y": tokens.spacing.xl,
        "width": tokens.spacing.xl * 20,   # Scale-based sizing
        "height": tokens.spacing.xl * 10,
        "border_style": "double",
        "color_fg": rgb_to_terminal_color_name(tokens.colors.warning),
        "color_bg": rgb_to_terminal_color_name(tokens.colors.surface),
        "title_padding": tokens.spacing.md,    # Consistent spacing
        "content_padding": tokens.spacing.lg,  # System-wide scale
    }


# ========================================
# Animation timing migration
# ========================================

def setup_fade_in_old():
    """Old: magic number duration."""
    return {
        "duration": 200,  # Where does 200ms come from?
        "easing": "ease-in-out",  # String, not standardized
    }


def setup_fade_in_with_tokens():
    """New: semantic animation token."""
    return {
        "duration": tokens.animation.base,  # 160ms, system-wide
        "easing": tokens.animation.ease_out,  # Standardized curve
    }


# ========================================
# Demo output
# ========================================

if __name__ == "__main__":
    print("=== Migration Demo: Before vs After ===\n")
    
    print("BUTTON (old):")
    print(f"  {create_button_old_style()}")
    print()
    
    print("BUTTON (with tokens):")
    print(f"  {create_button_with_tokens()}")
    print()
    
    print("DIALOG (old):")
    print(f"  {create_dialog_old_style()}")
    print()
    
    print("DIALOG (with tokens):")
    print(f"  {create_dialog_with_tokens()}")
    print()
    
    print("ANIMATION (old):")
    print(f"  {setup_fade_in_old()}")
    print()
    
    print("ANIMATION (with tokens):")
    print(f"  {setup_fade_in_with_tokens()}")
    print()
    
    print("=== Benefits ===")
    print("✅ Consistent spacing scale (4px-based)")
    print("✅ Semantic color names (primary, surface, warning)")
    print("✅ No magic numbers (spacing.sm vs 8)")
    print("✅ System-wide changes (update tokens.colors.primary once)")
    print("✅ Better maintainability and design coherence")
