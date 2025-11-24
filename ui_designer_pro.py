#!/usr/bin/env python3
"""
UI Designer Pro - Complete Integration
All features combined: Preview, Themes, Components, Animations, Responsive
"""

import atexit
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from ui_designer import UIDesigner
from ui_models import WidgetConfig, WidgetType, BorderStyle
from ui_themes import ThemeManager, Theme
from ui_components import ComponentLibrary, ComponentTemplate
from ui_animations import AnimationDesigner, Animation
from ui_responsive import ResponsiveLayoutSystem, LayoutConstraints


class _SafeStream:
    """Wrapper to prevent stdout/stderr crashes on consoles without Unicode support."""

    def __init__(self, stream):
        if stream is None:
            stream = open(os.devnull, "w", encoding="utf-8", errors="ignore")
        self.stream = stream

    def write(self, data):
        try:
            return self.stream.write(data)
        except (OSError, ValueError):
            return 0

    def flush(self):
        try:
            return self.stream.flush()
        except (OSError, ValueError):
            return None

    def __getattr__(self, name):
        return getattr(self.stream, name)


def _configure_stdio() -> None:
    """Ensure stdout/stderr can print Unicode without crashing on legacy codepages."""
    def _wrap(stream):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
        return _SafeStream(stream)

    sys.stdout = _wrap(sys.stdout)
    sys.stderr = _wrap(sys.stderr)


_INSTANCE_LOCK_HANDLE: Optional[object] = None


def _release_single_instance_lock() -> None:
    """Release the single-instance lock if held."""
    global _INSTANCE_LOCK_HANDLE
    handle = _INSTANCE_LOCK_HANDLE
    _INSTANCE_LOCK_HANDLE = None
    if handle is None:
        return
    try:
        if os.name == "nt":
            import msvcrt
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
        handle.close()
    except Exception:
        pass


def _acquire_single_instance_lock() -> bool:
    """Prevent multiple instances from spawning repeatedly (helps avoid respawn storms)."""
    if os.environ.get("ESP32OS_DISABLE_SINGLE_INSTANCE") == "1":
        return True
    lock_path = Path(tempfile.gettempdir()) / "esp32os_ui_designer.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        handle = open(lock_path, "w")
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False
    except Exception:
        return False
    global _INSTANCE_LOCK_HANDLE
    _INSTANCE_LOCK_HANDLE = handle
    atexit.register(_release_single_instance_lock)
    return True


