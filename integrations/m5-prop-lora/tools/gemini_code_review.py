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
    "README.md",
    "BUILD.md",
    "uiflow/dial/README.md",
    "uiflow/dial/blocks/README.md",
    "uiflow/dial/blocks/prop_tx.json",
    "uiflow/dial/blocks/alpha2/PropTx.py",
    "uiflow/dial/blocks/dist/PropTx.m5b2",
    "uiflow/dial/blocks/code/send_fire.py",
    "uiflow/dial/blocks/code/reply.py",
    "uiflow/dial/blocks/examples/prop_tx_smoke.py",
    "uiflow/dial/prop_frame.py",
    "tools/gemini_key.py",
    "shared/protocol/prop_protocol.h",
    "shared/protocol/protocol.py",
    "tools/build_uiflow_alpha2_artifact.py",
    "tools/validate_uiflow_blocks.py",
    "tools/uiflow_dial_offline.py",
    "tools/gemini_jury.py",
    "tools/ask_gemini.py",
    "tools/gemini_dinrx_review.py",
    "tools/gemini_code_review.py",
    "tests/test_uiflow_blocks_bundle.py",
    "tests/test_uiflow_dial_offline.py",
    "tests/test_uiflow_prop_frame_parity.py",
    "tests/test_uiflow_main_app.py",
    "tests/test_gemini_key.py",
    "tests/test_gemini_jury.py",
    "tests/test_gemini_code_review.py",
    "uiflow/dial/main.py",
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


def _read_target(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    if not path.is_file():
        return f"### {rel}\n\n<MISSING>\n"
    if path.suffix == ".m5b2":
        return _summarize_m5b2(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    return f"### {rel}\n\n```text\n{redact_secrets(text)}\n```\n"


def collect_snapshot(targets: list[str] | None = None, max_chars: int = 70_000) -> str:
    selected = DEFAULT_TARGETS if targets is None else tuple(targets)
    chunks: list[str] = []
    used = 0

    for target in selected:
        chunk = _read_target(_normalise_target(target))
        remaining = max_chars - used
        if remaining <= 0:
            break
        if len(chunk) > remaining:
            chunk = chunk[: max(0, remaining - 80)] + "\n\n<TRUNCATED BY max-chars>\n"
        chunks.append(chunk)
        used += len(chunk)

    return "\n".join(chunks)


def build_review_prompt(targets: list[str] | None = None, max_chars: int = 70_000) -> str:
    selected = DEFAULT_TARGETS if targets is None else tuple(targets)
    file_list = "\n".join(f"- {target}" for target in selected)
    snapshot = collect_snapshot(targets=targets, max_chars=max_chars)
    return redact_secrets(
        f"{REVIEW_BRIEF}\n\n# Included Files\n\n{file_list}\n\n# Repository Snapshot\n\n{snapshot}"
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
        detail = exc.read().decode("utf-8", "replace")[:600]
        return f"ERROR HTTP {exc.code}: {detail}"
    except Exception as exc:  # noqa: BLE001
        return f"ERROR: {exc}"

    return (
        data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    ) or "(empty)"


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
    ap.add_argument("--max-chars", type=int, default=70_000, help="snapshot character budget")
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

    review = ask_gemini(prompt)
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
