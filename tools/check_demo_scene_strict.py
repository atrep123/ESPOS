#!/usr/bin/env python3
"""Generate demo scene and enforce strict-critical validation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO_CHECK_PATH = ROOT / "output" / "buildprobe" / "demo_scene.strict.json"
TEMPLATES_PATH = ROOT / "templates.json"


def _run(step: str, args: list[str]) -> int:
    print(f"== {step} ==")
    cmd = [sys.executable, *args]
    print(" ".join(cmd))
    proc = subprocess.run(cmd, cwd=ROOT, check=False)
    return int(proc.returncode)


def main() -> int:
    templates_before = (
        TEMPLATES_PATH.read_text(encoding="utf-8") if TEMPLATES_PATH.exists() else None
    )

    DEMO_CHECK_PATH.parent.mkdir(parents=True, exist_ok=True)

    try:
        rc = _run(
            "Generate demo scene (temp)",
            ["tools/generate_demo_scene.py", str(DEMO_CHECK_PATH)],
        )
        if rc != 0:
            return rc

        rc = _run(
            "Validate generated demo scene (--strict-critical)",
            ["tools/validate_design.py", str(DEMO_CHECK_PATH), "--strict-critical"],
        )
        if rc != 0:
            return rc
    finally:
        if templates_before is None:
            if TEMPLATES_PATH.exists():
                TEMPLATES_PATH.unlink()
        elif TEMPLATES_PATH.read_text(encoding="utf-8") != templates_before:
            TEMPLATES_PATH.write_text(templates_before, encoding="utf-8")

    print("[OK] demo_scene.json strict gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
