"""Ask Gemini for a non-visual code/workflow review of the M5 UIFlow path.

This complements screenshot jury reviews by packaging selected source, tests,
docs, and manifests into a text-only prompt. The API key is loaded through the
shared gemini_key module and is never written to the report.

Usage:
    python tools/gemini_code_review.py --dry-run
    python tools/gemini_code_review.py
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

from gemini_key import load_api_key


ROOT = Path(__file__).resolve().parents[1]
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_ENDPOINT_PREFIX = "https://generativelanguage.googleapis.com/v1beta/models/"

DEFAULT_TARGETS = (
    "uiflow/dial/blocks/prop_tx.json",
    "uiflow/dial/blocks/alpha2/PropTx.py",
    "uiflow/dial/blocks/dist/PropTx.m5b2",
    "uiflow/dial/blocks/code/send_fire.py",
    "uiflow/dial/blocks/code/reply.py",
    "uiflow/dial/blocks/examples/prop_tx_smoke.py",
    "uiflow/dial/prop_frame.py",
    "uiflow/dial/main.py",
    "shared/core/safety_logic.h",
    "shared/protocol/prop_protocol.h",
    "shared/protocol/prop_runtime_key.h",
    "shared/protocol/protocol.py",
    "firmware/din-rx/src/prop_rx.cpp",
    "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.h",
    "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp",
    "firmware/c6l-modem/src/modem_core.h",
    "tools/build.ps1",
    "tools/build_uiflow_alpha2_artifact.py",
    "tools/validate_uiflow_blocks.py",
    "tools/uiflow_dial_offline.py",
    "tools/gemini_key.py",
    "tools/gemini_code_review.py",
    "tools/gemini_jury.py",
    "tools/ask_gemini.py",
    "tools/sim_link.py",
    "tests/test_project_sources.py",
    "tests/test_gemini_key.py",
    "tests/test_gemini_jury.py",
    "tests/test_gemini_code_review.py",
    "tests/test_uiflow_blocks_bundle.py",
    "tests/test_uiflow_dial_offline.py",
    "tests/test_uiflow_main_app.py",
    "tests/test_uiflow_prop_frame_parity.py",
    "tests/test_sim_link_safety.py",
    "README.md",
    "BUILD.md",
    "docs/control_architecture.md",
    "docs/cxx_key_provisioning.md",
    "docs/hardware.md",
    "docs/bench_test_checklist.md",
    "uiflow/dial/README.md",
    "uiflow/dial/blocks/README.md",
    "tools/gemini_dinrx_review.py",
)

REVIEW_BRIEF = """\
You are reviewing a text-only snapshot of the M5Stack Dial UIFlow2 integration
inside the ESPOS repository.

Do not review screenshots or visual polish here. Focus on code, tests, docs,
and release workflow. Evaluate:

1. UIFlow2 custom block artifact reproducibility and import/runtime parity.
2. The offline mpremote workflow, bundle manifest, verification, and deploy safety.
3. wire protocol parity between MicroPython PropTx calls and the shared firmware decoder.
4. secret handling for Gemini as a review gate, including accidental logging/persistence.
5. Test coverage gaps that could let artifact drift, frame drift, or unsafe deploys pass.
6. Documentation gaps for operating M5 work from the full ESPOS repository.

Reviewing source code for the key loader or its tests is expected and is not
itself a secret exposure; only concrete secret values, persisted key files,
unredacted runtime payloads, or logs containing key values are blockers.
Treat <redacted> inside source excerpts as a sanitization artifact, not source
evidence, unless confirmed by unredacted tests or coverage.

C++ Dial/DinMeter firmware must not compile usable HMAC key material. A hardcoded
byte pattern used only to reject the known dry-smoke key is not usable key
material. Treat production as blocked unless the runtime key provider is used,
missing/mismatched keys fail closed, and UIFlow `/flash/prop_key.py` keys are
proven to match the C++ runtime provisioning source.

Interpret these expected invariants carefully:
- `uiflow/dial/prop_frame.py` intentionally rejects legacy `SHARED_KEY`
  byte/string schemas and accepts only `SHARED_KEY_HEX`; that rejection is a
  safety control, not a mismatch. Flag it only if generated bundles still emit
  legacy `SHARED_KEY`, or if malformed/missing keys do not fail closed.
