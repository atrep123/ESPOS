#!/usr/bin/env python3
"""Validate web/token_allow.txt formatting."""

import re
from pathlib import Path

ALLOW_PATH = Path("web/token_allow.txt")
HEX_RE = re.compile(r"^[0-9a-fA-F]{6}$")


def test_token_allow_file_exists():
    assert ALLOW_PATH.exists(), "token allow-list missing"


def test_token_allow_is_normalized_and_unique():
    raw_lines = [ln.strip() for ln in ALLOW_PATH.read_text(encoding="utf-8").splitlines() if ln.strip()]
    # Ignore comments
    lines = [ln.lstrip("#") for ln in raw_lines if not ln.startswith("#")]
    assert lines, "token allow-list is empty"
    assert all(HEX_RE.match(ln) for ln in lines), "token allow-list must contain 6-hex lines (no #)"
    assert len(lines) == len(set(lines)), "token allow-list contains duplicates"
    assert lines == sorted(lines), "token allow-list should be sorted for readability"
