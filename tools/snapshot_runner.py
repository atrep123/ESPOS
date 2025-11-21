#!/usr/bin/env python3
"""
Headless snapshot generator for UI Designer scenes.

Renders PNG and/or ASCII snapshots without opening Tk windows.

Usage:
    python tools/snapshot_runner.py --scene examples/demo_scene.json --out-dir reports/snapshots --png --ascii
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List

# Force headless mode to avoid Tk UI
os.environ.setdefault("ESP32OS_HEADLESS", "1")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui_designer import UIDesigner  # noqa: E402
from ui_designer_preview import VisualPreviewWindow  # noqa: E402


def render_ascii(vp: VisualPreviewWindow) -> List[str]:
    scene = vp.designer.scenes.get(vp.designer.current_scene)
    if not scene:
        return []
    return vp._render_ascii_scene(scene, use_cache=False)  # type: ignore[attr-defined]


def render_png(vp: VisualPreviewWindow, include_grid: bool = True) -> "Image.Image | None":
    scene = vp.designer.scenes.get(vp.designer.current_scene)
    if not scene:
        return None
    try:
        return vp._render_scene_image(  # type: ignore[attr-defined]
            scene,
            background_color=vp.settings.background_color,
            include_grid=include_grid and vp.settings.grid_enabled,
            use_overlays=False,
            highlight_selection=True,
        )
    except Exception:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Headless snapshot generator for UI Designer scenes.")
    parser.add_argument("--scene", required=True, help="Path to scene JSON (ui_designer format).")
    parser.add_argument("--out-dir", default="reports/snapshots", help="Output directory.")
    parser.add_argument("--png", action="store_true", help="Generate PNG snapshot.")
    parser.add_argument("--ascii", action="store_true", help="Generate ASCII snapshot (txt).")
    parser.add_argument("--zoom", type=float, default=4.0, help="Preview zoom (default 4.0).")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    designer = UIDesigner()
    designer.load_from_json(args.scene)
    vp = VisualPreviewWindow(designer)
    vp.settings.zoom = args.zoom
    stem = Path(args.scene).stem
    if args.png:
        img = render_png(vp)
        if img:
            png_path = out_dir / f"{stem}.png"
            img.save(png_path)
            print(f"PNG snapshot written: {png_path}")
        else:
            print("PNG snapshot skipped (render error).")
    if args.ascii:
        lines = render_ascii(vp)
        txt_path = out_dir / f"{stem}.txt"
        txt_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"ASCII snapshot written: {txt_path}")


if __name__ == "__main__":
    main()
