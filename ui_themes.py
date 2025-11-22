#!/usr/bin/env python3
"""
Theme System for UI Designer
Pre-built color schemes and theme management
"""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

from design_tokens import COLOR_HEX


class ThemePreset(Enum):
    """Pre-built theme presets"""
    DARK = "dark"
    LIGHT = "light"
    CYBERPUNK = "cyberpunk"
    RETRO = "retro"
    MINIMAL = "minimal"
    NORD = "nord"
    SOLARIZED = "solarized"
    DRACULA = "dracula"
    MONOKAI = "monokai"
    MATRIX = "matrix"


@dataclass
class ColorScheme:
    """Color scheme definition"""
    # Base colors
    background: str
    foreground: str
    
    # UI element colors
    primary: str
    secondary: str
    accent: str
    
    # Status colors
    success: str
    warning: str
    error: str
    info: str
    
    # Widget-specific colors
    button_bg: str
    button_fg: str
    button_active: str
    
    input_bg: str
    input_fg: str
    input_border: str
    
    panel_bg: str
    panel_fg: str
    panel_border: str
    
    # Text colors
    text_primary: str
    text_secondary: str
    text_muted: str
    
    # Border colors
    border_light: str
    border_normal: str
    border_heavy: str
    
    # Special effects
    shadow: str
    highlight: str
    selection: str


