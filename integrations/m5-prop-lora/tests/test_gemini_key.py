from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
KEY_SCRIPT = TOOLS / "gemini_key.py"
JURY_SCRIPT = TOOLS / "gemini_jury.py"
ASK_SCRIPT = TOOLS / "ask_gemini.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_gemini_key_prefers_env(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(TOOLS))
    monkeypatch.setenv("GEMINI_API_KEY", "env-key")
    monkeypatch.setenv("GEMINI_API_KEY_FILE", str(tmp_path / "ignored-key-file"))

    module = load_module(KEY_SCRIPT, "gemini_key_env_under_test")

    assert module.load_api_key(root=tmp_path, home=tmp_path) == "env-key"


def test_gemini_key_reads_explicit_key_file(monkeypatch, tmp_path):
    key_file = tmp_path / "gemini.secret"
    key_file.write_text("file-key\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(TOOLS))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY_FILE", str(key_file))

    module = load_module(KEY_SCRIPT, "gemini_key_file_under_test")

    assert module.load_api_key(root=tmp_path, home=tmp_path) == "file-key"


def test_gemini_key_reads_home_key_file(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".gemini_api_key").write_text("home-key\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(TOOLS))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY_FILE", raising=False)

    module = load_module(KEY_SCRIPT, "gemini_key_home_under_test")

    assert module.load_api_key(root=tmp_path / "repo", home=home) == "home-key"


def test_gemini_key_reports_supported_sources(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(TOOLS))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY_FILE", raising=False)

    module = load_module(KEY_SCRIPT, "gemini_key_missing_under_test")

    with pytest.raises(SystemExit) as exc:
        module.load_api_key(root=tmp_path / "repo", home=tmp_path / "home")

    assert "GEMINI_API_KEY" in str(exc.value)
    assert "GEMINI_API_KEY_FILE" in str(exc.value)
    assert ".gemini_api_key" in str(exc.value)


def test_gemini_jury_uses_shared_key_loader(monkeypatch, tmp_path):
    key_file = tmp_path / "gemini.secret"
    key_file.write_text("jury-key\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(TOOLS))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY_FILE", str(key_file))

    module = load_module(JURY_SCRIPT, "gemini_jury_key_loader_under_test")

    assert module._load_api_key() == "jury-key"


def test_ask_gemini_redacts_secret_like_response_text(monkeypatch, tmp_path, capsys):
    secret = "AIza" + ("A" * 35)
    image = tmp_path / "preview.png"
    image.write_bytes(b"not-a-real-png")
    monkeypatch.syspath_prepend(str(TOOLS))
    monkeypatch.setattr(sys, "argv", [str(ASK_SCRIPT), str(image)])

    module = load_module(ASK_SCRIPT, "ask_gemini_redaction_under_test")
    monkeypatch.setattr(module, "load_api_key", lambda: secret)

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {
                    "candidates": [
                        {"content": {"parts": [{"text": f"model echoed {secret} in response"}]}}
                    ]
                }
            ).encode("utf-8")

    def fake_urlopen(req, timeout):
        assert req.headers["X-goog-api-key"] == secret
        assert timeout == 120
        return FakeResponse()

    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)

    assert module.main() == 0

    captured = capsys.readouterr()
    written = (ROOT / "build" / "preview" / "gemini_review.txt").read_text(encoding="utf-8")
    assert secret not in captured.out
    assert secret not in written
    assert "AIza<redacted>" in captured.out
    assert "AIza<redacted>" in written
