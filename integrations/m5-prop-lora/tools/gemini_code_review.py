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
    "shared/protocol/protocol.py",
    "firmware/din-rx/src/prop_rx.cpp",
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
    "docs/hardware.md",
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

The prototype HMAC key is acceptable only for PoC/dry-smoke work when release
gates explicitly block it from Release/CI builds; treat it as a production/field
release blocker if the gate is missing, untested, or bypassable.

Return a concise engineering review:
- BLOCKERS: concrete issues that should stop hardware acceptance.
- IMPORTANT: fixes worth doing before the next field test.
- NICE: lower-risk cleanup.
- TESTS: exact tests or commands you would add/run.
- ACCEPTANCE: whether this is ready for a dry hardware smoke, and why.

Be specific and cite filenames from the snapshot. Avoid generic advice.
"""

API_KEY_RE = re.compile(r"AIza[0-9A-Za-z_-]{20,}")
ENV_SECRET_RE = re.compile(
    r"\b((?:GEMINI|GOOGLE|OPENAI|ANTHROPIC|API|AUTH)[A-Z0-9_]*(?:KEY|TOKEN|SECRET))=([^\s&]+)"
)
QUERY_KEY_RE = re.compile(r"([?&]key=)([^&\s]+)")
BEARER_RE = re.compile(r"(Authorization:\s*Bearer\s+)([^\s]+)", re.IGNORECASE)
GOOG_HEADER_RE = re.compile(r"(x-goog-api-key:\s*)([^\s]+)", re.IGNORECASE)
SECRET_LIKE_NAMES = {".gemini_api_key"}
FULL_TEXT_CHAR_LIMIT = 4_000
SUMMARY_MATCH_LIMIT = 60
SUMMARY_KEYWORDS = (
    "ACCEPTANCE",
    "PROTOTYPE_SHARED_KEY",
    "PROP_ALLOW_PROTOTYPE_SHARED_KEY",
    "PROP_TX_ALLOW_SELFTEST_FIRE",
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
    "UIFlow",
    "blocks",
    "Custom",
    "mpremote",
    "offline",
    "PropTx",
    "redact",
    "remote_led",
    "secret",
    "SHARED_KEY",
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
    return GOOG_HEADER_RE.sub(lambda m: f"{m.group(1)}<redacted>", redacted)


def _looks_secret_like(path: Path) -> bool:
    for part in path.parts:
        lower = part.lower()
        if lower in SECRET_LIKE_NAMES:
            return True
        if lower.endswith(".secret") or lower.startswith(".env"):
            return True
        if lower.endswith("_token") or lower.endswith("_api_key"):
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
    matches = _keyword_matches(source)
    if matches:
        lines.append("keyword_matches:")
        lines.extend(f"  - {item}" for item in matches)
    return f"### {rel}\n\n```text\n" + "\n".join(lines) + "\n```\n"


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
    redacted = redact_secrets(text)
    source_hash = _sha256_bytes(redacted.encode("utf-8"))
    if len(redacted) > FULL_TEXT_CHAR_LIMIT:
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
    targets: list[str] | None = None, max_chars: int = 140_000
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


def collect_snapshot(targets: list[str] | None = None, max_chars: int = 140_000) -> str:
    snapshot, _coverage = collect_snapshot_with_coverage(targets=targets, max_chars=max_chars)
    return snapshot


def format_snapshot_coverage(coverage: list[SnapshotCoverage]) -> str:
    if not coverage:
        return "- <no files selected>"
    return "\n".join(item.line() for item in coverage)


def build_review_prompt(targets: list[str] | None = None, max_chars: int = 140_000) -> str:
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
        "# Repository Snapshot\n\n"
        f"{snapshot}"
    )


def _endpoint(api_key: str) -> str:
    return f"{GEMINI_ENDPOINT_PREFIX}{GEMINI_MODEL}:generateContent"


def ask_gemini(prompt: str) -> str:
    api_key = load_api_key(ROOT)
    endpoint = _endpoint(api_key)
    body = json.dumps(
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.35,
                "maxOutputTokens": 1800,
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

    return (
        redact_secrets(
            data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        )
        or "(empty)"
    )


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
    ap.add_argument("--max-chars", type=int, default=140_000, help="snapshot character budget")
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
        print(f"No Gemini API call was made; prompt written to {out_path}")
        return 0

    review = redact_secrets(ask_gemini(prompt))
    _write(
        out_path,
        "# Gemini code/workflow review\n\n"
        f"model: {GEMINI_MODEL}\n\n"
        "## Review\n\n"
        f"{review}\n\n"
        "## Prompt Snapshot\n\n"
        f"```text\n{prompt}\n```\n",
    )
    print(f"Gemini code/workflow review written to {out_path}")
    print(review)
    return 1 if review.startswith("ERROR") else 0


if __name__ == "__main__":
    raise SystemExit(main())
