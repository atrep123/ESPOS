from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
SCRIPT = TOOLS / "gemini_code_review.py"


def load_module():
    if str(TOOLS) not in sys.path:
        sys.path.insert(0, str(TOOLS))
    spec = importlib.util.spec_from_file_location("gemini_code_review_under_test", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_gemini_code_review_help_does_not_require_api_key():
    env = os.environ.copy()
    env.pop("GEMINI_API_KEY", None)
    env.pop("GEMINI_API_KEY_FILE", None)

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
    assert "--dry-run" in result.stdout
    assert "--max-chars" in result.stdout


def test_gemini_code_review_prompt_covers_non_visual_domains():
    module = load_module()

    prompt = module.build_review_prompt(max_chars=16_000)

    assert "Do not review screenshots" in prompt
    assert "UIFlow2 custom block artifact" in prompt
    assert "offline mpremote workflow" in prompt
    assert "wire protocol parity" in prompt
    assert "secret handling" in prompt
    assert "Gemini as a review gate" in prompt


def test_gemini_code_review_default_snapshot_includes_core_files():
    module = load_module()

    prompt = module.build_review_prompt(max_chars=50_000)

    assert "tools/validate_uiflow_blocks.py" in prompt
    assert "tools/uiflow_dial_offline.py" in prompt
    assert "uiflow/dial/blocks/alpha2/PropTx.py" in prompt
    assert "uiflow/dial/prop_frame.py" in prompt
    assert "tests/test_uiflow_blocks_bundle.py" in prompt


def test_gemini_code_review_redacts_google_api_keys():
    module = load_module()

    text = "\n".join(
        [
            "temporary key = AIza" + ("A" * 35),
            "GEMINI_API_KEY=plain-secret-value",
            "https://example.test/path?key=query-secret-value&x=1",
            "Authorization: Bearer bearer-secret-value",
            "x-goog-api-key: header-secret-value",
        ]
    )

    redacted = module.redact_secrets(text)

    assert text not in redacted
    assert "AIza<redacted>" in redacted
    assert "GEMINI_API_KEY=<redacted>" in redacted
    assert "key=<redacted>" in redacted
    assert "Authorization: Bearer <redacted>" in redacted
    assert "x-goog-api-key: <redacted>" in redacted


def test_gemini_code_review_rejects_secret_like_targets(tmp_path):
    module = load_module()
    secret = tmp_path / ".gemini_api_key"
    secret.write_text("local-secret", encoding="utf-8")

    with pytest.raises(ValueError, match="refusing to include secret-like target"):
        module._normalise_target(".gemini_api_key")


def test_gemini_code_review_dry_run_writes_prompt_without_api_key(tmp_path):
    env = os.environ.copy()
    env.pop("GEMINI_API_KEY", None)
    env.pop("GEMINI_API_KEY_FILE", None)
    out = tmp_path / "review_prompt.md"

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--dry-run", "--out", str(out), "--max-chars", "12000"],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert out.exists()
    written = out.read_text(encoding="utf-8")
    assert "# Gemini code/workflow review prompt" in written
    assert "No Gemini API call was made" in result.stdout


def test_gemini_code_review_default_snapshot_includes_protocol_and_generator_files():
    module = load_module()

    prompt = module.build_review_prompt(max_chars=90_000)

    assert "shared/protocol/prop_protocol.h" in prompt
    assert "shared/protocol/protocol.py" in prompt
    assert "tools/build_uiflow_alpha2_artifact.py" in prompt
    assert "uiflow/dial/blocks/dist/PropTx.m5b2" in prompt
    assert "uiflow/dial/blocks/code/reply.py" in prompt
