#!/usr/bin/env python3
"""
Token usage report - list used and unused design tokens across the codebase.

Usage:
    python tools/token_usage.py --paths . --ext .py .c .h .html
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable, List, Set

ROOT = Path(__file__).resolve().parents[1]

import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from design_tokens import COLOR_HEX  # noqa: E402

TOKEN_PATTERN = re.compile(
    r'color_hex\(\s*[\"\']([^\"\']+)|COLOR_HEX\[[\"\']([^\"\']+)[\"\']\]'
)


def gather_targets(path_args: List[str], exts: List[str]) -> List[Path]:
    targets: List[Path] = []
    for p in path_args:
        path = Path(p)
        if path.is_dir():
            targets.extend(sorted(fp for fp in path.rglob("*") if fp.suffix.lower() in exts))
        elif path.is_file():
            targets.append(path)
    return targets


def find_used_tokens(paths: Iterable[Path]) -> Set[str]:
    used: Set[str] = set()
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        for match in TOKEN_PATTERN.finditer(text):
            used.update(g for g in match.groups() if g)
    return used


def main() -> int:
    parser = argparse.ArgumentParser(description="Report used and unused design tokens.")
    parser.add_argument("--paths", nargs="+", required=True, help="Files or directories to scan.")
    parser.add_argument("--ext", nargs="*", default=[".py"], help="File extensions to include when scanning directories.")
    parser.add_argument("--out", help="Optional output file to write the report.")
    args = parser.parse_args()

    targets = gather_targets(args.paths, [ext.lower() for ext in args.ext])
    used = find_used_tokens(targets)
    unused = set(COLOR_HEX.keys()) - used

    lines = [
        f"Used tokens ({len(used)}):",
        ", ".join(sorted(used)),
        "",
        f"Unused tokens ({len(unused)}):",
        ", ".join(sorted(unused)),
    ]
    report = "\n".join(lines)
    print(report)

    if args.out:
        try:
            Path(args.out).write_text(report + "\n", encoding="utf-8")
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
