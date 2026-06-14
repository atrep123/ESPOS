from __future__ import annotations

import base64
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest


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


def test_gemini_jury_parses_only_exact_vote_shape(monkeypatch):
    monkeypatch.syspath_prepend(str(TOOLS))
    spec = importlib.util.spec_from_file_location("gemini_jury_parse_under_test", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    parsed = module.parse_vote_output(
        "SCORE: 8\nSAFE: yes\nISSUE: Clear enough.\nGOOD: Strong contrast."
    )

    assert parsed["score"] == 8
    assert parsed["safe"] is True
    for malformed in [
        "SCORE: 999\nSAFE: yes\nISSUE: nope\nGOOD: nope",
        "SCORE: 8\nSAFE: yes\nISSUE: missing good",
        "extra\nSCORE: 8\nSAFE: yes\nISSUE: ok\nGOOD: ok",
    ]:
        with pytest.raises(ValueError, match="malformed Gemini vote"):
            module.parse_vote_output(malformed)


def test_gemini_jury_returns_nonzero_when_votes_error(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(TOOLS))
    spec = importlib.util.spec_from_file_location("gemini_jury_error_under_test", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    img_dir = tmp_path / "build" / "preview"
    img_dir.mkdir(parents=True)
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

    rc = module.main(
        ["--dir", "build/preview", "--device", "M5 Dial", "--per", "1", "--workers", "1"]
    )

    assert rc == 1
    report = tmp_path / "build" / "reviews" / "jury_preview.md"
    assert "## Errors" in report.read_text(encoding="utf-8")


def test_gemini_jury_can_select_contact_sheet_explicitly(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(TOOLS))
    spec = importlib.util.spec_from_file_location("gemini_jury_exact_image_under_test", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    img_dir = tmp_path / "build" / "preview"
    img_dir.mkdir(parents=True)
    (img_dir / "01_ready.png").write_bytes(PNG_1X1)
    (img_dir / "contact.png").write_bytes(PNG_1X1)
    seen: list[str] = []

    def fake_run_one(img, device, idx, endpoint):
        seen.append(img.name)
        return {
            "img": img.name,
            "idx": idx,
            "score": 8,
            "safe": True,
            "issue": "No blocking issue.",
            "good": "Selected image was reviewed.",
        }

    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "_load_api_key", lambda: "fake-key")
    monkeypatch.setattr(module, "run_one", fake_run_one)

    rc = module.main(
        [
            "--dir",
            "build/preview",
            "--image",
            "contact.png",
            "--device",
            "M5 Dial",
            "--per",
            "2",
            "--workers",
            "1",
        ]
    )

    assert rc == 0
    assert seen == ["contact.png", "contact.png"]
    report = tmp_path / "build" / "reviews" / "jury_preview.md"
    text = report.read_text(encoding="utf-8")
    assert "contact.png" in text
    assert "01_ready.png" not in text


def test_gemini_jury_allows_errors_only_with_flag(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(TOOLS))
    spec = importlib.util.spec_from_file_location("gemini_jury_allow_errors_under_test", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    img_dir = tmp_path / "build" / "preview"
    img_dir.mkdir(parents=True)
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
            "build/preview",
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


def test_gemini_jury_redacts_model_text_before_print_and_write(monkeypatch, tmp_path, capsys):
    monkeypatch.syspath_prepend(str(TOOLS))
    spec = importlib.util.spec_from_file_location("gemini_jury_redaction_under_test", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    img_dir = tmp_path / "build" / "preview"
    img_dir.mkdir(parents=True)
    (img_dir / "01_ready.png").write_bytes(PNG_1X1)
    raw_key = "AIza" + ("A" * 35)

    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "_load_api_key", lambda: "fake-key")
    monkeypatch.setattr(
        module,
        "run_one",
        lambda img, device, idx, endpoint: {
            "img": img.name,
            "idx": idx,
            "score": 7,
            "safe": True,
            "issue": (
                f"model echoed {raw_key} and https://example.test/path?key=query-secret-value"
            ),
            "good": "Authorization: Bearer bearer-secret-value",
        },
    )

    rc = module.main(
        ["--dir", "build/preview", "--device", "M5 Dial", "--per", "1", "--workers", "1"]
    )

    assert rc == 0
    captured = capsys.readouterr()
    written = (tmp_path / "build" / "reviews" / "jury_preview.md").read_text(encoding="utf-8")
    for text in (captured.out, captured.err, written):
        assert raw_key not in text
        assert "query-secret-value" not in text
        assert "bearer-secret-value" not in text
    assert "AIza<redacted>" in captured.out
    assert "key=<redacted>" in written


def test_gemini_jury_redacts_transport_exception_issue(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(TOOLS))
    spec = importlib.util.spec_from_file_location("gemini_jury_transport_redaction", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    img = tmp_path / "screen.png"
    img.write_bytes(PNG_1X1)
    raw_key = "AIza" + ("B" * 35)

    def fake_urlopen(_req, timeout):
        raise RuntimeError(f"x-goog-api-key: {raw_key}")

    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)

    result = module.run_one(img, "M5 Dial", 0, module._endpoint("fake-key"))

    assert raw_key not in result["issue"]
    assert "x-goog-api-key: <redacted>" in result["issue"]


def test_gemini_jury_rejects_external_image_dir_without_explicit_flag(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(TOOLS))
    spec = importlib.util.spec_from_file_location("gemini_jury_external_dir", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    img_dir = tmp_path / "screens"
    img_dir.mkdir()
    (img_dir / "01_ready.png").write_bytes(PNG_1X1)
    monkeypatch.setattr(module, "ROOT", tmp_path / "repo")

    rc = module.main(["--dir", str(img_dir), "--device", "M5 Dial"])

    assert rc == 2


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
