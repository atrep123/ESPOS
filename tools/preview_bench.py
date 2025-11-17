#!/usr/bin/env python3
"""
Lightweight preview renderer micro-benchmark (headless).

- Builds a small sample scene
- Runs N renders of ASCII and (optionally) image pipeline
- Prints timing summary

Usage examples (PowerShell):
    python tools/preview_bench.py --iters 200 --widgets 24
    python tools/preview_bench.py --iters 200 --widgets 24 --image
"""

import argparse
import os
import statistics
import sys
import time
from pathlib import Path
from typing import List

# Force headless to avoid Tk
os.environ.setdefault("ESP32OS_HEADLESS", "1")

# Add repo root to import path to allow running from tools/
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui_designer import UIDesigner, WidgetType
from ui_designer_preview import VisualPreviewWindow


def build_sample_scene(width: int, height: int, widgets: int):
    d = UIDesigner(width, height)
    d.create_scene("bench")
    # Place a simple grid of mixed widgets
    x, y = 2, 2
    col = 0
    cols = max(1, width // 40)
    for i in range(widgets):
        kind = [
            WidgetType.BOX if hasattr(WidgetType, 'BOX') else WidgetType.PANEL,
            WidgetType.LABEL,
            WidgetType.BUTTON,
            WidgetType.PROGRESSBAR,
            WidgetType.SLIDER,
            WidgetType.CHECKBOX,
            WidgetType.GAUGE,
        ][i % 7]
        w = 36 if kind != WidgetType.PROGRESSBAR else min(60, width - 4)
        h = 10 if kind not in (WidgetType.PROGRESSBAR, WidgetType.SLIDER) else 6
        d.add_widget(kind, x=x, y=y, width=min(w, width - 4), height=min(h, height - 4),
                     text=("Bench" if kind in (WidgetType.LABEL, WidgetType.BUTTON) else ""),
                     value=(i * 13) % 100,
                     checked=(i % 3 == 0))
        col += 1
        x += w + 2
        if col >= cols or x + w >= width - 2:
            col = 0
            x = 2
            y += max(h + 4, 12)
            if y >= height - 8:
                y = 2
    return d


def run_image_pass(designer: UIDesigner, include_grid: bool, iters: int) -> dict:
    vp = VisualPreviewWindow(designer)
    scene = designer.scenes[designer.current_scene]
    samples: List[float] = []
    for _ in range(iters):
        t0 = time.perf_counter()
        try:
            _ = vp._render_scene_image(
                scene,
                background_color=vp.settings.background_color,
                include_grid=include_grid,
                use_overlays=False,
                highlight_selection=False,
            )
        except TypeError:
            try:
                _ = vp._render_scene_image(scene, include_grid, False, False)
            except TypeError:
                _ = vp._render_scene_image(scene)
        samples.append((time.perf_counter() - t0) * 1000.0)
    avg = sum(samples) / len(samples)
    p95 = statistics.quantiles(samples, n=20, method="inclusive")[18] if len(samples) >= 20 else max(samples)
    return {"count": len(samples), "avg_ms": avg, "p95_ms": p95}

def run_ascii_pass(designer: UIDesigner, iters: int) -> dict:
    vp = VisualPreviewWindow(designer)
    scene = designer.scenes[designer.current_scene]
    samples: List[float] = []
    for _ in range(iters):
        t0 = time.perf_counter()
        _ = vp._render_ascii_scene(scene, use_cache=False)
        samples.append((time.perf_counter() - t0) * 1000.0)
    avg = sum(samples) / len(samples)
    p95 = statistics.quantiles(samples, n=20, method="inclusive")[18] if len(samples) >= 20 else max(samples)
    return {"count": len(samples), "avg_ms": avg, "p95_ms": p95}


def main():
    ap = argparse.ArgumentParser(description="ESP32OS preview micro-benchmark (headless)")
    ap.add_argument("--width", type=int, default=128)
    ap.add_argument("--height", type=int, default=64)
    ap.add_argument("--widgets", type=int, default=24)
    ap.add_argument("--iters", type=int, default=200)
    ap.add_argument("--image", action="store_true", help="Benchmark image renderer as well")
    ap.add_argument("--grid", action="store_true", help="Include grid in image benchmark")
    args = ap.parse_args()

    designer = build_sample_scene(args.width, args.height, args.widgets)

    ascii_res = run_ascii_pass(designer, args.iters)
    print("[preview-bench] ascii     count={count} avg={avg_ms:.3f}ms p95={p95_ms:.3f}ms".format(**ascii_res))

    if args.image and hasattr(VisualPreviewWindow, "_render_scene_image"):
        img_res = run_image_pass(designer, include_grid=args.grid, iters=args.iters)
        print("[preview-bench] image     count={count} avg={avg_ms:.3f}ms p95={p95_ms:.3f}ms".format(**img_res))
    elif args.image:
        print("[preview-bench] image     skipped (renderer helper not available)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
