#!/usr/bin/env python3
"""Basic Markdown lint: checks fenced code blocks have language.
Exit 1 if any missing languages or emphasis-as-heading pattern.
"""
from pathlib import Path
import sys
import re

ROOT = Path(__file__).resolve().parent.parent
md_files = [p for p in ROOT.rglob("*.md") if ".git" not in p.parts]
missing = []
invalid_heading = []
code_fence_re = re.compile(r"^```(.*)$")
emphasis_heading_re = re.compile(r"^\*\*[^*]+\*\*$")
for f in md_files:
    lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
    for i,l in enumerate(lines):
        m = code_fence_re.match(l)
        if m:
            lang = m.group(1).strip()
            if lang == "" and (i+1) < len(lines):
                missing.append((f,i+1))
        if emphasis_heading_re.match(l.strip()) and (i==0 or not lines[i-1].startswith("#")):
            invalid_heading.append((f,i+1))

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
