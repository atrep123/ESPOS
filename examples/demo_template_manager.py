#!/usr/bin/env python3
"""
Quick demo of Template Manager integration
"""

from ui_designer import UIDesigner
from ui_designer_preview import VisualPreviewWindow


def main():
    # Create designer with default scene
    designer = UIDesigner(width=240, height=320)
    designer.create_scene("main")
    
    # Open preview window (includes Template Manager button)
    preview = VisualPreviewWindow(designer)
    
    print("✅ Template Manager Demo")
    print("   Click '📑 Templates' button in left palette")
    print("   Features:")
    print("   - Browse 3 default templates (Dashboard, Form, Dialog)")
    print("   - Search templates by name/description/tags")
    print("   - Save current scene as template")
    print("   - Apply template to scene")
    print("   - Export/Import templates as JSON")
    print("   - Delete custom templates")
    print("")
    print("Press Ctrl+C to exit")
    
    preview.run()

if __name__ == '__main__':
    main()
