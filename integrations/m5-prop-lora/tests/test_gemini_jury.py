from __future__ import annotations

import base64
import importlib.util
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "gemini_jury.py"
TOOLS = ROOT / "tools"
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


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


def test_gemini_jury_returns_nonzero_when_votes_error(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(TOOLS))
    spec = importlib.util.spec_from_file_location("gemini_jury_error_under_test", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    img_dir = tmp_path / "preview"
    img_dir.mkdir()
    (img_dir / "01_ready.png").write_bytes(PNG_1X1)

    def fake_run_one(img, device, idx, endpoint):
        return {
            "img": img.name,
            "idx": idx,
            "score": None,
            "safe": None,
            "issue": "ERROR: synthetic failure",
            "good": "",
        }

    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "_load_api_key", lambda: "fake-key")
    monkeypatch.setattr(module, "run_one", fake_run_one)

    rc = module.main(["--dir", "preview", "--device", "M5 Dial", "--per", "1", "--workers", "1"])

    assert rc == 1
    report = tmp_path / "build" / "reviews" / "jury_preview.md"
    assert "## Errors" in report.read_text(encoding="utf-8")


def test_gemini_jury_allows_errors_only_with_flag(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(TOOLS))
    spec = importlib.util.spec_from_file_location("gemini_jury_allow_errors_under_test", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    img_dir = tmp_path / "preview"
    img_dir.mkdir()
    (img_dir / "01_ready.png").write_bytes(PNG_1X1)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "_load_api_key", lambda: "fake-key")
    monkeypatch.setattr(
        module,
        "run_one",
        lambda img, device, idx, endpoint: {
            "img": img.name,
            "idx": idx,
            "score": None,
            "safe": None,
            "issue": "ERROR: synthetic failure",
            "good": "",
        },
    )

    rc = module.main(
        [
            "--dir",
            "preview",
            "--device",
            "M5 Dial",
            "--per",
            "1",
            "--workers",
            "1",
            "--allow-errors",
        ]
    )

    assert rc == 0


def test_gemini_jury_rejects_zero_per_and_workers_without_api_key(tmp_path):
    env = os.environ.copy()
    env.pop("GEMINI_API_KEY", None)
    env.pop("GEMINI_API_KEY_FILE", None)
    img_dir = tmp_path / "preview"
    img_dir.mkdir()
    (img_dir / "01_ready.png").write_bytes(PNG_1X1)

    for flag in ("--per", "--workers"):
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--dir",
                str(img_dir),
                "--device",
                "M5 Dial",
                flag,
                "0",
            ],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        assert result.returncode == 2
        assert "must be >= 1" in result.stderr
