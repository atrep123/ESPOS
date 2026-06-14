from __future__ import annotations

import io
import importlib.util
import json
import sys
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "gemini_dinrx_review.py"
TOOLS = ROOT / "tools"


def test_gemini_dinrx_review_import_does_not_require_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    original_exists = Path.exists

    def fake_exists(path: Path) -> bool:
        if path.name == ".gemini_api_key":
            return False
        return original_exists(path)

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.syspath_prepend(str(TOOLS))
    sys.modules.pop("gemini_dinrx_review_no_key_import", None)

    spec = importlib.util.spec_from_file_location("gemini_dinrx_review_no_key_import", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    assert module.GEMINI_MODEL


def load_module(monkeypatch, name: str = "gemini_dinrx_review_under_test"):
    monkeypatch.syspath_prepend(str(TOOLS))
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_gemini_dinrx_review_ask_redacts_success_and_http_error(monkeypatch):
    module = load_module(monkeypatch, "gemini_dinrx_review_redaction")
    raw_key = "AIza" + ("C" * 35)

    class FakeResponse:
        def read(self):
            return json.dumps(
                {
                    "candidates": [
                        {"content": {"parts": [{"text": f"model echoed {raw_key}"}]}}
                    ]
                }
            ).encode("utf-8")

    monkeypatch.setattr(module.urllib.request, "urlopen", lambda _req, timeout: FakeResponse())

    text = module._ask(module._endpoint("fake-key"), [{"text": "prompt"}])

    assert raw_key not in text
    assert "AIza<redacted>" in text

    def fake_http_error(_req, timeout):
        raise urllib.error.HTTPError(
            "https://example.test",
            400,
            "bad request",
            hdrs=None,
            fp=io.BytesIO(f'{{"error":"x-goog-api-key: {raw_key}"}}'.encode("utf-8")),
        )

    monkeypatch.setattr(module.urllib.request, "urlopen", fake_http_error)

    error = module._ask(module._endpoint("fake-key"), [{"text": "prompt"}])

    assert raw_key not in error
    assert "x-goog-api-key: <redacted>" in error


def test_gemini_dinrx_review_main_redacts_report_before_print_and_write(
    monkeypatch, tmp_path, capsys
):
    module = load_module(monkeypatch, "gemini_dinrx_review_main_redaction")
    raw_key = "AIza" + ("D" * 35)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "_load_api_key", lambda: "fake-key")
    monkeypatch.setattr(module.P, "FONT_BOLD", tmp_path / "missing.ttf", raising=False)
    monkeypatch.setattr(module.P, "scenes", lambda: {"ready": ("view", "page")})
    monkeypatch.setattr(
        module.P,
        "render",
        lambda _view, _page, hires=True: module.Image.new("RGB", (4, 4), (0, 0, 0)),
    )
    monkeypatch.setattr(
        module,
        "_ask",
        lambda *_args, **_kwargs: (
            f"ISSUE: leaked {raw_key} and https://example.test/path?key=query-secret-value"
        ),
    )

    rc = module.main()

    assert rc == 0
    captured = capsys.readouterr()
    written = (tmp_path / "build" / "reviews" / "gemini_dinrx_hires.md").read_text(
        encoding="utf-8"
    )
    for text in (captured.out, captured.err, written):
        assert raw_key not in text
        assert "query-secret-value" not in text
    assert "AIza<redacted>" in captured.out
    assert "key=<redacted>" in written


def test_gemini_dinrx_review_main_fails_when_any_vote_returns_error(
    monkeypatch, tmp_path, capsys
):
    module = load_module(monkeypatch, "gemini_dinrx_review_main_error_gate")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "_load_api_key", lambda: "fake-key")
    monkeypatch.setattr(module.P, "FONT_BOLD", tmp_path / "missing.ttf", raising=False)
    monkeypatch.setattr(module.P, "scenes", lambda: {"ready": ("view", "page")})
    monkeypatch.setattr(
        module.P,
        "render",
        lambda _view, _page, hires=True: module.Image.new("RGB", (4, 4), (0, 0, 0)),
    )
    monkeypatch.setattr(module, "_ask", lambda *_args, **_kwargs: "ERROR HTTP 500: synthetic")

    rc = module.main()

    assert rc == 1
    captured = capsys.readouterr()
    written = (tmp_path / "build" / "reviews" / "gemini_dinrx_hires.md").read_text(
        encoding="utf-8"
    )
    assert "ERROR HTTP 500" in captured.out
    assert "ERROR HTTP 500" in written
