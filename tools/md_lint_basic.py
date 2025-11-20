#!/usr/bin/env python3
"""Basic Markdown lint: checks fenced code blocks have language.
Exit 1 if any missing languages or emphasis-as-heading pattern.
"""
from pathlib import Path
import sys
import re

ROOT = Path(__file__).resolve().parent.parent

# Ignore patterns for external dependencies
IGNORE_DIRS = {".git", "node_modules", "target", ".pio", ".venv", "build"}

def should_ignore(path: Path) -> bool:
    """Check if path should be ignored based on IGNORE_DIRS."""
    return any(ignored in path.parts for ignored in IGNORE_DIRS)

md_files = [p for p in ROOT.rglob("*.md") if not should_ignore(p)]
missing = []
invalid_heading = []
code_fence_re = re.compile(r"^```(.*)$")
emphasis_heading_re = re.compile(r"^\*\*[^*]+\*\*$")

for f in md_files:
    lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
    in_code = False
    for i, l in enumerate(lines):
        # Track fenced code blocks and require language only on opening fence
        m = code_fence_re.match(l)
        if m:
            lang = m.group(1).strip()
            if not in_code:
                # Opening fence
                if lang == "" and (i + 1) < len(lines):
                    missing.append((f, i + 1))
                in_code = True
            else:
                # Closing fence
                in_code = False

        # Heuristic for emphasis-used-as-heading:
        # keep allowing label-style lines like **Funkce:** (ending with :)
        stripped = l.strip()
        if emphasis_heading_re.match(stripped):
            inner = stripped[2:-2].strip()
            if inner.endswith(":"):
                continue
            if i == 0 or not lines[i - 1].lstrip().startswith("#"):
                invalid_heading.append((f, i + 1))

if missing or invalid_heading:
    print("Markdown lint FAILED")
    if missing:
        print("Missing language spec for fenced code blocks:")
        for f,ln in missing:
            print(f"  {f}:{ln}")
    if invalid_heading:
        print("Emphasis used as heading lines:")
        for f,ln in invalid_heading:
            print(f"  {f}:{ln}")
    sys.exit(1)
print("Markdown lint PASS (basic checks)")
