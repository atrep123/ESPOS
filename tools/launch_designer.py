#!/usr/bin/env python3
"""
Launcher for Visual UI Designer preview.

Usage examples:
  python tools/launch_designer.py                # empty 128x64 scene
  python tools/launch_designer.py --width 320 --height 240
  python tools/launch_designer.py --json test_scene.json
"""

import argparse
import os
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch ESP32OS UI Designer Preview")
    parser.add_argument("--json", type=str, default="", help="Path to design JSON to open")
    parser.add_argument("--width", type=int, default=128, help="Canvas width when creating a new scene")
    parser.add_argument("--height", type=int, default=64, help="Canvas height when creating a new scene")
    parser.add_argument("--scene", type=str, default="demo", help="Name of the created scene when not loading JSON")
    args = parser.parse_args()

    # Ensure we can import project modules when launched from tools/
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    try:
        from ui_designer import UIDesigner
        from ui_designer_preview import VisualPreviewWindow
    except Exception as e:
        print(f"Failed to import designer modules: {e}")
        print("Make sure project dependencies are installed: pip install -r requirements.txt")
        return 1

    designer = UIDesigner(args.width, args.height)

    if args.json:
        try:
            designer.load_from_json(args.json)
        except Exception as e:
            print(f"Error loading JSON '{args.json}': {e}")
            return 1
    else:
        designer.create_scene(args.scene)

    try:
        preview = VisualPreviewWindow(designer)
        preview.run()
    except Exception as e:
        print(f"Preview failed to launch: {e}")
        print("Tip: This requires Tkinter and Pillow. On Windows, Tkinter ships with Python.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
