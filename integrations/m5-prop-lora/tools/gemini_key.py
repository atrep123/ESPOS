"""Shared Gemini API key loading for local review tools.

Secrets are never committed or printed. The loader only returns the key value to
the caller that is about to make the REST request.
"""

from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def candidate_key_files(root: Path | None = None, home: Path | None = None) -> list[Path]:
    root = ROOT if root is None else Path(root)
    home = Path.home() if home is None else Path(home)

    candidates: list[Path] = []
    explicit_file = os.environ.get("GEMINI_API_KEY_FILE", "").strip()
    if explicit_file:
        candidates.append(Path(explicit_file).expanduser())
    candidates.append(root / ".gemini_api_key")
    candidates.append(home / ".gemini_api_key")

    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def load_api_key(root: Path | None = None, home: Path | None = None) -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key

    candidates = candidate_key_files(root=root, home=home)
    for path in candidates:
        if path.is_file():
            key = path.read_text(encoding="utf-8").strip()
            if key:
                return key

    paths = ", ".join(str(path) for path in candidates)
    raise SystemExit(
        "No Gemini API key: set GEMINI_API_KEY, set GEMINI_API_KEY_FILE, "
        f"or create .gemini_api_key at one of: {paths}"
    )
