#!/usr/bin/env python3
"""
Export ESP32OS designer JSON -> embedded-friendly C header.

Output is header-only and uses the firmware schema in `src/ui_scene.h`:
  - UiWidgetType / UiWidget / UiScene

It intentionally emits `static const` data so the header can be included
without a separate .c file (simple integration for small projects).
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Ensure repository root is on sys.path so `tools.ui_codegen` is importable
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.ui_codegen import generate_scenes_header


def export_header(json_path: Path, out_path: Path) -> None:
    guard = (out_path.stem.upper().replace("-", "_") + "_H").replace(".", "_")
    if guard[0].isdigit():
        guard = "_" + guard
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = generate_scenes_header(
        json_path, guard=guard, source_name=json_path.name, generated_ts=ts
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    p = argparse.ArgumentParser(
        description="Export ESP32OS design JSON to C header (ui_scene.h schema)"
    )
    p.add_argument("json", type=Path, help="Input design JSON (from the designer)")
    p.add_argument(
        "-o", "--output", type=Path, required=True, help="Output header path (e.g. output/ui.h)"
    )
    args = p.parse_args()

    for name in ("json", "output"):
        if not str(getattr(args, name)).strip():
            p.error(f"{name} path cannot be empty or whitespace-only")

    if not args.json.exists():
        raise SystemExit(f"[FAIL] JSON not found: {args.json}")
    export_header(args.json, args.output)
    print(f"[OK] Exported C header: {args.output}")


if __name__ == "__main__":
    main()
