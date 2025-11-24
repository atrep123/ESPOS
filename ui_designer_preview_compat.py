#!/usr/bin/env python3
"""
Visual Preview Window for UI Designer - COMPATIBILITY LAYER
This file maintains backward compatibility by re-exporting from the new preview/ package.

The actual implementation has been refactored into:
- preview/settings.py - PreviewSettings dataclass
- preview/window.py - VisualPreviewWindow (main class - to be extracted)
- preview/animation_editor.py - AnimationEditorWindow
- preview/rendering.py - Rendering helper functions
"""

from __future__ import annotations

# Re-export from new modular structure
from preview import AnimationEditorWindow, PreviewSettings, VisualPreviewWindow

# Maintain compatibility
__all__ = ["PreviewSettings", "VisualPreviewWindow", "AnimationEditorWindow"]


# Entry point for CLI usage
if __name__ == "__main__":
    import argparse
    import sys

    # CLI arguments preserved for backward compatibility
    parser = argparse.ArgumentParser(description="UI Designer Preview (headless)")
    parser.add_argument("--json", help="Load JSON file in headless mode")
    parser.add_argument("--out-png", help="Export PNG")
    parser.add_argument("--out-html", help="Export HTML")
    parser.add_argument("--width", type=int, help="Canvas width")
    parser.add_argument("--height", type=int, help="Canvas height")

    args = parser.parse_args()

    if args.json:
        print(f"[preview-compat] Headless mode requested for {args.json}")
        print("[preview-compat] Full headless support to be implemented in preview.window")
        sys.exit(1)
    else:
        print(
            "[preview-compat] No CLI args; "
            "use as import: from preview import VisualPreviewWindow"
        )
        sys.exit(0)
