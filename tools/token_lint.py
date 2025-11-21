#!/usr/bin/env python3
"""
Token lint - report hardcoded hex colors in selected files.

Usage:
    python tools/token_lint.py --paths ui_designer_preview.py ui_components.py

Exit code:
    0 always (report only).
"""
from __future__ import annotations

import argparse
import re
from collections import Counter
import sys
from pathlib import Path
from typing import Iterable, Set

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from design_tokens import COLOR_HEX


HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})")


def _normalize_hex(h: str) -> str:
    h = h.lower()
    if len(h) == 4:  # #abc -> #aabbcc
        return "#" + "".join([c * 2 for c in h[1:]])
    return h


def find_hex_literals(paths: Iterable[Path], allow: Set[str]) -> Counter:
    counts: Counter = Counter()
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        for match in HEX_RE.findall(text):
            hx = _normalize_hex(match)
            if hx not in allow:
                counts[hx] += 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Report hardcoded hex colors outside design tokens.")
    parser.add_argument("--paths", nargs="+", required=True, help="Files or directories to scan.")
    parser.add_argument("--top", type=int, default=20, help="Show top N literals.")
    args = parser.parse_args()

    targets = []
    for p in args.paths:
        path = Path(p)
        if path.is_dir():
            targets.extend(sorted(path.rglob("*.py")))
        elif path.is_file():
            targets.append(path)

    allow = set(_normalize_hex(v) for v in COLOR_HEX.values())
    counts = find_hex_literals(targets, allow)
    if not counts:
        print("No non-token hex literals found.")
        return 0

    print("Non-token hex literals (top):")
    for literal, cnt in counts.most_common(args.top):
        print(f"{literal}  x{cnt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