@dataclass
class Theme:
    """Complete theme definition"""
    name: str
    description: str
    author: str
    version: str
    colors: ColorScheme
    
    # Font settings
    font_family: str = "monospace"
    font_size: int = 8
    
    # Widget defaults
    default_border_style: str = "single"
    default_padding: int = 1
    default_margin: int = 0
    
    # Animation settings
    animation_duration: int = 300  # ms
    easing_function: str = "ease-in-out"
    
    # Metadata
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class ThemeManager:
    """Manage and apply themes"""
    
    def __init__(self):
        self.themes: Dict[str, Theme] = {}
        self.current_theme: Optional[str] = None
        
        # Register built-in themes
        self._register_builtin_themes()
    
    def _register_builtin_themes(self):
        """Register all built-in themes"""
        
        # Dark Theme (Default)
        dark = Theme(
            name="Dark",
            description="Classic dark theme with high contrast",
            author="ESP32OS",
            version="1.0",
            colors=ColorScheme(
                background=COLOR_HEX["theme_default_bg"],
                foreground=COLOR_HEX["theme_default_text"],
                primary=COLOR_HEX["theme_default_primary"],
                secondary=COLOR_HEX["legacy_gray16"],
                accent=COLOR_HEX["legacy_orange"],
                success=COLOR_HEX["legacy_green_mid2"],
                warning=COLOR_HEX["legacy_orange_warm"],
                error=COLOR_HEX.get("legacy_red_bright", COLOR_HEX["legacy_red"]),
                info=COLOR_HEX.get("legacy_blue_bright", COLOR_HEX["theme_default_primary"]),
                button_bg=COLOR_HEX["legacy_gray3"],
                button_fg=COLOR_HEX["text_primary"],
                button_active=COLOR_HEX["legacy_blue"],
                input_bg=COLOR_HEX["legacy_gray5"],
                input_fg=COLOR_HEX["text_primary"],
                input_border=COLOR_HEX["legacy_gray2"],
                panel_bg=COLOR_HEX["legacy_gray17"],
                panel_fg=COLOR_HEX["legacy_gray_light"],
                panel_border=COLOR_HEX["legacy_gray3"],
                text_primary=COLOR_HEX["text_primary"],
                text_secondary=COLOR_HEX["legacy_gray_light"],
                text_muted=COLOR_HEX["legacy_gray2"],
                border_light=COLOR_HEX["legacy_gray3"],
                border_normal=COLOR_HEX["legacy_gray2"],
                border_heavy=COLOR_HEX["legacy_gray7"],
                shadow=COLOR_HEX["shadow"],
                highlight=COLOR_HEX["text_primary"],
                selection=COLOR_HEX["legacy_blue"]
            ),
            tags=["dark", "classic", "high-contrast"]
        )
        
        # Light Theme
        light = Theme(
            name="Light",
            description="Clean light theme for bright environments",
            author="ESP32OS",
            version="1.0",
            colors=ColorScheme(
                background="#FFFFFF",
                foreground="#000000",
                primary=COLOR_HEX["legacy_blue"],
                secondary=COLOR_HEX["legacy_gray_lighter"],
                accent=COLOR_HEX["legacy_orange"],
                success=COLOR_HEX["legacy_green_soft"],
                warning=COLOR_HEX["legacy_orange_deep"],
                error=COLOR_HEX["legacy_red_dark"],
                info=COLOR_HEX["legacy_blue_mid"],
                button_bg=COLOR_HEX["legacy_gray18"],
                button_fg=COLOR_HEX["shadow"],
                button_active=COLOR_HEX["legacy_blue"],
                input_bg=COLOR_HEX["legacy_gray19"],
                input_fg=COLOR_HEX["shadow"],
                input_border=COLOR_HEX["legacy_gray_light"],
                panel_bg=COLOR_HEX["legacy_gray20"],
                panel_fg=COLOR_HEX["legacy_gray3"],
                panel_border=COLOR_HEX["legacy_gray6"],
                text_primary=COLOR_HEX["shadow"],
                text_secondary=COLOR_HEX["legacy_gray11"],
                text_muted=COLOR_HEX["legacy_gray7"],
                border_light=COLOR_HEX["legacy_gray18"],
                border_normal=COLOR_HEX["legacy_gray_light"],
                border_heavy=COLOR_HEX["legacy_gray7"],
                shadow=COLOR_HEX["legacy_gray_light"],
                highlight=COLOR_HEX["shadow"],
                selection=COLOR_HEX["legacy_blue"]
            ),
            tags=["light", "clean", "minimal"]
        )
        
        # Cyberpunk Theme
        cyberpunk = Theme(
            name="Cyberpunk",
            description="Neon-infused cyberpunk aesthetic",
            author="ESP32OS",
            version="1.0",
            colors=ColorScheme(
                background="#0A0E27",
                foreground="#00FFFF",
                primary=COLOR_HEX["legacy_dracula_pink"],
                secondary=COLOR_HEX["legacy_navyslate"],
                accent=COLOR_HEX["legacy_yellow"],
                success=COLOR_HEX["legacy_green"],
                warning=COLOR_HEX["legacy_orange_soft"],
                error=COLOR_HEX["legacy_pink_hot"],
                info=COLOR_HEX["legacy_blue_cyan"],
                button_bg=COLOR_HEX["legacy_navyslate"],
                button_fg=COLOR_HEX["legacy_dracula_cyan"],
                button_active=COLOR_HEX["legacy_dracula_pink"],
                input_bg=COLOR_HEX["legacy_navy_ink"],
                input_fg=COLOR_HEX["legacy_dracula_cyan"],
                input_border=COLOR_HEX["legacy_dracula_pink"],
                panel_bg=COLOR_HEX["legacy_navy_dark"],
                panel_fg=COLOR_HEX["legacy_dracula_cyan"],
                panel_border=COLOR_HEX["legacy_dracula_pink"],
                text_primary=COLOR_HEX["legacy_dracula_cyan"],
                text_secondary=COLOR_HEX["legacy_cyan_soft"],
                text_muted=COLOR_HEX["legacy_teal_muted"],
                border_light=COLOR_HEX["legacy_dracula_pink"],
                border_normal=COLOR_HEX["legacy_dracula_cyan"],
                border_heavy=COLOR_HEX["legacy_yellow"],
                shadow=COLOR_HEX["legacy_navy_base"],
                highlight=COLOR_HEX["legacy_dracula_cyan"],
                selection=COLOR_HEX["legacy_dracula_pink"]
            ),
            tags=["dark", "neon", "vibrant", "cyberpunk"]
        )
        
        # Retro Terminal Theme
        retro = Theme(
            name="Retro",
            description="Classic amber/green terminal aesthetic",
            author="ESP32OS",
            version="1.0",
            colors=ColorScheme(
                background=COLOR_HEX["theme_default_bg"],
                foreground=COLOR_HEX["legacy_green"],
                primary=COLOR_HEX["legacy_green_dark"],
                secondary=COLOR_HEX["legacy_green_deep"],
                accent=COLOR_HEX["legacy_orange_bright"],
                success=COLOR_HEX["legacy_green"],
                warning=COLOR_HEX["legacy_hc_accent"] if "legacy_hc_accent" in COLOR_HEX else COLOR_HEX["theme_hc_accent"],
                error=COLOR_HEX["legacy_orange_hot"],
                info=COLOR_HEX["legacy_cyan_mid"],
                button_bg=COLOR_HEX["legacy_green_ultradark"],
                button_fg=COLOR_HEX["legacy_green"],
                button_active=COLOR_HEX["legacy_green_dark"],
                input_bg=COLOR_HEX["theme_default_bg"],
                input_fg=COLOR_HEX["legacy_green"],
                input_border=COLOR_HEX["legacy_green_dark"],
                panel_bg=COLOR_HEX["theme_default_bg"],
                panel_fg=COLOR_HEX["legacy_green_mid"],
                panel_border=COLOR_HEX["legacy_green_dark"],
                text_primary=COLOR_HEX["legacy_green"],
                text_secondary=COLOR_HEX["legacy_green_mid"],
                text_muted=COLOR_HEX["legacy_green_base"],
                border_light=COLOR_HEX["legacy_green_deep"],
                border_normal=COLOR_HEX["legacy_green_dark"],
                border_heavy=COLOR_HEX["legacy_green"],
                shadow=COLOR_HEX["shadow"],
                highlight=COLOR_HEX["legacy_green"],
                selection=COLOR_HEX["legacy_green_dark"]
            ),
            tags=["dark", "retro", "terminal", "vintage"]
        )
        
        # Minimal Theme
        minimal = Theme(
            name="Minimal",
            description="Ultra-clean monochrome design",
            author="ESP32OS",
            version="1.0",
            colors=ColorScheme(
                background=COLOR_HEX["text_primary"],
                foreground=COLOR_HEX["shadow"],
                primary=COLOR_HEX["shadow"],
                secondary=COLOR_HEX["legacy_gray21"],
                accent=COLOR_HEX["legacy_gray2"],
                success=COLOR_HEX["shadow"],
                warning=COLOR_HEX["legacy_gray2"],
                error=COLOR_HEX["legacy_gray3"],
                info=COLOR_HEX["shadow"],
                button_bg=COLOR_HEX["shadow"],
                button_fg=COLOR_HEX["text_primary"],
                button_active=COLOR_HEX["legacy_gray2"],
                input_bg=COLOR_HEX["text_primary"],
                input_fg=COLOR_HEX["shadow"],
                input_border=COLOR_HEX["shadow"],
                panel_bg=COLOR_HEX["text_primary"],
                panel_fg=COLOR_HEX["shadow"],
                panel_border=COLOR_HEX["shadow"],
                text_primary=COLOR_HEX["shadow"],
                text_secondary=COLOR_HEX["legacy_gray2"],
                text_muted=COLOR_HEX["legacy_gray_light"],
                border_light=COLOR_HEX["legacy_gray_light"],
                border_normal=COLOR_HEX["shadow"],
                border_heavy=COLOR_HEX["shadow"],
                shadow=COLOR_HEX["legacy_gray_light"],
                highlight=COLOR_HEX["shadow"],
                selection=COLOR_HEX["shadow"]
            ),
            default_border_style="single",
            tags=["light", "minimal", "monochrome"]
        )
        
        # Nord Theme
        nord = Theme(
            name="Nord",
            description="Arctic, north-bluish color palette",
            author="ESP32OS",
            version="1.0",
            colors=ColorScheme(
                background=COLOR_HEX["legacy_nord_base"],
                foreground=COLOR_HEX["legacy_gray_soft"],
                primary=COLOR_HEX["legacy_nord_cyan"],
                secondary=COLOR_HEX["legacy_nord_bg"],
                accent=COLOR_HEX["legacy_nord_blue2"],
                success=COLOR_HEX["legacy_nord_green"],
                warning=COLOR_HEX["legacy_nord_yellow"],
                error=COLOR_HEX["legacy_nord_red"],
                info=COLOR_HEX["legacy_nord_cyan"],
                button_bg=COLOR_HEX["legacy_nord_slate2"],
                button_fg=COLOR_HEX["legacy_gray_soft"],
                button_active=COLOR_HEX["legacy_nord_cyan"],
                input_bg=COLOR_HEX["legacy_nord_bg"],
                input_fg=COLOR_HEX["legacy_gray_soft"],
                input_border=COLOR_HEX["legacy_nord_slate"],
                panel_bg=COLOR_HEX["legacy_nord_base"],
                panel_fg=COLOR_HEX["legacy_nord_light"],
                panel_border=COLOR_HEX["legacy_nord_slate"],
                text_primary=COLOR_HEX["legacy_gray_soft"],
                text_secondary=COLOR_HEX["legacy_nord_light"],
                text_muted=COLOR_HEX["legacy_nord_slate"],
                border_light=COLOR_HEX["legacy_nord_bg"],
                border_normal=COLOR_HEX["legacy_nord_slate"],
                border_heavy=COLOR_HEX["legacy_nord_slate3"],
                shadow=COLOR_HEX["legacy_gray22"],
                highlight=COLOR_HEX["legacy_gray_soft"],
                selection=COLOR_HEX["legacy_nord_cyan"]
            ),
            tags=["dark", "nord", "arctic", "calm"]
        )
        
        # Dracula Theme
        dracula = Theme(
            name="Dracula",
            description="Dark theme with purple accents",
            author="ESP32OS",
            version="1.0",
            colors=ColorScheme(
                background=COLOR_HEX["legacy_dracula_bg"],
                foreground=COLOR_HEX["legacy_offwhite"],
                primary=COLOR_HEX["legacy_nord_purple"],
                secondary=COLOR_HEX["legacy_dracula_slate"],
                accent=COLOR_HEX["legacy_dracula_pink"],
                success=COLOR_HEX["legacy_dracula_green"],
                warning=COLOR_HEX["legacy_dracula_yellow"],
                error=COLOR_HEX["legacy_dracula_red"],
                info=COLOR_HEX["legacy_dracula_cyan"],
                button_bg=COLOR_HEX["legacy_dracula_slate"],
                button_fg=COLOR_HEX["legacy_offwhite"],
                button_active=COLOR_HEX["legacy_nord_purple"],
                input_bg=COLOR_HEX["legacy_dracula_bg"],
                input_fg=COLOR_HEX["legacy_offwhite"],
                input_border=COLOR_HEX["legacy_nord_blue"],
                panel_bg=COLOR_HEX["legacy_dracula_bg"],
                panel_fg=COLOR_HEX["legacy_offwhite"],
                panel_border=COLOR_HEX["legacy_nord_blue"],
                text_primary=COLOR_HEX["legacy_offwhite"],
                text_secondary=COLOR_HEX["legacy_offwhite"],
                text_muted=COLOR_HEX["legacy_nord_blue"],
                border_light=COLOR_HEX["legacy_dracula_slate"],
                border_normal=COLOR_HEX["legacy_nord_blue"],
                border_heavy=COLOR_HEX["legacy_nord_purple"],
                shadow=COLOR_HEX["legacy_gray23"],
                highlight=COLOR_HEX["legacy_offwhite"],
                selection=COLOR_HEX["legacy_nord_purple"]
            ),
            tags=["dark", "dracula", "purple"]
        )
        
        # Matrix Theme
        matrix = Theme(
            name="Matrix",
            description="Falling code aesthetic",
            author="ESP32OS",
            version="1.0",
            colors=ColorScheme(
                background="#000000",
                foreground="#00FF41",
                primary="#008F11",
                secondary="#003B00",
                accent="#00FF41",
                success="#00FF41",
                warning="#AAFF00",
                error="#FF4444",
                info="#00FFAA",
                button_bg="#001100",
                button_fg="#00FF41",
                button_active="#008F11",
                input_bg="#000000",
                input_fg="#00FF41",
                input_border="#008F11",
                panel_bg="#000000",
                panel_fg="#00DD33",
                panel_border="#008F11",
                text_primary="#00FF41",
                text_secondary="#00DD33",
                text_muted="#005500",
                border_light="#003300",
                border_normal="#008F11",
                border_heavy="#00FF41",
                shadow="#000000",
                highlight="#00FF41",
                selection="#008F11"
            ),
            tags=["dark", "matrix", "green", "hacker"]
        )
        
        # Register all themes
        for theme in [dark, light, cyberpunk, retro, minimal, nord, dracula, matrix]:
            self.register_theme(theme)
        
        # Set default
        self.current_theme = "Dark"
    
    def register_theme(self, theme: Theme):
        """Register a theme"""
        self.themes[theme.name] = theme
    
    def get_theme(self, name: str) -> Optional[Theme]:
        """Get theme by name"""
        return self.themes.get(name)
    
    def list_themes(self) -> List[str]:
        """List all available themes"""
        return list(self.themes.keys())
    
    def search_themes(self, tag: str) -> List[Theme]:
        """Search themes by tag"""
        return [t for t in self.themes.values() if tag in t.tags]
    
    def apply_theme_to_widget(self, widget_config: Dict[str, Any], 
                             widget_type: str = "default") -> Dict[str, Any]:
        """Apply current theme colors to widget config"""
        if not self.current_theme:
            return widget_config
        
        theme = self.themes[self.current_theme]
        colors = theme.colors
        
        # Apply colors based on widget type
        if widget_type == "button":
            widget_config["color_bg"] = colors.button_bg
            widget_config["color_fg"] = colors.button_fg
        elif widget_type in ["textbox", "input"]:
            widget_config["color_bg"] = colors.input_bg
            widget_config["color_fg"] = colors.input_fg
        elif widget_type == "panel":
            widget_config["color_bg"] = colors.panel_bg
            widget_config["color_fg"] = colors.panel_fg
        else:
            widget_config["color_bg"] = colors.background
            widget_config["color_fg"] = colors.foreground
        
        # Apply border style
        if "border_style" not in widget_config:
            widget_config["border_style"] = theme.default_border_style
        
        # Apply padding/margin
        if "padding_x" not in widget_config:
            widget_config["padding_x"] = theme.default_padding
        if "margin_x" not in widget_config:
            widget_config["margin_x"] = theme.default_margin
        
        return widget_config
    
    def export_theme(self, theme_name: str, filename: str):
        """Export theme to JSON file"""
        theme = self.themes.get(theme_name)
        if not theme:
            raise ValueError(f"Theme '{theme_name}' not found")
        
        theme_dict = {
            "name": theme.name,
            "description": theme.description,
            "author": theme.author,
            "version": theme.version,
            "colors": asdict(theme.colors),
            "font_family": theme.font_family,
            "font_size": theme.font_size,
            "default_border_style": theme.default_border_style,
            "default_padding": theme.default_padding,
            "default_margin": theme.default_margin,
            "animation_duration": theme.animation_duration,
            "easing_function": theme.easing_function,
            "tags": theme.tags
        }
        
        with open(filename, 'w') as f:
            json.dump(theme_dict, f, indent=2)
    
    def import_theme(self, filename: str) -> Theme:
        """Import theme from JSON file"""
        with open(filename, 'r') as f:
            data = json.load(f)
        
        colors = ColorScheme(**data["colors"])
        theme = Theme(
            name=data["name"],
            description=data["description"],
            author=data["author"],
            version=data["version"],
            colors=colors,
            font_family=data.get("font_family", "monospace"),
            font_size=data.get("font_size", 8),
            default_border_style=data.get("default_border_style", "single"),
            default_padding=data.get("default_padding", 1),
            default_margin=data.get("default_margin", 0),
            animation_duration=data.get("animation_duration", 300),
            easing_function=data.get("easing_function", "ease-in-out"),
            tags=data.get("tags", [])
        )
        
        self.register_theme(theme)
        return theme
    
    def create_custom_theme(self, name: str, base_theme: str = "Dark") -> Theme:
        """Create custom theme based on existing theme"""
        base = self.themes.get(base_theme)
        if not base:
            raise ValueError(f"Base theme '{base_theme}' not found")
        
        # Deep copy
        colors_dict = asdict(base.colors)
        new_colors = ColorScheme(**colors_dict)
        
        new_theme = Theme(
            name=name,
            description=f"Custom theme based on {base_theme}",
            author="User",
            version="1.0",
            colors=new_colors,
            font_family=base.font_family,
            font_size=base.font_size,
            default_border_style=base.default_border_style,
            default_padding=base.default_padding,
            default_margin=base.default_margin,
            animation_duration=base.animation_duration,
            easing_function=base.easing_function,
            tags=["custom"]
        )
        
        self.register_theme(new_theme)
        return new_theme
    
    def get_color_palette(self, theme_name: Optional[str] = None) -> Dict[str, str]:
        """Get simplified color palette from theme"""
        if not theme_name:
            theme_name = self.current_theme
        
        theme = self.themes.get(theme_name)
        if not theme:
            return {}
        
        return {
            "bg": theme.colors.background,
            "fg": theme.colors.foreground,
            "primary": theme.colors.primary,
            "accent": theme.colors.accent,
            "success": theme.colors.success,
            "warning": theme.colors.warning,
            "error": theme.colors.error,
            "info": theme.colors.info,
        }
    
    def preview_theme(self, theme_name: str) -> str:
        """Generate ASCII preview of theme"""
        theme = self.themes.get(theme_name)
        if not theme:
            return f"Theme '{theme_name}' not found"
        
        c = theme.colors
        
        preview = f"""
╔══════════════════════════════════════════════════════════╗
║ {theme.name:<54} ║
╠══════════════════════════════════════════════════════════╣
║ {theme.description:<54} ║
║ Author: {theme.author:<47} ║
╠══════════════════════════════════════════════════════════╣
║ COLOR PALETTE                                            ║
╠══════════════════════════════════════════════════════════╣
║ Background:  {c.background:<43} ║
║ Foreground:  {c.foreground:<43} ║
║ Primary:     {c.primary:<43} ║
║ Accent:      {c.accent:<43} ║
║ Success:     {c.success:<43} ║
║ Warning:     {c.warning:<43} ║
║ Error:       {c.error:<43} ║
║ Info:        {c.info:<43} ║
╠══════════════════════════════════════════════════════════╣
║ WIDGET COLORS                                            ║
╠══════════════════════════════════════════════════════════╣
║ Button BG:   {c.button_bg:<43} ║
║ Button FG:   {c.button_fg:<43} ║
║ Input BG:    {c.input_bg:<43} ║
║ Input FG:    {c.input_fg:<43} ║
║ Panel BG:    {c.panel_bg:<43} ║
║ Panel FG:    {c.panel_fg:<43} ║
╠══════════════════════════════════════════════════════════╣
║ Tags: {', '.join(theme.tags):<50} ║
╚══════════════════════════════════════════════════════════╝
"""
        return preview


def main():
    """Demo theme system"""
    print("🎨 UI DESIGNER THEME SYSTEM\n")
    
    manager = ThemeManager()
    
    print("Available Themes:")
    for theme_name in manager.list_themes():
        theme = manager.get_theme(theme_name)
        print(f"  • {theme_name} - {theme.description}")
    
    print("\n" + "="*60)
    
    # Preview each theme
    for theme_name in ["Dark", "Cyberpunk", "Retro", "Nord"]:
        print(manager.preview_theme(theme_name))
    
    # Export example
    print("\n📦 Exporting 'Cyberpunk' theme...")
    manager.export_theme("Cyberpunk", "theme_cyberpunk.json")
    print("✓ Saved to theme_cyberpunk.json")
    
    # Create custom theme
    print("\n🎨 Creating custom theme...")
    custom = manager.create_custom_theme("MyTheme", "Nord")
    custom.colors.accent = "#FF6600"
    print(f"✓ Created '{custom.name}' based on Nord")
    
    print("\n✅ Theme system ready!")


if __name__ == "__main__":
    main()
