from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
import importlib.util
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "gemini_jury.py"
TOOLS = ROOT / "tools"


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


def test_gemini_jury_rubric_accepts_unambiguous_safe_screens(monkeypatch):
    monkeypatch.syspath_prepend(str(TOOLS))
    spec = importlib.util.spec_from_file_location("gemini_jury_rubric_under_test", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    assert "SAFE yes if the screen is unmistakably safe" in module.RUBRIC
    assert (
        "Do not mark safe/setup/ACK screens unsafe merely because they are not armed"
        in module.RUBRIC
    )
