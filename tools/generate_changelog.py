#!/usr/bin/env python3
"""
Generate a simple changelog from git history.
Usage:
  python tools/generate_changelog.py [from_ref] [to_ref]
Defaults to last git tag as from_ref and HEAD as to_ref.
"""
import logging
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parent.parent
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')


def run(cmd):
    return subprocess.check_output(cmd, cwd=ROOT, text=True).strip()


def split_commits(lines: List[str]) -> Tuple[List[str], List[str]]:
    breaking, regular = [], []
    for line in lines:
        if "[BREAKING]" in line.upper():
            clean = line.replace("[BREAKING]", "").replace("[breaking]", "").strip()
            breaking.append(clean)
        else:
            regular.append(line)
    return breaking, regular


def build_changelog(frm: str, to: str) -> str:
    range_spec = f"{frm}..{to}" if frm else to
    header = f"# Changelog ({range_spec})\n\n"
    try:
        raw = run(["git", "log", "--pretty=format:* %s (%an)", range_spec])
        lines = [l for l in raw.splitlines() if l.strip()]
    except subprocess.CalledProcessError as exc:
        logging.warning("git log failed for range %s: %s", range_spec, exc)
        lines = []

    breaking, regular = split_commits(lines)
    parts = [header]

    if breaking:
        parts.append("## Breaking Changes\n")
        parts.append("\n".join(breaking) + "\n")
    else:
        parts.append("## Breaking Changes\n- None\n")

    parts.append("## Changes\n")
    if regular:
        parts.append("\n".join(regular) + "\n")
    else:
        parts.append("_No commits found in range._\n")

    return "".join(parts)


def main():
    args = sys.argv[1:]
    if len(args) >= 1:
        frm = args[0]
    else:
        try:
            frm = run(["git", "describe", "--tags", "--abbrev=0"])
        except subprocess.CalledProcessError:
            frm = ""
    to = args[1] if len(args) >= 2 else "HEAD"

    changelog = build_changelog(frm, to)
    sys.stdout.write(changelog)


if __name__ == "__main__":
    main()
