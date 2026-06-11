from __future__ import annotations

import argparse
import re
from pathlib import Path

USE_RE = re.compile(r"^\s*(?:-\s*)?uses:\s*(?P<ref>[^\s#]+)(?P<rest>.*)$")
FULL_SHA_RE = re.compile(r"@[0-9a-f]{40}$")
VERSION_COMMENT_RE = re.compile(r"#\s*v\d+(?:\.\d+){0,2}\b")
AUDIT_TOOL_INSTALL_RE = re.compile(
    r"\b(?:python\s+-m\s+)?pip\s+install\b(?![^\n]*\s-r\b)[^\n#]*"
    r"(?:^|[\s\"'])(pip-audit|bandit|safety|cyclonedx-bom|pip-licenses)"
    r"(?:[<>=\s\"']|$)",
    re.IGNORECASE,
)
PIP_AUDIT_REQUIREMENT_RE = re.compile(r"^\s*pip-audit\b", re.MULTILINE)


def validate_workflow_text(path: Path, text: str) -> list[str]:
    issues: list[str] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        uses_match = USE_RE.match(line)
        if uses_match:
            ref = uses_match.group("ref")
            if ref.startswith("./"):
                continue
            if not FULL_SHA_RE.search(ref):
                issues.append(
                    f"{path}:{line_no}: action reference {ref!r} is not pinned to a full commit SHA"
                )
            elif not VERSION_COMMENT_RE.search(uses_match.group("rest")):
                issues.append(
                    f"{path}:{line_no}: action reference {ref!r} is missing inline version comment"
                )

        install_match = AUDIT_TOOL_INSTALL_RE.search(line)
        if install_match:
            tool = install_match.group(1)
            issues.append(
                f"{path}:{line_no}: install audit tooling from requirements-dev.txt, not ad hoc ({tool})"
            )
    return issues


def validate_requirements(text: str) -> list[str]:
    if PIP_AUDIT_REQUIREMENT_RE.search(text):
        return []
    return ["requirements-dev.txt: pip-audit must be declared in the dev dependency manifest"]


def collect_issues(root: Path) -> list[str]:
    issues: list[str] = []
    workflows_dir = root / ".github" / "workflows"
    for pattern in ("*.yml", "*.yaml"):
        for workflow in sorted(workflows_dir.glob(pattern)):
            issues.extend(validate_workflow_text(workflow, workflow.read_text(encoding="utf-8")))

    requirements_dev = root / "requirements-dev.txt"
    if requirements_dev.exists():
        issues.extend(validate_requirements(requirements_dev.read_text(encoding="utf-8")))
    else:
        issues.append("requirements-dev.txt: missing dev dependency manifest")
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check CI supply-chain guardrails.")
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root to scan.")
    args = parser.parse_args(argv)

    issues = collect_issues(args.root)
    if issues:
        for issue in issues:
            print(issue)
        return 1
    print("[OK] supply-chain guardrails")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
