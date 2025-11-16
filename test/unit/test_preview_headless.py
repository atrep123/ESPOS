import os
import subprocess
import sys
from pathlib import Path


def test_headless_preview_png(tmp_path):
    out = tmp_path / "preview.png"
    cmd = [sys.executable, "ui_designer_preview.py", "--headless", "--out-png", str(out)]
    r = subprocess.run(cmd, check=True, capture_output=True, text=True)
    assert out.exists(), f"PNG not created: {out} (stdout={r.stdout}, stderr={r.stderr})"
    # Basic size check (>1KB)
    assert out.stat().st_size > 1024
