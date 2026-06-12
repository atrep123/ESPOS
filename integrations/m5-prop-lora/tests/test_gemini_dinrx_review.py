from __future__ import annotations

import importlib.util
import sys
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