class UIDesignerPro:
    """Professional UI Designer with all advanced features"""
    
    def __init__(self, width: int = 128, height: int = 64):
        # Core designer
        self.designer = UIDesigner(width, height)
        
        # Advanced features
        self.theme_manager = ThemeManager()
        self.component_library = ComponentLibrary()
        self.animation_designer = AnimationDesigner()
        self.responsive_system = ResponsiveLayoutSystem()
        
        # Set default theme
        self.theme_manager.current_theme = "Dark"
    
    def create_scene(self, name: str):
        """Create new scene"""
        self.designer.create_scene(name)
    
    def set_theme(self, theme_name: str):
        """Apply theme"""
        if theme_name not in self.theme_manager.themes:
            raise ValueError(f"Theme '{theme_name}' not found")
        self.theme_manager.current_theme = theme_name
        print(f"[OK] Theme set to '{theme_name}'")
    
    def add_component(self, component_name: str, x: int = 0, y: int = 0, 
                     params: Optional[Dict[str, Any]] = None):
        """Add component from library"""
        widgets = self.component_library.instantiate_component(component_name, x, y, params)
        
        # Apply current theme to widgets
        for widget in widgets:
            themed_widget = self.theme_manager.apply_theme_to_widget(
                widget.__dict__, 
                widget.type
            )
            # Update widget with themed properties
            for key, value in themed_widget.items():
                if hasattr(widget, key):
                    setattr(widget, key, value)
        
        # Add to scene
        scene = self.designer.scenes.get(self.designer.current_scene)
        if scene:
            scene.widgets.extend(widgets)
            self.designer._save_state()
        
        print(f"[OK] Added component '{component_name}' with {len(widgets)} widgets")
        return widgets
    
    def add_widget_with_theme(self, widget_type: WidgetType, **kwargs):
        """Add widget with current theme applied"""
        # Apply theme
        themed_props = self.theme_manager.apply_theme_to_widget(kwargs, widget_type.value)
        
        # Create WidgetConfig
        widget = WidgetConfig(
            type=widget_type.value,
            x=themed_props.get('x', 0),
            y=themed_props.get('y', 0),
            width=themed_props.get('width', 20),
            height=themed_props.get('height', 10),
            text=themed_props.get('text', ''),
            color_bg=themed_props.get('color_bg', 'black'),
            color_fg=themed_props.get('color_fg', 'white'),
            border=themed_props.get('border', False),
            border_style=themed_props.get('border_style', 'single'),
        )
        
        # Add widget
        self.designer.add_widget(widget)
    
    def add_animation(self, animation_name: str, widget_index: int):
        """Add animation to widget"""
        self.animation_designer.play_animation(animation_name, widget_index)
        print(f"[OK] Animation '{animation_name}' added to widget {widget_index}")
    
    def make_responsive(self, from_size: tuple, to_size: tuple, mode: str = "proportional"):
        """Convert current scene to responsive layout"""
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            return
        
        from_w, from_h = from_size
        to_w, to_h = to_size
        
        # Scale all widgets
        for widget in scene.widgets:
            widget_dict = widget.__dict__
            scaled = self.responsive_system.scale_layout(
                widget_dict, from_w, from_h, to_w, to_h, mode
            )
            
            # Update widget
            for key, value in scaled.items():
                if hasattr(widget, key):
                    setattr(widget, key, value)
        
        # Update scene dimensions
        scene.width = to_w
        scene.height = to_h
        
        print(f"[OK] Scene scaled from {from_w}x{from_h} to {to_w}x{to_h} ({mode})")
    
    def export_complete(self, base_filename: str):
        """Export everything: design, theme, animations, responsive config"""
        # Export design
        self.designer.save_to_json(f"{base_filename}.json")
        
        # Export current theme
        if self.theme_manager.current_theme:
            self.theme_manager.export_theme(
                self.theme_manager.current_theme,
                f"{base_filename}_theme.json"
            )
        
        # Export animations
        for anim_name in self.animation_designer.list_animations():
            if anim_name in ["FadeIn", "SlideInLeft", "Bounce"]:  # Export selected
                self.animation_designer.export_animation(
                    anim_name,
                    f"{base_filename}_anim_{anim_name.lower()}.json"
                )
        
        print(f"[OK] Complete export saved:")
        print(f"  - {base_filename}.json (design)")
        print(f"  - {base_filename}_theme.json (theme)")
        print(f"  - {base_filename}_anim_*.json (animations)")
    
    def launch_preview(self):
        """Launch visual preview window"""
        try:
            from ui_designer_preview import VisualPreviewWindow
            preview = VisualPreviewWindow(self.designer)
            preview.run()
        except ImportError as e:
            print(f"[WARN] Preview requires tkinter and PIL: {e}")
            print("  Install with: pip install pillow")
    
    def show_stats(self):
        """Show designer statistics"""
        scene = self.designer.scenes.get(self.designer.current_scene)
        
        print("\n" + "="*60)
        print("UI DESIGNER PRO - STATISTICS")
        print("="*60)
        print(f"Current Scene: {self.designer.current_scene}")
        print(f"Display Size:  {self.designer.width}x{self.designer.height}")
        print(f"Current Theme: {self.theme_manager.current_theme}")
        print()

        if scene:
            print(f"Widgets:       {len(scene.widgets)}")
            widget_types = {}
            for w in scene.widgets:
                widget_types[w.type] = widget_types.get(w.type, 0) + 1
            for wtype, count in sorted(widget_types.items()):
                print(f"  - {wtype:12} {count:3d}")

        print()
        print(f"Available Themes:      {len(self.theme_manager.themes)}")
        print(f"Available Components:  {len(self.component_library.components)}")
        print(f"Available Animations:  {len(self.animation_designer.animations)}")
        print(f"Available Transitions: {len(self.animation_designer.transitions)}")
        print("="*60)


def main():
    """Demo UI Designer Pro"""
    _configure_stdio()
    if not _acquire_single_instance_lock():
        print("[WARN] Another ESP32OS UI Designer instance is already running; exiting.")
        return
    print("UI DESIGNER PRO - COMPLETE EDITION\n")
    print("All features integrated:")
    print("  - Visual Preview Window")
    print("  - Theme System (8 built-in themes)")
    print("  - Component Library (9 pre-built components)")
    print("  - Animation Designer (6 animations, 8 transitions)")
    print("  - Responsive Layout System")
    print()
    
    # Create designer
    designer_pro = UIDesignerPro(128, 64)
    designer_pro.create_scene("pro_demo")
    
    # Set theme
    print("Setting theme...")
    designer_pro.set_theme("Cyberpunk")
    
    # Add components
    print("\nAdding components...")
    designer_pro.add_component("StatusBar", x=0, y=54)
    designer_pro.add_component("CardWidget", x=5, y=5)
    
    # Add custom widgets with theme
    print("\nAdding custom widgets...")
    designer_pro.add_widget_with_theme(
        WidgetType.BUTTON,
        x=70, y=10, width=50, height=12,
        text="Themed Button"
    )
    
    # Show current state
    print("\nCurrent Design (ASCII preview):")
    preview = designer_pro.designer.preview_ascii()
    safe_preview = preview.encode("ascii", "replace").decode("ascii")
    print(safe_preview)
    
    # Show stats
    designer_pro.show_stats()
    
    # Export
    print("\nExporting...")
    designer_pro.export_complete("ui_designer_pro_demo")
    
    # Make responsive version
    print("\nCreating responsive versions...")
    designer_pro.make_responsive((128, 64), (320, 240), "proportional")
    designer_pro.designer.save_to_json("ui_designer_pro_demo_320x240.json")
    
    print("\nUI Designer Pro demo complete!")
    print("\nNext steps:")
    print("  - Run: python ui_designer_preview.py (launch visual editor)")
    print("  - Run: python ui_themes.py (preview all themes)")
    print("  - Run: python ui_components.py (browse component library)")
    print("  - Run: python ui_animations.py (test animation system)")
    print("  - Run: python ui_responsive.py (test responsive layouts)")


if __name__ == "__main__":
    main()
