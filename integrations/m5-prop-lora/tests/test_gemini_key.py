from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
KEY_SCRIPT = TOOLS / "gemini_key.py"
JURY_SCRIPT = TOOLS / "gemini_jury.py"


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
