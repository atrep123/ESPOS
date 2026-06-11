from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "gemini_jury.py"


def test_gemini_jury_help_does_not_require_api_key():
    env = os.environ.copy()
    env.pop("GEMINI_API_KEY", None)

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "--dir" in result.stdout
    assert "--device" in result.stdout