- The internal assignment `SHARED_KEY, DRY_SMOKE_KEY_ACTIVE = _load_shared_key()`
  in `uiflow/dial/prop_frame.py` is expected runtime state after validation. It
  is not the legacy `/flash/prop_key.py` schema and is not emitted by the bundle
  generator. Do not report it as a blocker.
- `tools/gemini_key.py` necessarily returns the Gemini API key string in memory
  so the HTTP request can be authenticated. This is a blocker only if the key is
  printed, persisted, included in prompts/reports, committed, or sent to an
  unintended endpoint; check the redaction and no-network-before-redaction tests
  for evidence.
- `shared/protocol/prop_runtime_key.h` may contain the known dry-smoke key bytes
  only as a rejection pattern. Treat that as acceptable evidence when production
  builds force `PROP_ALLOW_DRY_SMOKE_RUNTIME_KEY=0` and encoders/decoders use
  `RuntimeKey` data loaded from NVS/Preferences. Flag any compiled secret bytes
  that are used as HMAC key material.
- C++ production hardware remains blocked until the local non-source key has
  been provisioned into namespace `prop_key`, key `shared`; the presence of this
  runbook gap is important, but do not confuse it with a committed-key leak.
- Dial-TX runtime key usage is accepted when the snapshot shows the send/decode
  paths calling `_runtime_key_or_status()` and passing `key->data()` plus
  `key->size()` into `prop_protocol::encodeFrame` or `prop_protocol::decodeFrame`.
  Do not report Dial-TX as unable to authenticate frames unless you can cite a
  specific current send path that lacks those calls.
- `key_handling_evidence` entries are file-local positive sightings. Missing
  evidence in a header, test file, or unrelated helper is not a violation by
  itself; judge send/receive authentication from the owning implementation files.

The actual `/flash/prop_key.py` file is intentionally not included in snapshots
because it can contain production HMAC material. For UIFlow/MicroPython, the
runtime provider is the generated or provisioned `/flash/prop_key.py` file with
`SHARED_KEY_HEX` plus `ALLOW_PROTOTYPE_SHARED_KEY`; it is expected not to use
ESP32 NVS directly. Review `tools/uiflow_dial_offline.py`, its manifest, and
tests for that schema. For C++ Dial/DinMeter, the runtime provider is NVS /
Preferences namespace `prop_key`, key `shared`. Hardware acceptance requires
both providers to be populated from the same local non-source secret. If no C++
prototype key bytes or legacy prototype compile flag remain, do not require a
prototype-key compile gate solely for its own sake; source and release gates
should instead prove that compiled key bytes are absent.

Return a concise engineering review:
- EXPECTED INVARIANTS: accepted/violated/insufficient-evidence status for the
  four named invariant areas above. Do not repeat accepted invariants under
  BLOCKERS.
- BLOCKERS: concrete issues that should stop hardware acceptance.
- IMPORTANT: fixes worth doing before the next field test.
- NICE: lower-risk cleanup.
- TESTS: exact tests or commands you would add/run.
- ACCEPTANCE: separate statuses for `code snapshot`, `dry hardware smoke`, and
  `production hardware acceptance`. Do not mark production hardware accepted
  unless the C++ key provisioning and hardware smoke sequence are complete.

Be specific and cite filenames from the snapshot. Avoid generic advice.
"""

PROP_KEY_SCHEMA = """\
### /flash/prop_key.py redacted schema (not a committed file)

