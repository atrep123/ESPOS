#!/usr/bin/env python3
"""
Quick launcher for UI Designer with GUI (Dark Mode)
"""

# Import from preview module (new location)
try:
    from preview.window import VisualPreviewWindow
except ImportError:
    # Fallback to old location
    from ui_designer_preview import VisualPreviewWindow

from ui_designer import UIDesigner

# Create designer with default screen size (128x64 for OLED)
designer = UIDesigner(width=128, height=64)

# Create default scene
designer.create_scene("main")
designer.current_scene = "main"

# Add a welcome label
designer.add_widget(
    'label',
    x=10,
    y=10,
    width=108,
    height=12,
    text="UI Designer",
    align="center"
)

# Launch visual editor with dark theme
print("🌙 Opening UI Designer in Dark Mode...")
print("- Drag widgets to move")
print("- Drag handles to resize")
print("- Double-click to edit properties")
print("- Ctrl+S to save")
print("- Theme: Dark (customizable in dropdown)")

preview = VisualPreviewWindow(designer)
preview.run()
