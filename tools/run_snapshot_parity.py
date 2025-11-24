#!/usr/bin/env python3
"""
Run snapshot_runner for selected scenes and diff against baseline.

Usage:
    python tools/run_snapshot_parity.py --scenes output/demo_scene.json output/ui_demo.json
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run snapshot parity check.")
    parser.add_argument("--scenes", nargs="+", required=True, help="List of scene JSON files.")
    parser.add_argument("--baseline", default="reports/baseline", help="Baseline directory.")
    parser.add_argument("--out-dir", default="reports/snapshots", help="Output directory for current run.")
    parser.add_argument("--threshold", type=int, default=0, help="PNG diff tolerance (nonzero pixels).")
    args = parser.parse_args()

    env = os.environ.copy()
    env.setdefault("ESP32OS_HEADLESS", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")

    # Run snapshot_runner for each scene
    for scene in args.scenes:
        subprocess.run(
            [sys.executable, "tools/snapshot_runner.py", "--scene", scene, "--out-dir", args.out_dir, "--png", "--ascii"],
            check=True,
            cwd=Path(__file__).resolve().parents[1],
            env=env,
        )

    # Run diff
    result = subprocess.run(
        [sys.executable, "tools/snapshot_diff.py", "--baseline", args.baseline, "--current", args.out_dir, "--threshold", str(args.threshold)],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
