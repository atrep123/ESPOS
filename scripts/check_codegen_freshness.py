#!/usr/bin/env python3
"""Check that src/ui_design.c and src/ui_design.h are up-to-date with main_scene.json.

Exit 0   — files match (or JSON has no scenes).
Exit 1   — files are stale (diff shown).
Exit 2   — error (missing file, bad JSON, etc.).

Usage:
    python scripts/check_codegen_freshness.py [main_scene.json]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.ui_codegen import (
    generate_ui_design_multi_pair,
    generate_ui_design_pair,
    load_scenes,
)


def main() -> int:
    json_path = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / "main_scene.json"
    json_path = json_path.resolve()
    if not json_path.exists():
        print(f"[SKIP] JSON not found: {json_path}")
        return 0

    try:
        scenes = load_scenes(json_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"[ERROR] Failed to parse {json_path.name}: {exc}", file=sys.stderr)
        return 2

    if not scenes:
        print("[SKIP] No scenes in JSON — nothing to check.")
        return 0

    try:
        source_label = json_path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        source_label = json_path.name

    if len(scenes) > 1:
        expected_c, expected_h = generate_ui_design_multi_pair(json_path, source_label=source_label)
    else:
        scene_name = next(iter(scenes))
        expected_c, expected_h = generate_ui_design_pair(
            json_path, scene_name=scene_name, source_label=source_label
        )

    out_c = REPO_ROOT / "src" / "ui_design.c"
    out_h = REPO_ROOT / "src" / "ui_design.h"
    stale: list[str] = []

    for path, expected in [(out_c, expected_c), (out_h, expected_h)]:
        if not path.exists():
            stale.append(f"  {path.name}: MISSING")
            continue
        actual = path.read_text(encoding="utf-8")
        if actual != expected:
            stale.append(f"  {path.name}: STALE")

    if stale:
        print("[FAIL] Generated files out of date:")
        for line in stale:
            print(line)
        print(
            'Regenerate with: python -c "from scripts.pio_generate_ui_design import *" '
            "or run a PlatformIO build."
        )
        return 1

    print("[OK] src/ui_design.c and src/ui_design.h are up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
