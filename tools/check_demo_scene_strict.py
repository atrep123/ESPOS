#!/usr/bin/env python3
"""Generate demo scene and enforce strict-critical validation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _run(step: str, args: list[str]) -> int:
    print(f"== {step} ==")
    cmd = [sys.executable, *args]
    print(" ".join(cmd))
    proc = subprocess.run(cmd, cwd=ROOT, check=False)
    return int(proc.returncode)


def main() -> int:
    rc = _run("Generate demo_scene.json", ["tools/generate_demo_scene.py"])
    if rc != 0:
        return rc

    rc = _run(
        "Validate demo_scene.json (--strict-critical)",
        ["tools/validate_design.py", "demo_scene.json", "--strict-critical"],
    )
    if rc != 0:
        return rc

    print("[OK] demo_scene.json strict gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
