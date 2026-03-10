import json
import os
import subprocess
import sys
from pathlib import Path


def test_run_designer_headless_export(tmp_path):
    """Headless export should create JSON without opening a window."""
    out = tmp_path / "tmp_scene.json"
    cmd = [
        sys.executable,
        "run_designer.py",
        str(out),
        "--headless-export",
        "--no-audio",
    ]
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        cmd, cwd=str(Path(__file__).resolve().parents[1]), capture_output=True, text=True, env=env
    )
    assert result.returncode == 0, result.stderr
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "scenes" in data
    assert data.get("width") > 0 and data.get("height") > 0