```python
# Generated by tools/uiflow_dial_offline.py from a local key file.
# Do not commit generated production key bundles.
ALLOW_PROTOTYPE_SHARED_KEY = False  # True only for explicit dry-smoke bundles
SHARED_KEY_HEX = "<redacted hex, at least 16 bytes>"
```
"""

API_KEY_RE = re.compile(r"AIza[0-9A-Za-z_-]{20,}")
ENV_SECRET_RE = re.compile(
    r"\b((?:GEMINI|GOOGLE|OPENAI|ANTHROPIC|API|AUTH)[A-Z0-9_]*(?:KEY|TOKEN|SECRET))=([^\s&]+)"
)
QUERY_KEY_RE = re.compile(r"([?&]key=)([^&\s]+)")
BEARER_RE = re.compile(r"(Authorization:\s*Bearer\s+)([^\s]+)", re.IGNORECASE)
GOOG_HEADER_RE = re.compile(r"(x-goog-api-key:\s*)([^\s]+)", re.IGNORECASE)
HMAC_HEX_ASSIGN_RE = re.compile(
    r"\b((?:SHARED_KEY_HEX|PROP_KEY_HEX|HMAC_KEY_HEX|PROTOTYPE_KEY_HEX|DRY_SMOKE_KEY_HEX)\s*=\s*[\"'])([0-9A-Fa-f]{32,128})([\"'])"
)
RAW_HMAC_HEX_RE = re.compile(r"\b[0-9A-Fa-f]{32,128}\b")
SECRET_LIKE_NAMES = {".gemini_api_key"}
FULL_TEXT_CHAR_LIMIT = 4_000
FULL_TEXT_TARGETS = {
    "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp",
    "firmware/din-rx/src/prop_rx.cpp",
    "shared/protocol/prop_protocol.h",
    "tools/uiflow_dial_offline.py",
    "tests/test_uiflow_dial_offline.py",
    "uiflow/dial/blocks/alpha2/PropTx.py",
    "uiflow/dial/prop_frame.py",
    "uiflow/dial/main.py",
    "uiflow/dial/README.md",
}
SUMMARY_MATCH_LIMIT = 90
REQUIRED_REVIEW_SECTIONS = (
    "EXPECTED INVARIANTS",
    "BLOCKERS",
    "IMPORTANT",
    "NICE",
    "TESTS",
    "ACCEPTANCE",
)
RAW_SOURCE_SECRET_PATTERNS = (
    API_KEY_RE,
    ENV_SECRET_RE,
    QUERY_KEY_RE,
    BEARER_RE,
    GOOG_HEADER_RE,
)
SUMMARY_KEYWORDS = (
    "ACCEPTANCE",
    "PROP_ALLOW_PROTOTYPE_SHARED_KEY",
    "PROP_TX_ALLOW_SELFTEST_FIRE",
    "DRY_SMOKE_KEY_ACTIVE",
    "Release",
    "Release/CI",
    "ARM",
    "FIRE",
    "FF ",
    "SEND ",
    "ack",
    "artifact",
    "block_type",
    "build_artifact",
    "bundle",
    "deploy",
    "fire_burst",
    "GEMINI_API_KEY",
    "Gemini",
    "KEY MISSING",
    "--production requires --prop-key-hex-file",
    "--prop-key-hex-file",
    "UIFlow",
    "blocks",
    "Custom",
    "mpremote",
    "offline",
    "PropTx",
    "production bundle requires",
    "key_fingerprint",
    "key_kind",
    "prop_runtime_key",
    "prop_key_hex_file mismatch",
    "redact",
    "refusing to bundle prototype HMAC key",
    "remote_led",
    "runtime_key",
    "runtimeKey",
    "secret",
    "prop_key.py did not provide SHARED_KEY",
    "prop_key.py must not define SHARED_KEY",
    "SHARED_KEY",
    "key->data",
    "key->size",
    "load_runtime_key",
    "loadRuntimeKey",
    "sleep_ms",
    "validate",
    "verify",
)


@dataclass(frozen=True)
class SnapshotChunk:
    target: str
    text: str
    representation: str
    source_chars: int
    sha256: str | None = None


@dataclass(frozen=True)
class SnapshotCoverage:
    target: str
    status: str
    representation: str
    source_chars: int
    included_chars: int
    sha256: str | None = None

    def line(self) -> str:
        detail = (
            f"representation={self.representation}; "
            f"included_chars={self.included_chars}; source_chars={self.source_chars}"
        )
        if self.sha256:
            detail += f"; sha256={self.sha256[:12]}"
        return f"- {self.target}: {self.status} ({detail})"


def redact_secrets(text: str) -> str:
    redacted = API_KEY_RE.sub("AIza<redacted>", text)
    redacted = ENV_SECRET_RE.sub(lambda m: f"{m.group(1)}=<redacted>", redacted)
    redacted = QUERY_KEY_RE.sub(lambda m: f"{m.group(1)}<redacted>", redacted)
    redacted = BEARER_RE.sub(lambda m: f"{m.group(1)}<redacted>", redacted)
    redacted = GOOG_HEADER_RE.sub(lambda m: f"{m.group(1)}<redacted>", redacted)
    return HMAC_HEX_ASSIGN_RE.sub(lambda m: f"{m.group(1)}<redacted>{m.group(3)}", redacted)


def require_no_unredacted_secrets(text: str, label: str) -> None:
    if redact_secrets(text) != text:
        raise ValueError(f"unredacted secret-like value in {label}")


def require_no_raw_transport_secrets(text: str, label: str) -> None:
    for pattern in RAW_SOURCE_SECRET_PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(0)
            if _looks_like_regex_literal_fragment(value) or _looks_like_placeholder_secret(value):
                continue
            raise ValueError(f"raw secret-like value in {label}; refusing to include it")


def require_no_raw_hmac_key_material(text: str, label: str) -> None:
    if not _looks_hmac_key_material_label(label):
        return
    if RAW_HMAC_HEX_RE.search(text):
        raise ValueError(f"raw HMAC key-like value in {label}; refusing to include it")


def _looks_hmac_key_material_label(label: str) -> bool:
    lower = label.replace("\\", "/").lower()
    name = lower.rsplit("/", 1)[-1]
    return (
        name in {"prop-key.hex", "prop_key.hex", "prop_key.py"}
        or name.endswith(".prop-key")
        or name.endswith(".prop-key.hex")
        or name.endswith(".prop-key.txt")
        or name.endswith(".prop_key")
        or name.endswith(".prop_key.hex")
        or name.endswith(".prop_key.txt")
    )


def _looks_like_regex_literal_fragment(value: str) -> bool:
    return any(fragment in value for fragment in (r"\s", r"[^\s]", r"[0-9", r"{20,}"))


def _looks_like_placeholder_secret(value: str) -> bool:
    return (
        value.endswith("=...")
        or "<redacted>" in value
        or "secret-value" in value
        or ("{" in value and "}" in value)
    )


def safe_print(text: str, stream=None) -> None:
    stream = sys.stdout if stream is None else stream
    try:
        print(text, file=stream)
    except UnicodeEncodeError:
        encoding = getattr(stream, "encoding", None) or "utf-8"
        safe = text.encode(encoding, "replace").decode(encoding, "replace")
        print(safe, file=stream)


def _looks_secret_like(path: Path) -> bool:
    for part in path.parts:
        lower = part.lower()
        if lower in SECRET_LIKE_NAMES:
            return True
        if lower in {"secrets", "prop_key.py", "prop-key.hex", "prop_key.hex"}:
            return True
        if lower.endswith(".secret") or lower.startswith(".env"):
            return True
        if lower.endswith("_token") or lower.endswith("_api_key"):
            return True
        if lower.endswith(".prop-key") or lower.endswith(".prop-key.hex") or lower.endswith(".prop-key.txt"):
            return True
        if lower.endswith(".prop_key") or lower.endswith(".prop_key.hex") or lower.endswith(".prop_key.txt"):
            return True
    return False


def _normalise_target(path: str) -> Path:
    if _looks_secret_like(Path(path)):
        raise ValueError(f"refusing to include secret-like target: {path}")
    candidate = (ROOT / path).resolve()
    try:
        candidate.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"target escapes repo root: {path}") from exc
    return candidate


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _python_outline(text: str) -> list[str]:
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return [f"python_parse_error: {exc}"]

    lines: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            methods = [
                item.name
                for item in node.body
                if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef)
            ]
            lines.append(f"class {node.name}: methods={methods}")
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            lines.append(f"def {node.name}(...): line {node.lineno}")
    return lines


def _keyword_matches(text: str) -> list[str]:
    matches: list[str] = []
    seen: set[int] = set()
    source_lines = text.splitlines()
    for keyword in SUMMARY_KEYWORDS:
        lower_keyword = keyword.lower()
        keyword_count = 0
        for lineno, line in enumerate(source_lines, start=1):
            if lineno in seen or lower_keyword not in line.lower():
                continue
            seen.add(lineno)
            matches.append(f"{lineno}: {line[:220]}")
            keyword_count += 1
            if keyword_count >= 4 or len(matches) >= SUMMARY_MATCH_LIMIT:
                break
        if len(matches) >= SUMMARY_MATCH_LIMIT:
            break
    return matches


def _summarize_text_target(path: Path, text: str) -> str:
    rel = path.relative_to(ROOT).as_posix()
    source = redact_secrets(text)
    lines = [
        f"chars: {len(source)}",
        f"sha256: {_sha256_bytes(source.encode('utf-8'))}",
        "representation: compact-summary",
    ]
    if path.suffix == ".py":
        outline = _python_outline(text)
        if outline:
            if not outline[0].startswith("python_parse_error:"):
                lines.append("python_syntax: ok")
            lines.append("python_outline:")
            lines.extend(f"  - {item}" for item in outline)
    key_evidence = _key_handling_evidence(source)
    if key_evidence:
        lines.append("key_handling_evidence:")
        lines.extend(f"  - {item}" for item in key_evidence)
    matches = _keyword_matches(source)
    if matches:
        lines.append("keyword_matches:")
        lines.extend(f"  - {item}" for item in matches)
    return f"### {rel}\n\n```text\n" + "\n".join(lines) + "\n```\n"


def _key_handling_evidence(text: str) -> list[str]:
    if not any(
        marker in text
        for marker in (
            "prop_runtime_key",
            "load_runtime_key",
            "loadRuntimeKey",
            "SHARED_KEY",
            "encodeFrame",
            "decodeFrame",
        )
    ):
        return []
    active_lines = "\n".join(
        line
        for line in text.splitlines()
        if not re.search(r"\bassert(?:In|NotIn|True|False|Equal|NotEqual)?\b", line)
    )
    needles = {
        "uses_uiflow_prop_key_provider": "import prop_key" in text,
        "uses_cxx_runtime_key_provider": "prop_runtime_key.h" in text,
        "references_runtime_namespace": "prop_runtime_key::" in text,
        "loads_runtime_key": "load_runtime_key_from_nvs" in text
        or "loadRuntimeKeyFromPreferences" in text,
        "uses_runtime_key_data": "key->data()" in text,
        "uses_runtime_key_size": "key->size()" in text,
        "reports_key_missing": "KEY MISSING" in text,
        "defines_shared_key_array_literal": "SHARED_KEY[]" in active_lines,
        "uses_sizeof_shared_key_as_key_material": "sizeof(SHARED_KEY)" in active_lines,
        "mentions_shared_key_array_literal": "SHARED_KEY[]" in text,
        "mentions_known_dry_smoke_key_hex": "00112233445566778899aabbccddeeff" in text,
        "rejects_known_dry_smoke_key": (
            "isKnownDrySmokeKey(src, len) && !allowDrySmokeRuntimeKey()" in text
        ),
        "mentions_legacy_prototype_compile_gate": "PROP_ALLOW_PROTOTYPE_SHARED_KEY" in text,
    }
    return [f"{name}: True" for name, value in needles.items() if value]


def _summarize_m5b2(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    raw = path.read_bytes()
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        return (
            f"### {rel}\n\n"
            "```text\n"
            f"bytes: {len(raw)}\n"
            f"sha256: {_sha256_bytes(raw)}\n"
            f"parse_error: {type(exc).__name__}: {exc}\n"
            "```\n"
        )

    uiflow2 = data.get("uiflow2", {}) if isinstance(data, dict) else {}
    members = data.get("data", {}).get("members", []) if isinstance(data, dict) else []
    py_code = str(data.get("pyCode", "")) if isinstance(data, dict) else ""
    jscode = str(uiflow2.get("jscode", "")) if isinstance(uiflow2, dict) else ""
    toolbox = str(uiflow2.get("toolbox", "")) if isinstance(uiflow2, dict) else ""
    block_types = uiflow2.get("block_type", []) if isinstance(uiflow2, dict) else []
    member_names = [
        str(member.get("name", ""))
        for member in members
        if isinstance(member, dict) and member.get("name")
    ]
    summary = {
        "bytes": len(raw),
        "sha256": _sha256_bytes(raw),
        "version": data.get("version") if isinstance(data, dict) else None,
        "category": data.get("category") if isinstance(data, dict) else None,
        "color": data.get("color") if isinstance(data, dict) else None,
        "top_level_keys": sorted(data) if isinstance(data, dict) else [],
        "block_type_count": len(block_types) if isinstance(block_types, list) else 0,
        "member_count": len(member_names),
        "member_names": member_names,
        "pyCode_sha256": _sha256_bytes(py_code.encode("utf-8")),
        "jscode_sha256": _sha256_bytes(jscode.encode("utf-8")),
        "toolbox_sha256": _sha256_bytes(toolbox.encode("utf-8")),
    }
    lines = [f"{key}: {value}" for key, value in summary.items()]
    return f"### {rel}\n\n```text\n" + "\n".join(lines) + "\n```\n"


def _read_target(path: Path) -> SnapshotChunk:
    rel = path.relative_to(ROOT).as_posix()
    if not path.is_file():
        return SnapshotChunk(rel, f"### {rel}\n\n<MISSING>\n", "missing", 0)
    if path.suffix == ".m5b2":
        raw = path.read_bytes()
        return SnapshotChunk(
            rel,
            _summarize_m5b2(path),
            "artifact-summary",
            len(raw),
            _sha256_bytes(raw),
        )
    text = path.read_text(encoding="utf-8", errors="replace")
    require_no_raw_transport_secrets(text, rel)
    require_no_raw_hmac_key_material(text, rel)
    redacted = redact_secrets(text)
    require_no_unredacted_secrets(redacted, f"sanitized {rel}")
    source_hash = _sha256_bytes(redacted.encode("utf-8"))
    if rel not in FULL_TEXT_TARGETS and len(redacted) > FULL_TEXT_CHAR_LIMIT:
        return SnapshotChunk(
            rel,
            _summarize_text_target(path, text),
            "compact-summary",
            len(redacted),
            source_hash,
        )
    return SnapshotChunk(
        rel,
        f"### {rel}\n\n```text\n{redacted}\n```\n",
        "full-text",
        len(redacted),
        source_hash,
    )


def collect_snapshot_with_coverage(
    targets: list[str] | None = None, max_chars: int = 500_000
) -> tuple[str, list[SnapshotCoverage]]:
    selected = DEFAULT_TARGETS if targets is None else tuple(targets)
    chunks: list[str] = []
    coverage: list[SnapshotCoverage] = []
    used = 0

    for target in selected:
        chunk = _read_target(_normalise_target(target))
        remaining = max_chars - used
        if remaining <= 0:
            coverage.append(
                SnapshotCoverage(
                    chunk.target,
                    "omitted",
                    chunk.representation,
                    chunk.source_chars,
                    0,
                    chunk.sha256,
                )
            )
            continue
        if len(chunk.text) > remaining:
            suffix = "\n\n<TRUNCATED BY max-chars>\n"
            included = chunk.text[: max(0, remaining - len(suffix))] + suffix
            chunks.append(included)
            used += len(included)
            coverage.append(
                SnapshotCoverage(
                    chunk.target,
                    "partial",
                    chunk.representation,
                    chunk.source_chars,
                    len(included),
                    chunk.sha256,
                )
            )
            continue
        chunks.append(chunk.text)
        used += len(chunk.text)
        coverage.append(
            SnapshotCoverage(
                chunk.target,
                "full",
                chunk.representation,
                chunk.source_chars,
                len(chunk.text),
                chunk.sha256,
            )
        )

    return "\n".join(chunks), coverage


def collect_snapshot(targets: list[str] | None = None, max_chars: int = 500_000) -> str:
    snapshot, _coverage = collect_snapshot_with_coverage(targets=targets, max_chars=max_chars)
    return snapshot


def format_snapshot_coverage(coverage: list[SnapshotCoverage]) -> str:
    if not coverage:
        return "- <no files selected>"
    return "\n".join(item.line() for item in coverage)


def build_review_prompt(targets: list[str] | None = None, max_chars: int = 500_000) -> str:
    selected = DEFAULT_TARGETS if targets is None else tuple(targets)
    file_list = "\n".join(f"- {target}" for target in selected)
    snapshot, coverage = collect_snapshot_with_coverage(targets=targets, max_chars=max_chars)
    coverage_text = format_snapshot_coverage(coverage)
    return redact_secrets(
        f"{REVIEW_BRIEF}\n\n"
        "# Included Files\n\n"
        f"{file_list}\n\n"
        "# Snapshot Coverage\n\n"
        "Treat the Included Files list as review intent, not proof of inclusion. "
        "Use this coverage table to distinguish full, partial, and omitted evidence; "
        "report 'insufficient evidence' for omitted or truncated files instead of guessing. "
        "For compact-summary Python files, report syntax blockers only when "
        "python_syntax is not ok or a concrete parse error appears in the snapshot.\n\n"
        f"{coverage_text}\n\n"
        "# Redacted Runtime Key Schema\n\n"
        f"{PROP_KEY_SCHEMA}\n"
        "# Repository Snapshot\n\n"
        f"{snapshot}"
    )


def _endpoint(api_key: str) -> str:
    return f"{GEMINI_ENDPOINT_PREFIX}{GEMINI_MODEL}:generateContent"


def ask_gemini(prompt: str) -> str:
    require_no_unredacted_secrets(prompt, "Gemini prompt")
    api_key = load_api_key(ROOT)
    endpoint = _endpoint(api_key)
    body = json.dumps(
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.35,
                "maxOutputTokens": 4096,
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }
    ).encode("utf-8")
    req = urllib.request.Request(  # noqa: S310
        endpoint,
        data=body,
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=180)  # noqa: S310
        data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        detail = redact_secrets(exc.read().decode("utf-8", "replace"))[:600]
        return f"ERROR HTTP {exc.code}: {detail}"
    except Exception as exc:  # noqa: BLE001
        return redact_secrets(f"ERROR: {exc}")

    candidate = data.get("candidates", [{}])[0]
    text = redact_secrets(
        candidate.get("content", {}).get("parts", [{}])[0].get("text", "")
    ) or "(empty)"
    if candidate.get("finishReason") == "MAX_TOKENS":
        return "ERROR: Gemini response truncated at maxOutputTokens.\n\nPartial response:\n" + text
    return text


def review_gate_errors(review: str) -> list[str]:
    errors: list[str] = []
    if review.startswith("ERROR"):
        errors.append("Gemini API call failed or returned a tool-level error.")
        return errors

    def section_re(section: str) -> str:
        return rf"(?im)^\s*(?:[-*]\s*)?(?:#+\s*)?{re.escape(section)}\b(?:\s*:.*|\s*)$"

    for section in REQUIRED_REVIEW_SECTIONS:
        if not re.search(section_re(section), review):
            errors.append(f"missing required section: {section}")

    acceptance = re.search(
        r"(?ims)^\s*(?:[-*]\s*)?(?:#+\s*)?ACCEPTANCE\b(?:\s*:)?(.*)\Z",
        review,
    )
    acceptance_text = acceptance.group(1) if acceptance else ""
    for required in ("code snapshot", "dry hardware smoke", "production hardware acceptance"):
        if required not in acceptance_text.lower():
            errors.append(f"ACCEPTANCE missing separate `{required}` status")

    return errors


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(redact_secrets(text), encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out",
        default=str(ROOT / "build" / "reviews" / "gemini_code_review.md"),
        help="markdown report path",
    )
    ap.add_argument("--max-chars", type=int, default=500_000, help="snapshot character budget")
    ap.add_argument(
        "--target",
        action="append",
        dest="targets",
        help="repo-relative file to include; repeat to override defaults",
    )
    ap.add_argument("--dry-run", action="store_true", help="write the prompt without an API call")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    prompt = build_review_prompt(targets=args.targets, max_chars=args.max_chars)
    out_path = Path(args.out)

    if args.dry_run:
        _write(
            out_path,
            "# Gemini code/workflow review prompt\n\n"
            "No Gemini API call was made.\n\n"
            f"model: {GEMINI_MODEL}\n\n"
            f"```text\n{prompt}\n```\n",
        )
        safe_print(f"No Gemini API call was made; prompt written to {out_path}")
        return 0

    review = redact_secrets(ask_gemini(prompt))
    gate_errors = review_gate_errors(review)
    gate_section = (
        "## Gate Errors\n\n"
        + "\n".join(f"- {error}" for error in gate_errors)
        + "\n\n"
        if gate_errors
        else ""
    )
    report = (
        "# Gemini code/workflow review\n\n"
        f"model: {GEMINI_MODEL}\n\n"
        f"{gate_section}"
        "## Review\n\n"
        f"{review}\n\n"
        "## Prompt Snapshot\n\n"
        f"```text\n{prompt}\n```\n"
    )
    _write(out_path, report)
    safe_print(f"Gemini code/workflow review written to {out_path}")
    if gate_errors:
        safe_print("Gemini code/workflow review gate failed:")
        safe_print("\n".join(f"- {error}" for error in gate_errors))
    safe_print(review)
    return 1 if gate_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
