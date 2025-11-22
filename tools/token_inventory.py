#!/usr/bin/env python3
"""
Token inventory - report most common hardcoded literals to migrate onto design tokens.

Usage:
    python tools/token_inventory.py --paths ui_designer_preview.py ui_components.py

Outputs:
    Top N hex literals (normalized) with counts. Optional report file via --out.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable, List, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from design_tokens import COLOR_HEX

HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})")


def _normalize_hex(h: str) -> str:
    h = h.lower()
    if len(h) == 4:  # 3-digit -> expanded 6-digit
        return "#" + "".join(c * 2 for c in h[1:])
    return h


def _load_allow_file(path: Path) -> Set[str]:
    allow: Set[str] = set()
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if not line.startswith("#"):
                line = "#" + line
            allow.add(_normalize_hex(line))
    except Exception:
        pass
    return allow


def collect_hex_counts(paths: Iterable[Path]) -> Counter:
    counts: Counter = Counter()
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        for m in HEX_RE.finditer(text):
            # Skip tokens that are clearly part of words/directives (e.g., '#define').
            end = m.end()
            if end < len(text) and text[end].isalpha():
                continue
            counts[_normalize_hex(m.group())] += 1
    return counts


def gather_targets(path_args: List[str], exts: List[str]) -> List[Path]:
    targets: List[Path] = []
    for p in path_args:
        path = Path(p)
        if path.is_dir():
            targets.extend(sorted(fp for fp in path.rglob("*") if fp.suffix in exts))
        elif path.is_file():
            targets.append(path)
    return targets


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory literals to migrate to design tokens.")
    parser.add_argument("--paths", nargs="+", required=True, help="Files or directories to scan.")
    parser.add_argument("--ext", nargs="*", default=[".py"], help="File extensions to include when scanning directories.")
    parser.add_argument("--allow-file", help="Optional file with extra allowed hex values (one per line, with or without leading #).")
    parser.add_argument("--top", type=int, default=20, help="Show top N literals.")
    parser.add_argument("--out", help="Optional output file to write the report.")
    args = parser.parse_args()

    targets = gather_targets(args.paths, args.ext)
    if not targets:
        print("No valid files to scan.")
        return 0

    allow = set(_normalize_hex(v) for v in COLOR_HEX.values())
    if args.allow_file:
        allow |= _load_allow_file(Path(args.allow_file))
    counts = collect_hex_counts(targets)

    top = counts.most_common(args.top)
    lines: List[str] = []
    if not top:
        lines.append("No hex literals found.")
    else:
        lines.append("Top hex literals (including allowed tokens):")
        for literal, cnt in top:
            status = "token" if literal in allow else "non-token"
            lines.append(f"{literal:8} x{cnt:4}  [{status}]")

    report = "\n".join(lines)
    print(report)

    if args.out:
        try:
            Path(args.out).write_text(report + "\n", encoding="utf-8")
        except Exception as e:
            print(f"Failed to write report to {args.out}: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
