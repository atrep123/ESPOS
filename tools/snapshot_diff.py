#!/usr/bin/env python3
"""
Compare snapshot outputs against a baseline.

Supports PNG (pixel diff) and TXT (exact diff).

Usage:
    python tools/snapshot_diff.py --baseline reports/baseline --current reports/snapshots --threshold 0
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image, ImageChops  # type: ignore
except Exception:  # pragma: no cover
    Image = None  # type: ignore
    ImageChops = None  # type: ignore


def diff_text(baseline: Path, current: Path) -> bool:
    """Return True if files match exactly."""
    return baseline.read_text(encoding="utf-8") == current.read_text(encoding="utf-8")


def diff_png(baseline: Path, current: Path, threshold: int = 0) -> bool:
    """Return True if PNGs match within threshold (number of nonzero diff pixels)."""
    if Image is None or ImageChops is None:  # pragma: no cover
        print("Pillow not available; cannot diff PNGs", file=sys.stderr)
        return False
    try:
        b_img = Image.open(baseline).convert("RGB")
        c_img = Image.open(current).convert("RGB")
        # Align sizes if needed (pad smaller)
        if b_img.size != c_img.size:
            max_w = max(b_img.width, c_img.width)
            max_h = max(b_img.height, c_img.height)
            def pad(img):
                canvas = Image.new("RGB", (max_w, max_h), (0, 0, 0))
                canvas.paste(img, (0, 0))
                return canvas
            b_img = pad(b_img)
            c_img = pad(c_img)
        diff = ImageChops.difference(b_img, c_img)
        # Count non-zero pixels
        hist = diff.convert("L").point(lambda x: 255 if x else 0).histogram()
        changed = sum(hist[1:])  # histogram[0] are zero-diff pixels
        return changed <= threshold
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Diff snapshots against baseline.")
    parser.add_argument("--baseline", required=True, help="Baseline directory containing snapshots.")
    parser.add_argument("--current", required=True, help="Current output directory to compare.")
    parser.add_argument("--threshold", type=int, default=0, help="Allowed nonzero pixel count for PNG diffs.")
    args = parser.parse_args()

    baseline_dir = Path(args.baseline)
    current_dir = Path(args.current)
    if not baseline_dir.is_dir() or not current_dir.is_dir():
        print("Both baseline and current must be directories.", file=sys.stderr)
        return 2

    mismatches = []

    for base_file in baseline_dir.rglob("*"):
        if base_file.is_dir():
            continue
        rel = base_file.relative_to(baseline_dir)
        cur_file = current_dir / rel
        if not cur_file.exists():
            mismatches.append((rel, "missing-current"))
            continue
        ok = False
        if base_file.suffix.lower() == ".txt":
            ok = diff_text(base_file, cur_file)
        elif base_file.suffix.lower() == ".png":
            ok = diff_png(base_file, cur_file, threshold=args.threshold)
        else:
            # Exact match for unknown types
            ok = base_file.read_bytes() == cur_file.read_bytes()
        if not ok:
            mismatches.append((rel, "diff"))

    if mismatches:
        print("Snapshot diff found mismatches:")
        for rel, reason in mismatches:
            print(f" - {rel}: {reason}")
        return 1

    print("Snapshot diff OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
