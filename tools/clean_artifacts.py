#!/usr/bin/env python3
"""
Cleanup helper for build/test artifacts.

Default is dry-run. Use --apply to actually delete.
"""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path, PurePosixPath
from typing import Iterable, List

DEFAULT_PATHS: List[Path] = [
    Path(".pio"),
    Path(".pytest_cache"),
    Path(".mypy_cache"),
    Path(".ruff_cache"),
    Path("dist"),
    Path("build"),
    Path("reports"),
    Path("output"),
    Path("screenshots"),
    Path("generated"),
]

DEFAULT_GLOBS: List[str] = [
    "**/__pycache__",
    "**/*.pyc",
    "**/.coverage",
    "coverage.xml",
    "report*.xml",
    "*.log",
    "*.tmp",
    "*.temp",
    "*.autosave.json",
    "headless_out.*",
    "no_preview*.*",
]

DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".venv",
    ".pio",
    "node_modules",
}


def remove_path(p: Path, apply: bool) -> None:
    if not p.exists():
        return
    if apply:
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        else:
            try:
                p.unlink()
            except Exception:
                pass
    print(f"{'Removed' if apply else 'Would remove'}: {p}")


def clean(paths: Iterable[Path], globs: Iterable[str], apply: bool) -> None:
    for p in paths:
        remove_path(p, apply)
    root = Path(".").resolve()
    # Avoid walking huge virtualenv/tool dirs by default.
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in DEFAULT_EXCLUDE_DIRS]
        current = Path(dirpath)

        rel_dir = PurePosixPath(current.relative_to(root).as_posix())
        for pattern in globs:
            if rel_dir.match(pattern):
                remove_path(current, apply)
                break

        for fname in filenames:
            fp = current / fname
            rel_file = PurePosixPath(fp.relative_to(root).as_posix())
            for pattern in globs:
                if rel_file.match(pattern):
                    remove_path(fp, apply)
                    break


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean build/test artifacts (dry-run by default)")
    parser.add_argument(
        "--apply", action="store_true", help="Perform deletion (default is dry-run)"
    )
    args = parser.parse_args()
    clean(DEFAULT_PATHS, DEFAULT_GLOBS, apply=args.apply)


if __name__ == "__main__":
    main()
