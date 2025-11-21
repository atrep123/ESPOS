#!/usr/bin/env python3
"""Ensure token_lint reports non-token hex literals as expected."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def test_token_lint_reports_hex():
    tmpdir = Path(tempfile.mkdtemp())
    target = tmpdir / "sample.py"
    target.write_text('COLOR = "#123abc"\n', encoding="utf-8")
    cmd = [
        sys.executable,
        "tools/token_lint.py",
        "--paths",
        str(target),
    ]
    out = subprocess.check_output(cmd, env=os.environ.copy(), cwd=Path(__file__).resolve().parent)
    assert b"123abc" in out


if __name__ == "__main__":
    test_token_lint_reports_hex()
