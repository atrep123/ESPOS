#!/usr/bin/env python3
"""Smoke test for snapshot_runner in headless mode."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def test_snapshot_runner_ascii_only():
    repo_root = Path(__file__).resolve().parent
    scene = repo_root / "examples" / "demo_scene.json"
    out_dir = Path(tempfile.mkdtemp())
    env = os.environ.copy()
    env["ESP32OS_HEADLESS"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    cmd = [
        sys.executable,
        "tools/snapshot_runner.py",
        "--scene",
        str(scene),
        "--out-dir",
        str(out_dir),
        "--ascii",
    ]
    subprocess.run(cmd, check=True, cwd=repo_root, env=env)
    txt = out_dir / f"{scene.stem}.txt"
    assert txt.exists(), "ASCII snapshot should be generated"
    assert txt.stat().st_size > 0, "ASCII snapshot should not be empty"


if __name__ == "__main__":
    test_snapshot_runner_ascii_only()
