from __future__ import annotations

import importlib.util
import io
import os
import subprocess
import sys
import urllib.error
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


def repository_snapshot(prompt: str) -> str:
    return prompt.split("# Repository Snapshot", 1)[1]


def snapshot_coverage(prompt: str) -> str:
    return prompt.split("# Snapshot Coverage", 1)[1].split("# Repository Snapshot", 1)[0]


def snapshot_section(prompt: str, path: str) -> str:
    snapshot = repository_snapshot(prompt)
    return snapshot.split(f"### {path}", 1)[1].split("\n### ", 1)[0]


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
    assert "Reviewing source code for the key loader or its tests is expected" in prompt
    assert "only concrete secret values" in prompt
    assert "prototype HMAC key is acceptable only for PoC/dry-smoke" in prompt
    assert "Release/CI builds" in prompt
    assert "Treat <redacted> inside source excerpts as a sanitization artifact" in prompt


def test_gemini_code_review_default_snapshot_includes_core_files():
    module = load_module()

    prompt = module.build_review_prompt()
    snapshot = repository_snapshot(prompt)

    assert "### tools/validate_uiflow_blocks.py" in snapshot
    assert "### tools/uiflow_dial_offline.py" in snapshot
    assert "### uiflow/dial/blocks/alpha2/PropTx.py" in snapshot
    assert "### uiflow/dial/prop_frame.py" in snapshot
    assert "### tests/test_uiflow_blocks_bundle.py" in snapshot


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


def test_gemini_code_review_redacts_http_error_body(monkeypatch):
    module = load_module()
    secret = "AIza" + ("B" * 35)
    body = "\n".join(
        [
            f"api key echoed: {secret}",
            "https://example.test/path?key=query-secret-value&x=1",
            "GEMINI_API_KEY=plain-secret-value",
            "Authorization: Bearer bearer-secret-value",
            "x-goog-api-key: header-secret-value",
        ]
    )

    def fake_urlopen(req, timeout):
        assert req.headers["X-goog-api-key"] == secret
        assert timeout == 180
        raise urllib.error.HTTPError(
            req.full_url,
            403,
            "Forbidden",
            hdrs=None,
            fp=io.BytesIO(body.encode("utf-8")),
        )

    monkeypatch.setattr(module, "load_api_key", lambda root: secret)
    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)

    result = module.ask_gemini("review me")

    assert result.startswith("ERROR HTTP 403:")
    for leaked in [
        secret,
        "query-secret-value",
        "plain-secret-value",
        "bearer-secret-value",
        "header-secret-value",
    ]:
        assert leaked not in result
    assert "AIza<redacted>" in result
    assert "key=<redacted>" in result
    assert "GEMINI_API_KEY=<redacted>" in result
    assert "Authorization: Bearer <redacted>" in result
    assert "x-goog-api-key: <redacted>" in result


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


def test_gemini_code_review_main_redacts_review_before_print_and_write(
    monkeypatch, tmp_path, capsys
):
    module = load_module()
    secret = "AIza" + ("D" * 35)
    out = tmp_path / "gemini_report.md"
    monkeypatch.setattr(
        module, "build_review_prompt", lambda targets=None, max_chars=140_000: "prompt"
    )
    monkeypatch.setattr(module, "ask_gemini", lambda prompt: f"model echoed {secret}")

    assert module.main(["--out", str(out)]) == 0

    captured = capsys.readouterr()
    written = out.read_text(encoding="utf-8")
    assert secret not in captured.out
    assert secret not in written
    assert "AIza<redacted>" in captured.out
    assert "AIza<redacted>" in written


def test_gemini_code_review_default_snapshot_includes_protocol_and_generator_files():
    module = load_module()

    prompt = module.build_review_prompt(max_chars=90_000)
    snapshot = repository_snapshot(prompt)

    assert "### shared/protocol/prop_protocol.h" in snapshot
    assert "### shared/protocol/protocol.py" in snapshot
    assert "### tools/build_uiflow_alpha2_artifact.py" in snapshot
    assert "### uiflow/dial/blocks/dist/PropTx.m5b2" in snapshot
    assert "### uiflow/dial/blocks/code/send_fire.py" in snapshot
    assert "### uiflow/dial/blocks/code/reply.py" in snapshot


def test_gemini_code_review_summarizes_m5b2_so_protocol_files_fit_default_budget():
    module = load_module()

    prompt = module.build_review_prompt()
    artifact_section = snapshot_section(prompt, "uiflow/dial/blocks/dist/PropTx.m5b2")

    assert "sha256:" in artifact_section
    assert "pyCode_sha256:" in artifact_section
    assert "block_type_count:" in artifact_section
    assert "<TRUNCATED BY max-chars>" not in artifact_section
    assert "### shared/protocol/prop_protocol.h" in prompt
    assert "### shared/protocol/protocol.py" in prompt


def test_gemini_code_review_includes_complete_key_loader_before_truncation():
    module = load_module()

    prompt = module.build_review_prompt()
    key_section = snapshot_section(prompt, "tools/gemini_key.py")

    assert "def load_api_key" in key_section
    assert "GEMINI_API_KEY_FILE" in key_section
    assert "Secrets are never committed or printed" in key_section
    assert "<TRUNCATED BY max-chars>" not in key_section


def test_gemini_code_review_reports_snapshot_coverage_for_omitted_files():
    module = load_module()

    prompt = module.build_review_prompt(
        targets=["tools/gemini_key.py", "tools/validate_uiflow_blocks.py"],
        max_chars=240,
    )
    coverage = snapshot_coverage(prompt)
    snapshot = repository_snapshot(prompt)

    assert "Treat the Included Files list as review intent, not proof of inclusion." in prompt
    assert "- tools/gemini_key.py: partial" in coverage
    assert "- tools/validate_uiflow_blocks.py: omitted" in coverage
    assert "### tools/gemini_key.py" in snapshot
    assert "### tools/validate_uiflow_blocks.py" not in snapshot


def test_gemini_code_review_default_budget_includes_non_visual_gate_files_untruncated():
    module = load_module()

    prompt = module.build_review_prompt()
    coverage = snapshot_coverage(prompt)
    snapshot = repository_snapshot(prompt)

    for path in [
        "tools/build_uiflow_alpha2_artifact.py",
        "tools/validate_uiflow_blocks.py",
        "tools/uiflow_dial_offline.py",
        "tools/gemini_key.py",
        "tools/gemini_code_review.py",
        "tools/gemini_jury.py",
        "tools/ask_gemini.py",
        "tools/sim_link.py",
        "uiflow/dial/main.py",
        "tests/test_gemini_key.py",
        "tests/test_gemini_jury.py",
        "tests/test_gemini_code_review.py",
        "tests/test_sim_link_safety.py",
        "tests/test_uiflow_blocks_bundle.py",
        "tests/test_uiflow_dial_offline.py",
        "tests/test_uiflow_main_app.py",
        "firmware/din-rx/src/prop_rx.cpp",
        "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp",
        "firmware/c6l-modem/src/modem_core.h",
        "shared/core/safety_logic.h",
        "tools/build.ps1",
        "docs/hardware.md",
        "uiflow/dial/README.md",
        "uiflow/dial/blocks/README.md",
    ]:
        assert f"- {path}: full" in coverage
        assert f"### {path}" in snapshot

    assert "- tests/test_project_sources.py:" in coverage
    assert "### tests/test_project_sources.py" in snapshot
    assert "PROTOTYPE_SHARED_KEY" in snapshot_section(prompt, "tests/test_project_sources.py")
    assert "python_syntax: ok" in snapshot_section(prompt, "tools/gemini_code_review.py")
