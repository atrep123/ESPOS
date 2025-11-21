#!/usr/bin/env python3
"""
Normalize line endings across the repo to LF.
Skips common binary/media directories and files.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", ".pio", "node_modules", "dist", "build", "reports", ".venv", "venv", "__pycache__"}
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".svg", ".exe", ".dll", ".bin", ".so"}


def should_process(path: Path) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return False
    if path.suffix.lower() in SKIP_SUFFIXES:
        return False
    return path.is_file()


def normalize_file(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="ignore")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if normalized != text:
        path.write_text(normalized, encoding="utf-8")


def main() -> None:
    for file_path in ROOT.rglob("*"):
        if should_process(file_path):
            normalize_file(file_path)


if __name__ == "__main__":
    main()
