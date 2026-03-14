#!/usr/bin/env python3
"""
Audit design JSON files for basic sanity:
- reports width/height, scene count, widget count
- flags empty scenes and oversized canvases (default threshold 320x240)

Usage:
    python tools/audit_designs.py
    python tools/audit_designs.py --max-width 320 --max-height 240
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, Tuple

DEFAULT_SKIP = {
    "pyrightconfig.json",
    ".sim_config.json",
    "profiler_enhanced.json",
    "templates.json",
}


def find_design_files(root: Path) -> Iterable[Path]:
    for p in root.glob("*.json"):
        if p.name in DEFAULT_SKIP:
            continue
        yield p


def audit_file(path: Path, max_w: int, max_h: int) -> Tuple[bool, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        w = int(data.get("width", 0))
        h = int(data.get("height", 0))
        scenes = data.get("scenes", {})
        details = []
        ok = True
        if w <= 0 or h <= 0:
            ok = False
            details.append("invalid size")
        if w > max_w or h > max_h:
            details.append(f"oversize {w}x{h}")
        empty_scenes = []
        total_widgets = 0
        for name, sc in scenes.items():
            widgets = sc.get("widgets", [])
            total_widgets += len(widgets)
            if len(widgets) == 0:
                empty_scenes.append(name)
        # Rough RAM/flash estimate
        depth = 1 if (w <= 128 and h <= 64) else 16
        area = max(1, w * h)
        fb_bytes = (area + 7) // 8 if depth <= 1 else int(area * (depth / 8.0))
        fb_kb = fb_bytes / 1024.0
        details.append(f"fb_est={fb_kb:.1f}KB/{depth}bpp")
        if empty_scenes:
            details.append(f"empty scenes: {', '.join(empty_scenes)}")
        summary = f"{path.name}: {w}x{h}, scenes={len(scenes)}, widgets={total_widgets}"
        if details:
            summary += " | " + "; ".join(details)
        return ok, summary
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        return False, f"{path.name}: FAILED to parse ({exc})"


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit design JSON files")
    parser.add_argument("--root", default=".", help="Root directory to scan")
    parser.add_argument("--max-width", type=int, default=320, help="Max recommended width")
    parser.add_argument("--max-height", type=int, default=240, help="Max recommended height")
    args = parser.parse_args()

    if not str(args.root).strip():
        parser.error("--root cannot be empty or whitespace-only")

    root = Path(args.root).resolve()
    files = list(find_design_files(root))
    if not files:
        print("No design JSON files found.")
        sys.exit(0)

    ok_all = True
    for p in sorted(files):
        ok, msg = audit_file(p, args.max_width, args.max_height)
        print(("[OK] " if ok else "[WARN] ") + msg)
        ok_all = ok_all and ok

    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
