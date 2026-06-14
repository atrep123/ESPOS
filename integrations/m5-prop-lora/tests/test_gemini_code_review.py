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


def compliant_review(extra: str = "") -> str:
    return "\n".join(
        [
            "EXPECTED INVARIANTS: accepted.",
            "BLOCKERS: None.",
            f"IMPORTANT: {extra or 'None.'}",
            "NICE: None.",
            "TESTS: python -m pytest -q.",
            (
                "ACCEPTANCE: code snapshot OK; dry hardware smoke OK on dummy load; "
                "production hardware acceptance blocked until C++ key provisioning and hardware smoke."
            ),
        ]
    )


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
    assert "C++ Dial/DinMeter firmware must not compile usable HMAC key material" in prompt
    assert "byte pattern used only to reject the known dry-smoke key" in prompt
    assert "not usable key" in prompt
    assert "runtime key provider is used" in prompt
    assert "EXPECTED INVARIANTS" in prompt
    assert "Do not repeat accepted invariants under" in prompt
    assert "actual `/flash/prop_key.py` file is intentionally not included" in prompt
    assert "runtime provider is the generated or provisioned `/flash/prop_key.py`" in prompt
    assert "/flash/prop_key.py redacted schema" in prompt
    assert 'SHARED_KEY_HEX = "<redacted hex, at least 16 bytes>"' in prompt
    assert "namespace `prop_key`, key `shared`" in prompt
    assert "same local non-source secret" in prompt
    assert "separate statuses for `code snapshot`, `dry hardware smoke`, and" in prompt
    assert "Do not mark production hardware accepted" in prompt
    assert "Treat <redacted> inside source excerpts as a sanitization artifact" in prompt
    assert "intentionally rejects legacy `SHARED_KEY`" in prompt
    assert "accepts only `SHARED_KEY_HEX`" in prompt
    assert "safety control, not a mismatch" in prompt
    assert "internal assignment `SHARED_KEY, DRY_SMOKE_KEY_ACTIVE = _load_shared_key()`" in prompt
    assert "is not the legacy `/flash/prop_key.py` schema" in prompt
    assert "necessarily returns the Gemini API key string in memory" in prompt
    assert "printed, persisted, included in prompts/reports" in prompt
    assert "only as a rejection pattern" in prompt
    assert "used as HMAC key material" in prompt
    assert "production hardware remains blocked until the local non-source key" in prompt
    assert "Dial-TX runtime key usage is accepted" in prompt
    assert "_runtime_key_or_status()" in prompt
    assert "key->data()" in prompt
    assert "key->size()" in prompt
    assert "file-local positive sightings" in prompt
    assert "header, test file, or unrelated helper is not a violation" in prompt


def test_gemini_code_review_default_snapshot_includes_core_files():
    module = load_module()

    prompt = module.build_review_prompt()
    snapshot = repository_snapshot(prompt)

    assert "### tools/validate_uiflow_blocks.py" in snapshot
    assert "### shared/protocol/prop_runtime_key.h" in snapshot
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
            'SHARED_KEY_HEX = "102132435465768798a9babbdcddedef"',
            'PROTOTYPE_KEY_HEX = "00112233445566778899aabbccddeeff"',
        ]
    )

    redacted = module.redact_secrets(text)

    assert text not in redacted
    assert "AIza<redacted>" in redacted
    assert "GEMINI_API_KEY=<redacted>" in redacted
    assert "key=<redacted>" in redacted
    assert "Authorization: Bearer <redacted>" in redacted
    assert "x-goog-api-key: <redacted>" in redacted
    assert 'SHARED_KEY_HEX = "<redacted>"' in redacted
    assert 'PROTOTYPE_KEY_HEX = "<redacted>"' in redacted
    assert "102132435465768798a9babbdcddedef" not in redacted
    assert "00112233445566778899aabbccddeeff" not in redacted


def test_gemini_code_review_refuses_raw_source_secret_before_snapshot(monkeypatch, tmp_path):
    module = load_module()
    secret = "AIza" + ("E" * 35)
    source = tmp_path / "leaky.py"
    source.write_text(
        "\n".join(
            [
                f"API_KEY = {secret!r}",
                "URL = 'https://example.test/path?key=query-secret-value'",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "ROOT", tmp_path)

    with pytest.raises(ValueError, match="raw secret-like value"):
        module.build_review_prompt(targets=["leaky.py"], max_chars=8_000)


def test_gemini_code_review_refuses_unredacted_prompt_before_network(monkeypatch):
    module = load_module()
    secret = "AIza" + ("F" * 35)

    def fail_urlopen(*_args, **_kwargs):
        raise AssertionError("network must not be called with unredacted prompt")

    monkeypatch.setattr(module.urllib.request, "urlopen", fail_urlopen)

    with pytest.raises(ValueError, match="unredacted secret"):
        module.ask_gemini(f"prompt accidentally contains {secret}")


def test_gemini_code_review_full_cpp_snapshot_exposes_runtime_key_evidence():
    module = load_module()

    prompt = module.build_review_prompt(
        targets=["shared/protocol/prop_runtime_key.h"]
    )
    section = snapshot_section(prompt, "shared/protocol/prop_runtime_key.h")

    assert "#define PROP_ALLOW_DRY_SMOKE_RUNTIME_KEY 0" in section
    assert "isKnownDrySmokeKey(src, len) && !allowDrySmokeRuntimeKey()" in section
    assert "return false;" in section
    assert "SHARED_KEY[]" not in section
    assert "sizeof(SHARED_KEY)" not in section


def test_gemini_code_review_full_dial_snapshot_exposes_runtime_key_use():
    module = load_module()

    prompt = module.build_review_prompt(
        targets=["firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp"]
    )
    section = snapshot_section(
        prompt, "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp"
    )

    assert '#include "prop_runtime_key.h"' in section
    assert "load_runtime_key_from_nvs" in section
    assert "key->data()" in section
    assert "key->size()" in section
    assert "KEY MISSING" in section
    assert "SHARED_KEY[]" not in section
    assert "sizeof(SHARED_KEY)" not in section


def test_gemini_code_review_full_uiflow_snapshot_exposes_prop_key_provider():
    module = load_module()

    prompt = module.build_review_prompt(targets=["uiflow/dial/prop_frame.py"])
    section = snapshot_section(prompt, "uiflow/dial/prop_frame.py")

    assert "import prop_key" in section
    assert "SHARED_KEY, DRY_SMOKE_KEY_ACTIVE = _load_shared_key()" in section
    assert 'if hasattr(prop_key, "SHARED_KEY")' in section
    assert 'raise RuntimeError("prop_key.py must not define SHARED_KEY; use SHARED_KEY_HEX")' in section
    assert 'key_hex = getattr(prop_key, "SHARED_KEY_HEX", None)' in section
    assert "00112233445566778899aabbccddeeff" not in section


def test_gemini_code_review_safe_print_handles_cp1250_console():
    module = load_module()

    class Cp1250Stream:
        encoding = "cp1250"

        def __init__(self):
            self.parts = []

        def write(self, text):
            text.encode(self.encoding)
            self.parts.append(text)

        def flush(self):
            pass

    stream = Cp1250Stream()

    module.safe_print("dry smoke -> Gemini says Dial \u2192 DinMeter", stream=stream)

    written = "".join(stream.parts)
    assert "dry smoke -> Gemini says Dial" in written
    assert "?" in written
    assert "\u2192" not in written


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
    for target in [
        "uiflow/dial/prop_key.py",
        "build/uiflow_dial_offline/device/prop_key.py",
        "prop-key.hex",
        "prop_key.hex",
        "secrets/prop-key.hex",
        "secrets/prop_key.hex",
        "local.prop-key.hex",
        "local.prop_key.hex",
    ]:
        with pytest.raises(ValueError, match="refusing to include secret-like target"):
            module._normalise_target(target)


def test_gemini_code_review_rejects_raw_hmac_hex_in_keyish_labels():
    module = load_module()

    with pytest.raises(ValueError, match="raw HMAC key-like value"):
        module.require_no_raw_hmac_key_material(
            "102132435465768798a9babbdcddedef\n", "secrets/prop_key.hex"
        )


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
    monkeypatch.setattr(module, "ask_gemini", lambda prompt: compliant_review(f"model echoed {secret}"))

    assert module.main(["--out", str(out)]) == 0

    captured = capsys.readouterr()
    written = out.read_text(encoding="utf-8")
    assert secret not in captured.out
    assert secret not in written
    assert "AIza<redacted>" in captured.out
    assert "AIza<redacted>" in written


def test_gemini_code_review_gate_rejects_truncated_or_missing_sections(tmp_path, monkeypatch):
    module = load_module()
    out = tmp_path / "gemini_report.md"
    monkeypatch.setattr(module, "build_review_prompt", lambda targets=None, max_chars=500_000: "prompt")
    monkeypatch.setattr(
        module,
        "ask_gemini",
        lambda prompt: "BLOCKERS: None.\nIMPORTANT: cut off before the required sections",
    )

    assert module.main(["--out", str(out)]) == 1

    written = out.read_text(encoding="utf-8")
    assert "## Gate Errors" in written
    assert "missing required section: EXPECTED INVARIANTS" in written
    assert "missing required section: ACCEPTANCE" in written


def test_gemini_code_review_gate_requires_separate_acceptance_statuses():
    module = load_module()

    errors = module.review_gate_errors(
        "\n".join(
            [
                "EXPECTED INVARIANTS: accepted.",
                "BLOCKERS: None.",
                "IMPORTANT: None.",
                "NICE: None.",
                "TESTS: pytest.",
                "ACCEPTANCE: ready.",
            ]
        )
    )

    assert "ACCEPTANCE missing separate `code snapshot` status" in errors
    assert "ACCEPTANCE missing separate `dry hardware smoke` status" in errors
    assert "ACCEPTANCE missing separate `production hardware acceptance` status" in errors


def test_gemini_code_review_gate_accepts_markdown_heading_sections():
    module = load_module()

    errors = module.review_gate_errors(
        "\n".join(
            [
                "## Engineering Review",
                "### EXPECTED INVARIANTS",
                "Accepted.",
                "### BLOCKERS",
                "None.",
                "### IMPORTANT",
                "None.",
                "### NICE",
                "None.",
                "### TESTS",
                "pytest.",
                "### ACCEPTANCE",
                "- Code Snapshot: OK.",
                "- Dry Hardware Smoke: OK on dummy load.",
                "- Production Hardware Acceptance: blocked until provisioning.",
            ]
        )
    )

    assert errors == []


def test_gemini_code_review_reports_max_token_truncation(monkeypatch):
    module = load_module()

    def fake_urlopen(req, timeout):
        assert timeout == 180
        return io.BytesIO(
            b'{"candidates":[{"finishReason":"MAX_TOKENS","content":{"parts":[{"text":"BLOCKERS: None"}]}}]}'
        )

    monkeypatch.setattr(module, "load_api_key", lambda root: "fake-key")
    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)

    result = module.ask_gemini("prompt")

    assert result.startswith("ERROR: Gemini response truncated")
    assert "Partial response:" in result


def test_gemini_code_review_default_snapshot_includes_protocol_and_generator_files():
    module = load_module()

    prompt = module.build_review_prompt()
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
        "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.h",
        "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp",
        "firmware/c6l-modem/src/modem_core.h",
        "shared/core/safety_logic.h",
        "shared/protocol/prop_runtime_key.h",
        "tools/build.ps1",
        "docs/control_architecture.md",
        "docs/cxx_key_provisioning.md",
        "docs/hardware.md",
        "docs/bench_test_checklist.md",
        "uiflow/dial/README.md",
        "uiflow/dial/blocks/README.md",
    ]:
        assert f"- {path}: full" in coverage
        assert f"### {path}" in snapshot

    assert "- tests/test_project_sources.py:" in coverage
    assert "### tests/test_project_sources.py" in snapshot
    assert "prop_key.py did not provide SHARED_KEY" in snapshot_section(
        prompt, "tests/test_project_sources.py"
    )
    assert "python_syntax: ok" in snapshot_section(prompt, "tools/gemini_code_review.py")


def test_gemini_code_review_default_snapshot_includes_full_key_fingerprint_workflow():
    module = load_module()

    prompt = module.build_review_prompt()
    offline_tool = snapshot_section(prompt, "tools/uiflow_dial_offline.py")
    offline_tests = snapshot_section(prompt, "tests/test_uiflow_dial_offline.py")

    assert "representation: compact-summary" not in offline_tool
    assert "def _key_fingerprint" in offline_tool
    assert "prop_key_hex_file mismatch: device/prop_key.py" in offline_tests
    assert "same local `prop-key.hex` as the source for C++ `prop_key/shared`" in prompt


def test_gemini_code_review_summaries_do_not_turn_test_mentions_into_key_material():
    module = load_module()

    prompt = module.build_review_prompt()
    section = snapshot_section(prompt, "tests/test_gemini_code_review.py")

    assert "contains_shared_key_array_literal: True" not in section
    assert "contains_sizeof_shared_key: True" not in section
    assert "defines_shared_key_array_literal: True" not in section
    assert "uses_sizeof_shared_key_as_key_material: True" not in section
